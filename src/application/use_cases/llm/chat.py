"""LLM 代理调用用例"""
import hashlib
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional
from src.domain.services.llm_service import ILLMService
from src.domain.api_key.repository import IApiKeyRepository
from src.domain.shared.exceptions import TokenInvalidException, TokenRevokedException


@dataclass
class ChatCommand:
    """LLM 调用命令"""
    plain_key: str             # 请求携带的明文 API Key
    model: str                 # 模型名称
    messages: List[Dict[str, Any]]
    temperature: float = 0.7
    max_tokens: Optional[int] = None


@dataclass
class ChatResult:
    """LLM 调用结果"""
    content: str
    model: str
    usage: Dict[str, Any] = field(default_factory=dict)


class ChatUseCase:
    """
    LLM 代理调用用例

    职责：
    - 验证 API Key 有效性
    - 透明转发到 LLM 服务（本地 Ollama 或云端 API）
    - 返回模型响应
    """

    def __init__(
        self,
        api_key_repository: IApiKeyRepository,
        llm_service: ILLMService,
    ) -> None:
        self._api_key_repo = api_key_repository
        self._llm_service = llm_service

    async def execute(self, command: ChatCommand) -> ChatResult:
        """执行非流式调用"""
        await self._validate_api_key(command.plain_key)

        result = await self._llm_service.chat(
            model=command.model,
            messages=command.messages,
            temperature=command.temperature,
            max_tokens=command.max_tokens,
        )
        return ChatResult(
            content=result["content"],
            model=result.get("model", command.model),
            usage=result.get("usage", {}),
        )

    async def execute_stream(
        self,
        command: ChatCommand,
    ) -> AsyncIterator[str]:
        """执行流式调用，逐块 yield 文本"""
        await self._validate_api_key(command.plain_key)

        async for chunk in self._llm_service.chat_stream(
            model=command.model,
            messages=command.messages,
            temperature=command.temperature,
            max_tokens=command.max_tokens,
        ):
            yield chunk

    async def _validate_api_key(self, plain_key: str) -> None:
        """验证 API Key 有效性"""
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        api_key = await self._api_key_repo.find_by_hash(key_hash)

        if not api_key:
            raise TokenInvalidException()
        if not api_key.is_valid():
            if api_key.status.value == "revoked":
                raise TokenRevokedException()
            raise TokenInvalidException()
