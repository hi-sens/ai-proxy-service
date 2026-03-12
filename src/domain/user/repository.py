"""User仓储接口"""
from abc import ABC, abstractmethod
from typing import Optional
from ..shared.value_objects import UserId
from .aggregate import User
from .value_objects import Email


class IUserRepository(ABC):
    """
    User仓储接口

    领域层定义接口，基础设施层实现。
    """

    @abstractmethod
    async def save(self, user: User) -> None:
        """保存用户（新增或更新）"""
        ...

    @abstractmethod
    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """根据ID查找用户"""
        ...

    @abstractmethod
    async def find_by_email(self, email: Email) -> Optional[User]:
        """根据邮箱查找用户"""
        ...

    @abstractmethod
    async def exists_by_email(self, email: Email) -> bool:
        """检查邮箱是否已注册"""
        ...

    @abstractmethod
    async def find_by_username(self, username: str) -> Optional[User]:
        """根据用户名查找用户"""
        ...
