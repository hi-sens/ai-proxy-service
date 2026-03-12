"""撤销 API Key 用例"""
from dataclasses import dataclass
from src.domain.api_key.repository import IApiKeyRepository
from src.domain.shared.value_objects import TokenId
from src.domain.shared.exceptions import TokenNotFoundException


@dataclass
class RevokeApiKeyCommand:
    """撤销 API Key 命令"""
    api_key_id: str
    user_id: str  # 只能撤销自己的 API Key


class RevokeApiKeyUseCase:
    """撤销 API Key 用例"""

    def __init__(self, api_key_repository: IApiKeyRepository) -> None:
        self._api_key_repo = api_key_repository

    async def execute(self, command: RevokeApiKeyCommand) -> None:
        """执行撤销"""
        api_key_id = TokenId.from_string(command.api_key_id)
        api_key = await self._api_key_repo.find_by_id(api_key_id)

        if not api_key or str(api_key.user_id) != command.user_id:
            raise TokenNotFoundException(command.api_key_id)

        api_key.revoke()
        await self._api_key_repo.save(api_key)
