"""TokenUsage 值对象"""
from dataclasses import dataclass
from uuid import UUID, uuid4

from ..shared.value_objects import EntityId


@dataclass(frozen=True)
class TokenUsageId(EntityId):
    """TokenUsage 记录 ID"""
    pass
