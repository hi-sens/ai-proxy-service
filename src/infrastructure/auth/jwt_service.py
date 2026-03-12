"""JWT 服务"""
from datetime import datetime, timedelta
from typing import Optional
import jwt
from ..config.settings import get_settings

settings = get_settings()


class JWTService:
    """JWT 令牌生成与解析服务"""

    def create_token(self, user_id: str) -> str:
        """生成 JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def decode_token(self, token: str) -> Optional[str]:
        """解析 JWT，返回 user_id；无效则返回 None"""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            return str(payload["sub"])
        except jwt.PyJWTError:
            return None
