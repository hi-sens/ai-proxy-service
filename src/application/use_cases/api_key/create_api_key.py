"""创建 API Key 用例"""
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from src.domain.api_key.aggregate import ApiKey
from src.domain.api_key.repository import IApiKeyRepository
from src.domain.shared.value_objects import UserId


@dataclass
class CreateApiKeyCommand:
    """创建 API Key 命令"""
    user_id: str
    name: str
    expires_at: Optional[datetime] = None


@dataclass
class CreateApiKeyResult:
    """创建 API Key 结果"""
    api_key_id: str
    name: str
    plain_key: str   # 仅此处返回一次明文
    expires_at: Optional[datetime]


class CreateApiKeyUseCase:
    """
    创建 API Key 用例

    职责：
    - 生成安全随机 API Key
    - 哈希后持久化
    - 将明文 key 一次性返回给用户
    """

    def __init__(self, api_key_repository: IApiKeyRepository) -> None:
        self._api_key_repo = api_key_repository

    async def execute(self, command: CreateApiKeyCommand) -> CreateApiKeyResult:
        """执行创建 API Key"""
        plain_key = "sk-" + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()

        # 将带时区的 datetime 统一转换为 UTC naive datetime，避免 asyncpg 类型错误
        expires_at = command.expires_at
        if expires_at is not None and expires_at.tzinfo is not None:
            from datetime import timezone
            expires_at = expires_at.astimezone(timezone.utc).replace(tzinfo=None)

        user_id = UserId.from_string(command.user_id)
        api_key = ApiKey.create(
            user_id=user_id,
            name=command.name,
            key_hash=key_hash,
            plain_key=plain_key,
            expires_at=expires_at,
        )
        await self._api_key_repo.save(api_key)

        return CreateApiKeyResult(
            api_key_id=str(api_key.id),
            name=api_key.name,
            plain_key=plain_key,
            expires_at=command.expires_at,
        )
