"""User聚合根"""
from dataclasses import dataclass, field
from typing import List
from ..shared.value_objects import UserId, Timestamp
from ..shared.exceptions import InvalidUserStateException
from .value_objects import Email, HashedPassword
from .events import DomainEvent, UserRegistered, UserDeactivated


@dataclass
class User:
    """
    User聚合根

    职责：
    1. 管理用户生命周期（注册、停用）
    2. 持有用户身份信息
    3. 发布领域事件

    不依赖任何外部框架，纯领域逻辑。
    密码哈希由应用层或基础设施层处理后传入。
    """
    id: UserId
    email: Email
    hashed_password: HashedPassword
    username: str
    is_active: bool
    created_at: Timestamp
    updated_at: Timestamp
    _events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)

    @classmethod
    def register(
        cls,
        email: str,
        hashed_password: str,
        username: str,
    ) -> 'User':
        """
        工厂方法 - 注册新用户

        业务规则：
        - 邮箱格式必须合法
        - 用户名不能为空
        """
        if not username or not username.strip():
            raise InvalidUserStateException("Username cannot be empty")

        user = cls(
            id=UserId.generate(),
            email=Email(value=email),
            hashed_password=HashedPassword(value=hashed_password),
            username=username.strip(),
            is_active=True,
            created_at=Timestamp.now(),
            updated_at=Timestamp.now(),
        )
        user._add_event(UserRegistered(user_id=user.id, email=email))
        return user

    def deactivate(self) -> None:
        """停用用户"""
        if not self.is_active:
            return
        self.is_active = False
        self.updated_at = Timestamp.now()
        self._add_event(UserDeactivated(user_id=self.id))

    def _add_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    @property
    def events(self) -> List[DomainEvent]:
        return self._events.copy()

    def clear_events(self) -> None:
        self._events.clear()
