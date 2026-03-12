"""ApiKey ORM 模型"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
import uuid
from ..database import Base


class ApiKeyModel(Base):  # type: ignore[misc]
    """API Key 数据库模型"""
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256 hex
    status = Column(String(20), nullable=False, default="active")
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<ApiKeyModel(id={self.id}, name={self.name}, status={self.status})>"
