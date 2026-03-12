"""ApiKey 仓储接口"""
from abc import ABC, abstractmethod

from ..shared.value_objects import TokenId, UserId
from .aggregate import ApiKey


class IApiKeyRepository(ABC):
    """
    ApiKey 仓储接口

    领域层定义接口，基础设施层实现。
    持久化时只存 key_hash，不存明文。
    """

    @abstractmethod
    async def save(self, api_key: ApiKey) -> None:
        """保存 API Key（新增或更新）"""
        ...

    @abstractmethod
    async def find_by_id(self, api_key_id: TokenId) -> ApiKey | None:
        """根据ID查找 API Key"""
        ...

    @abstractmethod
    async def find_by_hash(self, key_hash: str) -> ApiKey | None:
        """根据哈希查找 API Key（用于鉴权）"""
        ...

    @abstractmethod
    async def find_by_user(self, user_id: UserId) -> list[ApiKey]:
        """查找用户所有 API Key"""
        ...

    @abstractmethod
    async def delete(self, api_key_id: TokenId) -> None:
        """删除 API Key"""
        ...
