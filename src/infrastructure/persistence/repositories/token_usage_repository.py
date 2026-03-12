"""TokenUsage 仓储实现"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.shared.value_objects import Timestamp, TokenId, UserId
from src.domain.token_usage.aggregate import TokenUsage
from src.domain.token_usage.repository import ITokenUsageRepository, TokenUsageSummary
from src.domain.token_usage.value_objects import TokenUsageId

from ..models.token_usage_model import TokenUsageModel


class TokenUsageRepository(ITokenUsageRepository):
    """TokenUsage 仓储实现（PostgreSQL + SQLAlchemy）"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, usage: TokenUsage) -> None:
        """保存一条消耗记录"""
        self._session.add(self._to_model(usage))
        await self._session.commit()

    async def find_by_user(
        self,
        user_id: UserId,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TokenUsage]:
        """查询用户的消耗明细（分页，按时间倒序）"""
        stmt = (
            select(TokenUsageModel)
            .where(TokenUsageModel.user_id == user_id.value)
            .order_by(TokenUsageModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def find_by_api_key(
        self,
        api_key_id: TokenId,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TokenUsage]:
        """查询某个 API Key 的消耗明细"""
        stmt = (
            select(TokenUsageModel)
            .where(TokenUsageModel.api_key_id == api_key_id.value)
            .order_by(TokenUsageModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def summarize_by_user(self, user_id: UserId) -> TokenUsageSummary:
        """汇总用户的 token 消耗"""
        stmt = select(
            func.coalesce(func.sum(TokenUsageModel.prompt_tokens), 0),
            func.coalesce(func.sum(TokenUsageModel.completion_tokens), 0),
            func.coalesce(func.sum(TokenUsageModel.total_tokens), 0),
            func.count(TokenUsageModel.id),
        ).where(TokenUsageModel.user_id == user_id.value)
        result = await self._session.execute(stmt)
        row = result.one()
        return TokenUsageSummary(
            total_prompt_tokens=int(row[0]),
            total_completion_tokens=int(row[1]),
            total_tokens=int(row[2]),
            call_count=int(row[3]),
        )

    async def summarize_by_api_key(self, api_key_id: TokenId) -> TokenUsageSummary:
        """汇总某个 API Key 的 token 消耗"""
        stmt = select(
            func.coalesce(func.sum(TokenUsageModel.prompt_tokens), 0),
            func.coalesce(func.sum(TokenUsageModel.completion_tokens), 0),
            func.coalesce(func.sum(TokenUsageModel.total_tokens), 0),
            func.count(TokenUsageModel.id),
        ).where(TokenUsageModel.api_key_id == api_key_id.value)
        result = await self._session.execute(stmt)
        row = result.one()
        return TokenUsageSummary(
            total_prompt_tokens=int(row[0]),
            total_completion_tokens=int(row[1]),
            total_tokens=int(row[2]),
            call_count=int(row[3]),
        )

    # -------- 内部转换 --------

    def _to_model(self, usage: TokenUsage) -> TokenUsageModel:
        return TokenUsageModel(
            id=usage.id.value,
            user_id=usage.user_id.value,
            api_key_id=usage.api_key_id.value,
            model=usage.model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            created_at=usage.created_at.value,
        )

    def _to_domain(self, model: TokenUsageModel) -> TokenUsage:
        return TokenUsage(
            id=TokenUsageId(value=UUID(str(model.id))),
            user_id=UserId(value=UUID(str(model.user_id))),
            api_key_id=TokenId(value=UUID(str(model.api_key_id))),
            model=str(model.model),
            prompt_tokens=int(model.prompt_tokens),  # type: ignore[arg-type]
            completion_tokens=int(model.completion_tokens),  # type: ignore[arg-type]
            total_tokens=int(model.total_tokens),  # type: ignore[arg-type]
            created_at=Timestamp(value=datetime.fromisoformat(str(model.created_at))),
        )
