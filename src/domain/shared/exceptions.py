"""领域异常定义"""


class DomainException(Exception):
    """领域异常基类"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class UserNotFoundException(DomainException):
    """用户未找到"""
    def __init__(self, user_id: str):
        super().__init__(f"User not found: {user_id}")


class UserAlreadyExistsException(DomainException):
    """用户已存在"""
    def __init__(self, email: str):
        super().__init__(f"User already exists: {email}")


class InvalidCredentialsException(DomainException):
    """认证失败"""
    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class TokenNotFoundException(DomainException):
    """令牌未找到"""
    def __init__(self, token_id: str):
        super().__init__(f"Token not found: {token_id}")


class TokenInvalidException(DomainException):
    """令牌无效或已过期"""
    def __init__(self) -> None:
        super().__init__("Token is invalid or expired")


class TokenRevokedException(DomainException):
    """令牌已撤销"""
    def __init__(self) -> None:
        super().__init__("Token has been revoked")


class InvalidUserStateException(DomainException):
    """无效的用户状态"""
    pass
