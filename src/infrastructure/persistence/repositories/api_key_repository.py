"""ApiKey 仓储实现"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.api_key.aggregate import ApiKey
from src.domain.api_key.repository import IApiKeyRepository
from src.domain.api_key.value_objects import ApiKeyStatus
from src.domain.shared.value_objects import Timestamp, TokenId, UserId

from ..models.api_key_model import ApiKeyModel


class ApiKeyRepository(IApiKeyRepository):
    """ApiKey 仓储实现（PostgreSQL + SQLAlchemy）"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, api_key: ApiKey) -> None:
        """保存 API Key（新增或更新）"""
        stmt = select(ApiKeyModel).where(ApiKeyModel.id == api_key.id.value)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.status = api_key.status.value  # type: ignore[assignment]
            existing.updated_at = api_key.updated_at.value  # type: ignore[assignment]
        else:
            self._session.add(self._to_model(api_key))

        await self._session.commit()

    async def find_by_id(self, api_key_id: TokenId) -> ApiKey | None:
        """根据ID查找 API Key"""
        stmt = select(ApiKeyModel).where(ApiKeyModel.id == api_key_id.value)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_by_hash(self, key_hash: str) -> ApiKey | None:
        """根据哈希查找 API Key（用于鉴权）"""
        stmt = select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_by_user(self, user_id: UserId) -> list[ApiKey]:
        """查找用户所有 API Key"""
        stmt = select(ApiKeyModel).where(ApiKeyModel.user_id == user_id.value)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def delete(self, api_key_id: TokenId) -> None:
        """删除 API Key"""
        stmt = select(ApiKeyModel).where(ApiKeyModel.id == api_key_id.value)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            await self._session.delete(model)
            await self._session.commit()

    def _to_model(self, api_key: ApiKey) -> ApiKeyModel:
        return ApiKeyModel(
            id=api_key.id.value,
            user_id=api_key.user_id.value,
            name=api_key.name,
            key_hash=api_key.key_hash,
            status=api_key.status.value,
            expires_at=api_key.expires_at.value if api_key.expires_at else None,
            created_at=api_key.created_at.value,
            updated_at=api_key.updated_at.value,
        )

    def _to_domain(self, model: ApiKeyModel) -> ApiKey:
        expires_raw = model.expires_at
        expires_ts: Timestamp | None = (
            Timestamp(value=datetime.fromisoformat(str(expires_raw)))
            if expires_raw is not None else None
        )
        return ApiKey(
            id=TokenId(value=UUID(str(model.id))),
            user_id=UserId(value=UUID(str(model.user_id))),
            name=str(model.name),
            key_hash=str(model.key_hash),
            status=ApiKeyStatus(str(model.status)),
            expires_at=expires_ts,
            created_at=Timestamp(value=datetime.fromisoformat(str(model.created_at))),
            updated_at=Timestamp(value=datetime.fromisoformat(str(model.updated_at))),
        )
