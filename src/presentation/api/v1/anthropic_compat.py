"""Anthropic API 通用透传代理

鉴权流程：
  1. 从请求头提取系统用户 API Key（Authorization: Bearer <sk-xxx> 或 x-api-key: <sk-xxx>）
  2. 通过 ApiKeyRepository 验证该 Key 是否为系统内有效 Key（sha256 hash 比对数据库）
  3. 鉴权通过后，用 .env 中的 ANTHROPIC_API_KEY 替换，透传到 Anthropic 官方 API
  4. 非流式响应：解析返回体中的 usage 字段，写入 token_usages 表

路由映射（/anthropic 前缀 -> Anthropic 官方端点）：
  ANY /anthropic/{path:path} -> ANY {ANTHROPIC_BASE_URL}/{path}
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.domain.api_key.aggregate import ApiKey
from src.domain.token_usage.aggregate import TokenUsage
from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.repositories.api_key_repository import ApiKeyRepository
from src.infrastructure.persistence.repositories.token_usage_repository import TokenUsageRepository

from ..dependencies import get_api_key_repository, get_token_usage_repository

router = APIRouter(tags=["anthropic-proxy"])

_bearer = HTTPBearer(auto_error=False)

# 透传时需要过滤掉的逐跳请求头
_HOP_BY_HOP_HEADERS = frozenset({
    "host",
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "upgrade",
})


# ---------------------------------------------------------------------------
# 鉴权：验证系统用户 API Key，返回 ApiKey 聚合根
# ---------------------------------------------------------------------------

def _get_raw_key(
    credentials: HTTPAuthorizationCredentials | None,
    request: Request,
) -> str:
    """从请求头提取明文 API Key，未提供则 401。"""
    if credentials and credentials.credentials:
        return credentials.credentials
    x_api_key = request.headers.get("x-api-key", "")
    if x_api_key:
        return x_api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "type": "error",
            "error": {
                "type": "authentication_error",
                "message": "Missing API key. Provide via 'Authorization: Bearer <key>' or 'x-api-key' header.",
            },
        },
    )


async def _verify_system_api_key(
    plain_key: str,
    api_key_repo: ApiKeyRepository,
) -> ApiKey:
    """验证系统用户 API Key 是否有效，返回 ApiKey 聚合根。"""
    key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
    api_key = await api_key_repo.find_by_hash(key_hash)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "error",
                "error": {
                    "type": "authentication_error",
                    "message": "Invalid API key.",
                },
            },
        )
    if not api_key.is_valid():
        msg = "API key has been revoked." if api_key.status.value == "revoked" else "API key is invalid."
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "error",
                "error": {
                    "type": "authentication_error",
                    "message": msg,
                },
            },
        )
    return api_key


# ---------------------------------------------------------------------------
# Token 计费：从响应体提取 usage 并持久化
# ---------------------------------------------------------------------------

async def _record_token_usage(
    api_key: ApiKey,
    model: str,
    resp_body: dict,
    usage_repo: TokenUsageRepository,
) -> None:
    """从 Anthropic 响应体提取 usage，写入 token_usages 表。

    Anthropic Messages API 响应结构：
      {"usage": {"input_tokens": N, "output_tokens": M}, "model": "..."}
    """
    usage = resp_body.get("usage", {})
    if not usage:
        return

    # Anthropic 用 input_tokens / output_tokens；兼容 OpenAI 的 prompt_tokens / completion_tokens
    prompt_tokens = int(
        usage.get("input_tokens") or usage.get("prompt_tokens") or 0
    )
    completion_tokens = int(
        usage.get("output_tokens") or usage.get("completion_tokens") or 0
    )
    total_tokens = int(
        usage.get("total_tokens") or (prompt_tokens + completion_tokens)
    )

    # 取响应体中的实际模型名（可能比请求时更精确）
    actual_model = resp_body.get("model") or model

    record = TokenUsage.record(
        user_id=api_key.user_id,
        api_key_id=api_key.id,
        model=actual_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
    await usage_repo.save(record)


# ---------------------------------------------------------------------------
# 透传核心
# ---------------------------------------------------------------------------

def _build_proxy_headers(request: Request, anthropic_api_key: str) -> dict:
    """构造转发到 Anthropic 的请求头：过滤逐跳头，注入 Anthropic API Key。"""
    headers = {}
    for name, value in request.headers.items():
        if name.lower() in _HOP_BY_HOP_HEADERS:
            continue
        # 过滤掉客户端传来的鉴权头，由代理统一注入
        if name.lower() in ("authorization", "x-api-key"):
            continue
        headers[name] = value
    # 注入从 .env 读取的 Anthropic API Key
    headers["x-api-key"] = anthropic_api_key
    return headers


def _is_stream_request(request: Request, body: bytes) -> bool:
    """判断是否为流式请求（仅对 JSON body 的 POST 请求检测 stream 字段）。"""
    content_type = request.headers.get("content-type", "")
    if request.method == "POST" and "application/json" in content_type and body:
        try:
            payload = json.loads(body)
            return bool(payload.get("stream", False))
        except Exception:
            pass
    return False


def _get_request_model(body: bytes) -> str:
    """从请求体中提取 model 字段，用于 token 记录的 fallback。"""
    try:
        return str(json.loads(body).get("model", "unknown"))
    except Exception:
        return "unknown"


async def _proxy(
    method: str,
    upstream_path: str,
    request: Request,
    body: bytes,
    api_key_entity: ApiKey,
    anthropic_api_key: str,
    base_url: str,
    usage_repo: TokenUsageRepository,
) -> StreamingResponse | JSONResponse:
    base = base_url.rstrip("/")
    url = f"{base}/{upstream_path.lstrip('/')}"
    headers = _build_proxy_headers(request, anthropic_api_key)
    params = dict(request.query_params)
    stream = _is_stream_request(request, body)

    if stream:
        # 流式模式：直接透传字节流，不统计 token（SSE 格式解析复杂度高）
        async def generate() -> AsyncIterator[bytes]:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    method,
                    url,
                    headers=headers,
                    content=body,
                    params=params,
                ) as resp:
                    async for chunk in resp.aiter_bytes():
                        if chunk:
                            yield chunk

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # 非流式：完整拿到响应后解析 usage
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.request(
            method,
            url,
            headers=headers,
            content=body,
            params=params,
        )

    # 回传 anthropic-* 响应头
    resp_headers = {
        k: v for k, v in resp.headers.items()
        if k.lower().startswith("anthropic-")
    }

    try:
        resp_body = resp.json()
    except Exception:
        resp_body = resp.text

    # 仅在成功响应时记录 token 消耗
    if resp.status_code == 200 and isinstance(resp_body, dict):
        request_model = _get_request_model(body)
        try:
            await _record_token_usage(api_key_entity, request_model, resp_body, usage_repo)
        except Exception:
            # token 记录失败不影响正常响应
            pass

    return JSONResponse(
        content=resp_body,
        status_code=resp.status_code,
        headers=resp_headers,
    )


# ---------------------------------------------------------------------------
# 通用透传路由
# ---------------------------------------------------------------------------

@router.api_route(
    "/anthropic/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    response_model=None,
)
async def proxy_anthropic(
    path: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    api_key_repo: ApiKeyRepository = Depends(get_api_key_repository),
    usage_repo: TokenUsageRepository = Depends(get_token_usage_repository),
) -> Response:
    """通用透传：验证系统用户 API Key 后，用 .env 中的 ANTHROPIC_API_KEY 转发到上游。

    客户端传入的是系统颁发的 API Key（sk-xxx），代理替换为真实 Anthropic Key 后转发。
    非流式调用会自动统计并记录 token 消耗。
    """
    # 1. 提取客户端传来的系统 API Key
    plain_key = _get_raw_key(credentials, request)

    # 2. 验证系统 API Key 有效性，取回聚合根
    api_key_entity = await _verify_system_api_key(plain_key, api_key_repo)

    # 3. 读取 .env 中的 Anthropic 配置
    settings = get_settings()
    anthropic_api_key = settings.anthropic_api_key
    anthropic_base_url = settings.anthropic_base_url

    if not anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "type": "error",
                "error": {
                    "type": "service_unavailable",
                    "message": "Anthropic API key not configured on server.",
                },
            },
        )

    # 4. 透传请求（非流式自动记录 token 消耗）
    body = await request.body()
    return await _proxy(
        method=request.method,
        upstream_path=path,
        request=request,
        body=body,
        api_key_entity=api_key_entity,
        anthropic_api_key=anthropic_api_key,
        base_url=anthropic_base_url,
        usage_repo=usage_repo,
    )
