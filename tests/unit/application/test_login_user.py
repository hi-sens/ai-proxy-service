"""LoginUserUseCase 单元测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.application.use_cases.user.login_user import LoginUserCommand, LoginUserResult, LoginUserUseCase
from src.domain.shared.exceptions import InvalidCredentialsException
from src.domain.user.aggregate import User


def _make_user(username: str, hashed_password: str) -> User:
    """构造测试用 User 聚合根（绕过邮箱校验，使用用户名登录）"""
    return User.register(
        email="hello@example.com",
        hashed_password=hashed_password,
        username=username,
    )


class TestLoginUserUseCase:
    """LoginUserUseCase 测试套件"""

    def _build_use_case(
        self,
        user=None,
        password_verify_result: bool = True,
        access_token: str = "test-jwt-token",
    ) -> LoginUserUseCase:
        """构建带 Mock 依赖的用例"""
        user_repo = AsyncMock()
        user_repo.find_by_username = AsyncMock(return_value=user)
        user_repo.find_by_email = AsyncMock(return_value=user)

        password_hasher = MagicMock()
        password_hasher.verify = MagicMock(return_value=password_verify_result)

        jwt_service = MagicMock()
        jwt_service.create_token = MagicMock(return_value=access_token)

        return LoginUserUseCase(
            user_repository=user_repo,
            password_hasher=password_hasher,
            jwt_service=jwt_service,
        ), user_repo, password_hasher, jwt_service

    # ------------------------------------------------------------------
    # 正常登录
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_login_with_username_success(self):
        """使用用户名 hello + 密码 12345678 登录成功"""
        hashed = "hashed_12345678"
        user = _make_user("hello", hashed)
        use_case, user_repo, password_hasher, jwt_service = self._build_use_case(
            user=user,
            password_verify_result=True,
            access_token="jwt-abc123",
        )

        command = LoginUserCommand(identifier="hello", password="12345678")
        result = await use_case.execute(command)

        assert isinstance(result, LoginUserResult)
        assert result.username == "hello"
        assert result.access_token == "jwt-abc123"
        assert result.user_id == str(user.id)
        assert result.email == "hello@example.com"

        # 验证依赖调用
        user_repo.find_by_username.assert_called_once_with("hello")
        password_hasher.verify.assert_called_once_with("12345678", hashed)
        jwt_service.create_token.assert_called_once_with(str(user.id))

    @pytest.mark.asyncio
    async def test_login_with_email_success(self):
        """使用邮箱 hello@example.com + 密码 12345678 登录成功"""
        hashed = "hashed_12345678"
        user = _make_user("hello", hashed)
        use_case, user_repo, password_hasher, jwt_service = self._build_use_case(
            user=user,
            password_verify_result=True,
            access_token="jwt-xyz789",
        )

        command = LoginUserCommand(identifier="hello@example.com", password="12345678")
        result = await use_case.execute(command)

        assert result.username == "hello"
        assert result.access_token == "jwt-xyz789"
        user_repo.find_by_email.assert_called_once()

    # ------------------------------------------------------------------
    # 用户不存在
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_login_user_not_found_raises(self):
        """用户名不存在时应抛出 InvalidCredentialsException"""
        use_case, _, _, _ = self._build_use_case(user=None)

        command = LoginUserCommand(identifier="hello", password="12345678")
        with pytest.raises(InvalidCredentialsException):
            await use_case.execute(command)

    # ------------------------------------------------------------------
    # 密码错误
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises(self):
        """密码错误时应抛出 InvalidCredentialsException"""
        user = _make_user("hello", "hashed_12345678")
        use_case, _, _, _ = self._build_use_case(
            user=user,
            password_verify_result=False,
        )

        command = LoginUserCommand(identifier="hello", password="wrong_password")
        with pytest.raises(InvalidCredentialsException):
            await use_case.execute(command)
