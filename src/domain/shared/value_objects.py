"""共享值对象 - 跨聚合使用的值对象"""
from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar
from uuid import UUID, uuid4

T = TypeVar('T', bound='EntityId')


@dataclass(frozen=True)
class EntityId:
    """实体ID基类"""
    value: UUID

    @classmethod
    def generate(cls: type[T]) -> T:
        """生成新ID"""
        return cls(value=uuid4())

    @classmethod
    def from_string(cls: type[T], id_str: str) -> T:
        """从字符串创建"""
        return cls(value=UUID(id_str))

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class UserId(EntityId):
    """User ID"""
    pass


@dataclass(frozen=True)
class TokenId(EntityId):
    """API Token ID"""
    pass


@dataclass(frozen=True)
class Timestamp:
    """时间戳值对象"""
    value: datetime

    @classmethod
    def now(cls) -> 'Timestamp':
        """当前时间"""
        return cls(value=datetime.utcnow())

    def __str__(self) -> str:
        return self.value.isoformat()
