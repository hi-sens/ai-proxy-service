"""ApiKey 领域事件"""
from dataclasses import dataclass, field
from datetime import datetime

from ..shared.value_objects import TokenId, UserId


@dataclass(frozen=True)
class DomainEvent:
    """领域事件基类"""
    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class ApiKeyCreated(DomainEvent):
    """API Key 创建事件"""
    api_key_id: TokenId = field(default=None)  # type: ignore[assignment]
    user_id: UserId = field(default=None)  # type: ignore[assignment]
    name: str = field(default="")


@dataclass(frozen=True)
class ApiKeyRevoked(DomainEvent):
    """API Key 撤销事件"""
    api_key_id: TokenId = field(default=None)  # type: ignore[assignment]
    user_id: UserId = field(default=None)  # type: ignore[assignment]
