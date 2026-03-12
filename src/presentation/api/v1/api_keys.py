"""API Keys 路由 - 创建、列表、撤销"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from src.application.use_cases.api_key.create_api_key import CreateApiKeyUseCase, CreateApiKeyCommand
from src.application.use_cases.api_key.revoke_api_key import RevokeApiKeyUseCase, RevokeApiKeyCommand
from ..dependencies import (
    get_create_api_key_use_case,
    get_revoke_api_key_use_case,
    get_current_user_id,
    get_api_key_repository,
)
from src.domain.shared.exceptions import TokenNotFoundException, InvalidUserStateException
from src.domain.shared.value_objects import UserId

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    expires_at: Optional[datetime] = None


class CreateApiKeyResponse(BaseModel):
    api_key_id: str
    name: str
    plain_key: str   # 仅此处返回一次
    expires_at: Optional[datetime]


class ApiKeyItem(BaseModel):
    api_key_id: str
    name: str
    status: str
    expires_at: Optional[datetime]
    created_at: datetime


@router.post("", response_model=CreateApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateApiKeyRequest,
    user_id: str = Depends(get_current_user_id),
    use_case: CreateApiKeyUseCase = Depends(get_create_api_key_use_case),
) -> CreateApiKeyResponse:
    """创建 API Key（需登录）"""
    try:
        result = await use_case.execute(
            CreateApiKeyCommand(
                user_id=user_id,
                name=request.name,
                expires_at=request.expires_at,
            )
        )
        return CreateApiKeyResponse(
            api_key_id=result.api_key_id,
            name=result.name,
            plain_key=result.plain_key,
            expires_at=result.expires_at,
        )
    except InvalidUserStateException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)


@router.get("", response_model=List[ApiKeyItem])
async def list_api_keys(
    user_id: str = Depends(get_current_user_id),
    api_key_repo=Depends(get_api_key_repository),
) -> List[ApiKeyItem]:
    """获取当前用户的所有 API Key"""
    api_keys = await api_key_repo.find_by_user(UserId.from_string(user_id))
    return [
        ApiKeyItem(
            api_key_id=str(k.id),
            name=k.name,
            status=k.status.value,
            expires_at=k.expires_at.value if k.expires_at else None,
            created_at=k.created_at.value,
        )
        for k in api_keys
    ]


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    api_key_id: str,
    user_id: str = Depends(get_current_user_id),
    use_case: RevokeApiKeyUseCase = Depends(get_revoke_api_key_use_case),
) -> None:
    """撤销指定 API Key"""
    try:
        await use_case.execute(RevokeApiKeyCommand(api_key_id=api_key_id, user_id=user_id))
    except TokenNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
