"""Anthropic API 通用透传代理

鉴权流程：
  1. 从请求头提取系统用户 API Key（Authorization: Bearer <sk-xxx> 或 x-api-key: <sk-xxx>）
  2. 通过 ChatUseCase 验证该 Key 是否为系统内有效 Key（sha256 hash 比对数据库）
  3. 鉴权通过后，用 .env 中的 ANTHROPIC_API_KEY 替换，透传到 Anthropic 官方 API

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

from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.repositories.api_key_repository import ApiKeyRepository

from ..dependencies import get_api_key_repository

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
# 鉴权：验证系统用户 API Key
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
) -> None:
    """验证系统用户 API Key 是否有效（sha256 hash 比对数据库）。"""
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


async def _proxy(
    method: str,
    upstream_path: str,
    request: Request,
    body: bytes,
    api_key: str,
    base_url: str,
) -> StreamingResponse | JSONResponse:
    base = base_url.rstrip("/")
    url = f"{base}/{upstream_path.lstrip('/')}"
    headers = _build_proxy_headers(request, api_key)
    params = dict(request.query_params)
    stream = _is_stream_request(request, body)

    if stream:
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
) -> Response:
    """通用透传：验证系统用户 API Key 后，用 .env 中的 ANTHROPIC_API_KEY 转发到上游。

    客户端传入的是系统颁发的 API Key（sk-xxx），代理替换为真实 Anthropic Key 后转发。
    """
    # 1. 提取客户端传来的系统 API Key
    plain_key = _get_raw_key(credentials, request)

    # 2. 验证系统 API Key 有效性
    await _verify_system_api_key(plain_key, api_key_repo)

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

    # 4. 透传请求
    body = await request.body()
    return await _proxy(
        method=request.method,
        upstream_path=path,
        request=request,
        body=body,
        api_key=anthropic_api_key,
        base_url=anthropic_base_url,
    )
