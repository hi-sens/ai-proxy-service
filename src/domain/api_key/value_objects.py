"""ApiKey 聚合值对象"""
from enum import StrEnum


class ApiKeyStatus(StrEnum):
    """API Key 状态"""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
