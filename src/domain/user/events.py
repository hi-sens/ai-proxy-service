"""User领域事件"""
from dataclasses import dataclass, field
from datetime import datetime

from ..shared.value_objects import UserId


@dataclass(frozen=True)
class DomainEvent:
    """领域事件基类"""
    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    """用户注册事件"""
    user_id: UserId = field(default=None)  # type: ignore[assignment]
    email: str = field(default="")


@dataclass(frozen=True)
class UserLoggedIn(DomainEvent):
    """用户登录事件"""
    user_id: UserId = field(default=None)  # type: ignore[assignment]


@dataclass(frozen=True)
class UserDeactivated(DomainEvent):
    """用户停用事件"""
    user_id: UserId = field(default=None)  # type: ignore[assignment]
