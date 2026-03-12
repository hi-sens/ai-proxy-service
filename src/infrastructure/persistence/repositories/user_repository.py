"""User 仓储实现"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.shared.value_objects import Timestamp, UserId
from src.domain.user.aggregate import User
from src.domain.user.repository import IUserRepository
from src.domain.user.value_objects import Email, HashedPassword

from ..models.user_model import UserModel


class UserRepository(IUserRepository):
    """User 仓储实现（PostgreSQL + SQLAlchemy）"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, user: User) -> None:
        """保存用户（新增或更新）"""
        stmt = select(UserModel).where(UserModel.id == user.id.value)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.email = str(user.email)  # type: ignore[assignment]
            existing.hashed_password = str(user.hashed_password)  # type: ignore[assignment]
            existing.username = user.username  # type: ignore[assignment]
            existing.is_active = user.is_active  # type: ignore[assignment]
            existing.updated_at = user.updated_at.value  # type: ignore[assignment]
        else:
            self._session.add(self._to_model(user))

        await self._session.commit()

    async def find_by_id(self, user_id: UserId) -> User | None:
        """根据ID查找用户"""
        stmt = select(UserModel).where(UserModel.id == user_id.value)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_by_email(self, email: Email) -> User | None:
        """根据邮箱查找用户"""
        stmt = select(UserModel).where(UserModel.email == str(email))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def exists_by_email(self, email: Email) -> bool:
        """检查邮箱是否已注册"""
        stmt = select(UserModel.id).where(UserModel.email == str(email))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def find_by_username(self, username: str) -> User | None:
        """根据用户名查找用户"""
        stmt = select(UserModel).where(UserModel.username == username)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    def _to_model(self, user: User) -> UserModel:
        return UserModel(
            id=user.id.value,
            email=str(user.email),
            hashed_password=str(user.hashed_password),
            username=user.username,
            is_active=user.is_active,
            created_at=user.created_at.value,
            updated_at=user.updated_at.value,
        )

    def _to_domain(self, model: UserModel) -> User:
        return User(
            id=UserId(value=UUID(str(model.id))),
            email=Email(value=str(model.email)),
            hashed_password=HashedPassword(value=str(model.hashed_password)),
            username=str(model.username),
            is_active=bool(model.is_active),
            created_at=Timestamp(value=datetime.fromisoformat(str(model.created_at))),
            updated_at=Timestamp(value=datetime.fromisoformat(str(model.updated_at))),
        )
