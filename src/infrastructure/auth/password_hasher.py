"""密码哈希服务"""
import bcrypt


class PasswordHasher:
    """bcrypt 密码哈希服务"""

    def hash(self, password: str) -> str:
        """哈希密码"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
