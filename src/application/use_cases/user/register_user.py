"""用户注册用例"""
from dataclasses import dataclass

from src.domain.shared.exceptions import UserAlreadyExistsException
from src.domain.user.aggregate import User
from src.domain.user.repository import IUserRepository
from src.domain.user.value_objects import Email


@dataclass
class RegisterUserCommand:
    """注册用户命令"""
    email: str
    password: str
    username: str


@dataclass
class RegisterUserResult:
    """注册用户结果"""
    user_id: str
    email: str
    username: str


class RegisterUserUseCase:
    """
    用户注册用例

    职责：
    - 检查邮箱唯一性
    - 哈希密码
    - 创建 User 聚合根并持久化
    """

    def __init__(self, user_repository: IUserRepository, password_hasher: object) -> None:
        self._user_repo = user_repository
        self._password_hasher = password_hasher

    async def execute(self, command: RegisterUserCommand) -> RegisterUserResult:
        """执行注册"""
        email = Email(value=command.email)

        if await self._user_repo.exists_by_email(email):
            raise UserAlreadyExistsException(command.email)

        hashed_pw: str = self._password_hasher.hash(command.password)  # type: ignore[attr-defined]

        user = User.register(
            email=command.email,
            hashed_password=hashed_pw,
            username=command.username,
        )
        await self._user_repo.save(user)

        return RegisterUserResult(
            user_id=str(user.id),
            email=command.email,
            username=command.username,
        )
