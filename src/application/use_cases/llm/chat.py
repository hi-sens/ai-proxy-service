"""LLM 代理调用用例"""
import hashlib
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from src.domain.api_key.repository import IApiKeyRepository
from src.domain.services.llm_service import ILLMService
from src.domain.shared.exceptions import TokenInvalidException, TokenRevokedException
from src.domain.token_usage.aggregate import TokenUsage
from src.domain.token_usage.repository import ITokenUsageRepository


@dataclass
class ChatCommand:
    """LLM 调用命令"""
    plain_key: str             # 请求携带的明文 API Key
    model: str                 # 模型名称
    messages: list[dict[str, Any]]
    temperature: float = 0.7
    max_tokens: int | None = None


@dataclass
class ChatResult:
    """LLM 调用结果"""
    content: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)


class ChatUseCase:
    """
    LLM 代理调用用例

    职责：
    - 验证 API Key 有效性
    - 透明转发到 LLM 服务（本地 Ollama 或云端 API）
    - 记录 token 消耗（计费）
    - 返回模型响应
    """

    def __init__(
        self,
        api_key_repository: IApiKeyRepository,
        llm_service: ILLMService,
        token_usage_repository: ITokenUsageRepository | None = None,
    ) -> None:
        self._api_key_repo = api_key_repository
        self._llm_service = llm_service
        self._token_usage_repo = token_usage_repository

    async def execute(self, command: ChatCommand) -> ChatResult:
        """执行非流式调用，并记录 token 消耗"""
        api_key = await self._validate_api_key(command.plain_key)

        result = await self._llm_service.chat(
            model=command.model,
            messages=command.messages,
            temperature=command.temperature,
            max_tokens=command.max_tokens,
        )

        # 记录 token 消耗
        if self._token_usage_repo and api_key is not None:
            usage = result.get("usage", {})
            record = TokenUsage.record(
                user_id=api_key.user_id,
                api_key_id=api_key.id,
                model=result.get("model", command.model),
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )
            await self._token_usage_repo.save(record)

        return ChatResult(
            content=result["content"],
            model=result.get("model", command.model),
            usage=result.get("usage", {}),
        )

    async def execute_stream(
        self,
        command: ChatCommand,
    ) -> AsyncIterator[str]:
        """执行流式调用，逐块 yield 文本。

        注意：流式模式下 LiteLLM 通常不返回 usage，因此不记录 token 消耗。
        如需统计，可改用带 stream_options={"include_usage": True} 的模式。
        """
        await self._validate_api_key(command.plain_key)

        async for chunk in self._llm_service.chat_stream(
            model=command.model,
            messages=command.messages,
            temperature=command.temperature,
            max_tokens=command.max_tokens,
        ):
            yield chunk

    async def _validate_api_key(self, plain_key: str):
        """验证 API Key 有效性，返回 ApiKey 聚合根（供调用方使用）"""
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        api_key = await self._api_key_repo.find_by_hash(key_hash)

        if not api_key:
            raise TokenInvalidException()
        if not api_key.is_valid():
            if api_key.status.value == "revoked":
                raise TokenRevokedException()
            raise TokenInvalidException()

        return api_key
