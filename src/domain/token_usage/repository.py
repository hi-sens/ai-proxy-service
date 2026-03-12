"""TokenUsage 仓储接口"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..shared.value_objects import TokenId, UserId
from .aggregate import TokenUsage


@dataclass
class TokenUsageSummary:
    """Token 消耗汇总"""
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    call_count: int


class ITokenUsageRepository(ABC):
    """TokenUsage 仓储接口"""

    @abstractmethod
    async def save(self, usage: TokenUsage) -> None:
        """保存一条消耗记录"""
        ...

    @abstractmethod
    async def find_by_user(
        self,
        user_id: UserId,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TokenUsage]:
        """查询用户的消耗明细（分页）"""
        ...

    @abstractmethod
    async def find_by_api_key(
        self,
        api_key_id: TokenId,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TokenUsage]:
        """查询某个 API Key 的消耗明细"""
        ...

    @abstractmethod
    async def summarize_by_user(self, user_id: UserId) -> TokenUsageSummary:
        """汇总用户的 token 消耗"""
        ...

    @abstractmethod
    async def summarize_by_api_key(self, api_key_id: TokenId) -> TokenUsageSummary:
        """汇总某个 API Key 的 token 消耗"""
        ...
