"""ApiKey 聚合值对象"""
from dataclasses import dataclass
from enum import Enum


class ApiKeyStatus(str, Enum):
    """API Key 状态"""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
