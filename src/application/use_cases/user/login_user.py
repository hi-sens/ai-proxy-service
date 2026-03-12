"""用户登录用例"""
from dataclasses import dataclass

from src.domain.shared.exceptions import InvalidCredentialsException
from src.domain.user.repository import IUserRepository
from src.domain.user.value_objects import Email


@dataclass
class LoginUserCommand:
    """登录命令"""
    identifier: str  # 邮箱或用户名
    password: str


@dataclass
class LoginUserResult:
    """登录结果"""
    user_id: str
    email: str
    username: str
    access_token: str   # JWT 或 session token，由基础设施层生成


class LoginUserUseCase:
    """
    用户登录用例

    职责：
    - 验证邮箱 + 密码
    - 生成访问令牌（JWT）
    """

    def __init__(
        self,
        user_repository: IUserRepository,
        password_hasher: object,
        jwt_service: object,
    ) -> None:
        self._user_repo = user_repository
        self._password_hasher = password_hasher
        self._jwt_service = jwt_service

    async def execute(self, command: LoginUserCommand) -> LoginUserResult:
        """执行登录（支持邮箱或用户名）"""
        user = None
        if "@" in command.identifier:
            try:
                email = Email(value=command.identifier)
                user = await self._user_repo.find_by_email(email)
            except Exception:
                pass
        else:
            user = await self._user_repo.find_by_username(command.identifier)

        if not user:
            raise InvalidCredentialsException()

        if not self._password_hasher.verify(command.password, user.hashed_password.value):  # type: ignore[attr-defined]
            raise InvalidCredentialsException()

        access_token: str = self._jwt_service.create_token(str(user.id))  # type: ignore[attr-defined]

        return LoginUserResult(
            user_id=str(user.id),
            email=str(user.email),
            username=user.username,
            access_token=access_token,
        )
