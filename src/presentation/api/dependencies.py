"""依赖注入配置"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.persistence.database import get_db_session
from src.infrastructure.persistence.repositories.user_repository import UserRepository
from src.infrastructure.persistence.repositories.api_key_repository import ApiKeyRepository
from src.infrastructure.llm.litellm_service import LiteLLMService
from src.infrastructure.auth.password_hasher import PasswordHasher
from src.infrastructure.auth.jwt_service import JWTService
from src.application.use_cases.user.register_user import RegisterUserUseCase
from src.application.use_cases.user.login_user import LoginUserUseCase
from src.application.use_cases.api_key.create_api_key import CreateApiKeyUseCase
from src.application.use_cases.api_key.revoke_api_key import RevokeApiKeyUseCase
from src.application.use_cases.llm.chat import ChatUseCase

_bearer = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
_jwt_service = JWTService()
_password_hasher = PasswordHasher()
_llm_service = LiteLLMService()


# ---------- 基础设施依赖 ----------

async def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UserRepository:
    return UserRepository(session)


async def get_api_key_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ApiKeyRepository:
    return ApiKeyRepository(session)


def get_llm_service() -> LiteLLMService:
    return _llm_service


# ---------- 用例依赖 ----------

async def get_register_use_case(
    user_repo: UserRepository = Depends(get_user_repository),
) -> RegisterUserUseCase:
    return RegisterUserUseCase(user_repo, _password_hasher)


async def get_login_use_case(
    user_repo: UserRepository = Depends(get_user_repository),
) -> LoginUserUseCase:
    return LoginUserUseCase(user_repo, _password_hasher, _jwt_service)


async def get_create_api_key_use_case(
    api_key_repo: ApiKeyRepository = Depends(get_api_key_repository),
) -> CreateApiKeyUseCase:
    return CreateApiKeyUseCase(api_key_repo)


async def get_revoke_api_key_use_case(
    api_key_repo: ApiKeyRepository = Depends(get_api_key_repository),
) -> RevokeApiKeyUseCase:
    return RevokeApiKeyUseCase(api_key_repo)


async def get_chat_use_case(
    api_key_repo: ApiKeyRepository = Depends(get_api_key_repository),
    llm_service: LiteLLMService = Depends(get_llm_service),
) -> ChatUseCase:
    return ChatUseCase(api_key_repo, llm_service)


# ---------- JWT 认证依赖 ----------

async def get_current_user_id(
    token: str = Depends(_bearer),
) -> str:
    """从 JWT Bearer token 提取 user_id，验证失败则 401"""
    user_id = _jwt_service.decode_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user_id
