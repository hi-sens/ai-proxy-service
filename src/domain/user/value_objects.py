"""User聚合值对象"""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Email:
    """邮箱值对象"""
    value: str

    def __post_init__(self) -> None:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, self.value):
            raise ValueError(f"Invalid email address: {self.value}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class HashedPassword:
    """哈希密码值对象（存储哈希后的密码）"""
    value: str

    def __str__(self) -> str:
        return self.value
