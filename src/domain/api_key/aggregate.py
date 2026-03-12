"""ApiKey 聚合根"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from ..shared.value_objects import TokenId, UserId, Timestamp
from ..shared.exceptions import TokenRevokedException
from .value_objects import ApiKeyStatus
from .events import DomainEvent, ApiKeyCreated, ApiKeyRevoked


@dataclass
class ApiKey:
    """
    ApiKey 聚合根

    职责：
    1. 管理 API Key 生命周期（创建、撤销、过期判断）
    2. 持有明文 key 字符串（仅在创建时返回一次）
    3. 持有关联用户 ID 和有效期
    4. 发布领域事件

    plain_key 仅在 create() 时明文持有，持久化时应只保存哈希。
    """
    id: TokenId
    user_id: UserId
    name: str
    key_hash: str
    status: ApiKeyStatus
    expires_at: Optional[Timestamp]
    created_at: Timestamp
    updated_at: Timestamp
    _events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)
    # 仅在创建时持有明文，用于一次性返回给用户
    _plain_key: Optional[str] = field(default=None, init=False, repr=False)

    @classmethod
    def create(
        cls,
        user_id: UserId,
        name: str,
        key_hash: str,
        plain_key: str,
        expires_at: Optional[datetime] = None,
    ) -> 'ApiKey':
        """
        工厂方法 - 创建新 API Key

        key_hash: 应用层负责哈希后传入
        plain_key: 明文 key，仅此处持有，供上层一次性返回
        """
        if not name or not name.strip():
            from ..shared.exceptions import InvalidUserStateException
            raise InvalidUserStateException("API Key name cannot be empty")

        api_key = cls(
            id=TokenId.generate(),
            user_id=user_id,
            name=name.strip(),
            key_hash=key_hash,
            status=ApiKeyStatus.ACTIVE,
            expires_at=Timestamp(value=expires_at) if expires_at else None,
            created_at=Timestamp.now(),
            updated_at=Timestamp.now(),
        )
        object.__setattr__(api_key, '_plain_key', plain_key)
        api_key._add_event(ApiKeyCreated(api_key_id=api_key.id, user_id=user_id, name=name))
        return api_key

    def revoke(self) -> None:
        """撤销 API Key"""
        if self.status == ApiKeyStatus.REVOKED:
            return
        self.status = ApiKeyStatus.REVOKED
        self.updated_at = Timestamp.now()
        self._add_event(ApiKeyRevoked(api_key_id=self.id, user_id=self.user_id))

    def is_valid(self) -> bool:
        """检查 API Key 是否有效（未撤销且未过期）"""
        if self.status == ApiKeyStatus.REVOKED:
            return False
        if self.expires_at and self.expires_at.value < datetime.utcnow():
            return False
        return True

    @property
    def plain_key(self) -> Optional[str]:
        """明文 API Key（仅创建后可读一次）"""
        return self._plain_key

    def _add_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    @property
    def events(self) -> List[DomainEvent]:
        return self._events.copy()

    def clear_events(self) -> None:
        self._events.clear()
