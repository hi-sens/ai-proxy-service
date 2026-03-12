"""Token 消耗计费查询路由"""
import hashlib
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from src.domain.shared.exceptions import TokenInvalidException, TokenRevokedException
from src.domain.shared.value_objects import TokenId, UserId
from src.domain.token_usage.repository import TokenUsageSummary
from src.infrastructure.persistence.repositories.api_key_repository import ApiKeyRepository
from src.infrastructure.persistence.repositories.token_usage_repository import TokenUsageRepository

from ..dependencies import get_api_key_repository, get_token_usage_repository

router = APIRouter(prefix="/api/v1/token-usage", tags=["token-usage"])

_bearer = HTTPBearer(scheme_name="API Key", description="在此填入你的 API Key")


# ---------- 响应 Schema ----------

class TokenUsageRecord(BaseModel):
    id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    created_at: str


class TokenUsageSummaryResponse(BaseModel):
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    call_count: int


class TokenUsageListResponse(BaseModel):
    records: list[TokenUsageRecord]
    total: int


# ---------- 辅助：从 API Key 解析出聚合根 ----------

async def _get_api_key_entity(
    credentials: HTTPAuthorizationCredentials,
    api_key_repo: ApiKeyRepository,
):
    plain_key = credentials.credentials
    key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
    api_key = await api_key_repo.find_by_hash(key_hash)
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
    if not api_key.is_valid():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key revoked or expired")
    return api_key


# ---------- 接口 ----------

@router.get("/summary", response_model=TokenUsageSummaryResponse)
async def get_usage_summary(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    api_key_repo: ApiKeyRepository = Depends(get_api_key_repository),
    usage_repo: TokenUsageRepository = Depends(get_token_usage_repository),
) -> TokenUsageSummaryResponse:
    """查询当前 API Key 的 token 消耗汇总"""
    api_key = await _get_api_key_entity(credentials, api_key_repo)
    summary = await usage_repo.summarize_by_api_key(api_key.id)
    return TokenUsageSummaryResponse(
        total_prompt_tokens=summary.total_prompt_tokens,
        total_completion_tokens=summary.total_completion_tokens,
        total_tokens=summary.total_tokens,
        call_count=summary.call_count,
    )


@router.get("/records", response_model=TokenUsageListResponse)
async def get_usage_records(
    limit: int = Query(default=20, ge=1, le=100, description="每页条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    api_key_repo: ApiKeyRepository = Depends(get_api_key_repository),
    usage_repo: TokenUsageRepository = Depends(get_token_usage_repository),
) -> TokenUsageListResponse:
    """查询当前 API Key 的 token 消耗明细（分页，按时间倒序）"""
    api_key = await _get_api_key_entity(credentials, api_key_repo)
    records = await usage_repo.find_by_api_key(api_key.id, limit=limit, offset=offset)
    return TokenUsageListResponse(
        records=[
            TokenUsageRecord(
                id=str(r.id),
                model=r.model,
                prompt_tokens=r.prompt_tokens,
                completion_tokens=r.completion_tokens,
                total_tokens=r.total_tokens,
                created_at=str(r.created_at),
            )
            for r in records
        ],
        total=len(records),
    )


@router.get("/summary/user", response_model=TokenUsageSummaryResponse)
async def get_user_usage_summary(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    api_key_repo: ApiKeyRepository = Depends(get_api_key_repository),
    usage_repo: TokenUsageRepository = Depends(get_token_usage_repository),
) -> TokenUsageSummaryResponse:
    """查询当前用户（所有 API Key 合计）的 token 消耗汇总"""
    api_key = await _get_api_key_entity(credentials, api_key_repo)
    summary = await usage_repo.summarize_by_user(api_key.user_id)
    return TokenUsageSummaryResponse(
        total_prompt_tokens=summary.total_prompt_tokens,
        total_completion_tokens=summary.total_completion_tokens,
        total_tokens=summary.total_tokens,
        call_count=summary.call_count,
    )
