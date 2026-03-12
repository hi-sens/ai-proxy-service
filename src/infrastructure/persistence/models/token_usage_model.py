"""TokenUsage ORM 模型"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from ..database import Base


class TokenUsageModel(Base):
    """Token 消耗记录数据库模型"""
    __tablename__ = "token_usages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    api_key_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    model = Column(String(255), nullable=False, index=True)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<TokenUsageModel(id={self.id}, model={self.model}, "
            f"total_tokens={self.total_tokens})>"
        )
