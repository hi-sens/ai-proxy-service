"""认证路由 - 注册、登录"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field

from src.application.use_cases.user.login_user import LoginUserCommand, LoginUserUseCase
from src.application.use_cases.user.register_user import RegisterUserCommand, RegisterUserUseCase
from src.domain.shared.exceptions import InvalidCredentialsException, UserAlreadyExistsException

from ..dependencies import get_login_use_case, get_register_use_case

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    username: str = Field(..., min_length=2, max_length=50)


class RegisterResponse(BaseModel):
    user_id: str
    email: str
    username: str


class LoginRequest(BaseModel):
    identifier: str  # 邮箱或用户名
    password: str


class LoginResponse(BaseModel):
    user_id: str
    email: str
    username: str
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    use_case: RegisterUserUseCase = Depends(get_register_use_case),
) -> RegisterResponse:
    """用户注册"""
    try:
        result = await use_case.execute(
            RegisterUserCommand(
                email=request.email,
                password=request.password,
                username=request.username,
            )
        )
        return RegisterResponse(
            user_id=result.user_id,
            email=result.email,
            username=result.username,
        )
    except UserAlreadyExistsException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    use_case: LoginUserUseCase = Depends(get_login_use_case),
) -> LoginResponse:
    """用户登录（JSON），返回 JWT access_token"""
    try:
        result = await use_case.execute(
            LoginUserCommand(identifier=request.identifier, password=request.password)
        )
        return LoginResponse(
            user_id=result.user_id,
            email=result.email,
            username=result.username,
            access_token=result.access_token,
        )
    except InvalidCredentialsException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)


@router.post("/token", response_model=LoginResponse)
async def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    use_case: LoginUserUseCase = Depends(get_login_use_case),
) -> LoginResponse:
    """OAuth2 密码模式登录（供 Swagger UI Authorize 使用）。username 填邮箱，password 填密码。"""
    try:
        result = await use_case.execute(
            LoginUserCommand(identifier=form_data.username, password=form_data.password)
        )
        return LoginResponse(
            user_id=result.user_id,
            email=result.email,
            username=result.username,
            access_token=result.access_token,
            token_type="bearer",
        )
    except InvalidCredentialsException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)
