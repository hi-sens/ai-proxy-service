"""LLM 服务实现 - 基于 LiteLLM 统一路由

路由规则：
- 本地模型（local_models）：model 前缀补 ollama/，走本地 Ollama
- API 模型（model_api_bases）：model 前缀补 openai/，走 OpenAI 兼容代理

绕过系统代理：设置 NO_PROXY 环境变量，LiteLLM 内部 httpx 会跳过代理。
"""
import os
from typing import Any, AsyncIterator, Dict, List, Optional
import litellm
from src.domain.services.llm_service import ILLMService
from ..config.settings import get_settings

settings = get_settings()

# 将所有 API 模型的域名加入 NO_PROXY，让 LiteLLM 内部 httpx 直连，绕过系统代理
_api_hosts = ",".join(
    __import__("urllib.parse", fromlist=["urlparse"]).urlparse(base).hostname or ""
    for base in settings.model_api_bases.values()
    if base
)
if _api_hosts:
    for _var in ("NO_PROXY", "no_proxy"):
        existing = os.environ.get(_var, "")
        combined = ",".join(filter(None, [existing, _api_hosts]))
        os.environ[_var] = combined


class LiteLLMService(ILLMService):
    """
    LLM 服务实现（LiteLLM 统一路由）

    业务层只传裸模型名，无需感知底层差异。
    """

    def _is_local_model(self, model: str) -> bool:
        return model in settings.local_models or model.startswith("ollama/")

    def _resolve_model_and_kwargs(self, model: str) -> Dict[str, Any]:
        """将裸模型名解析为 LiteLLM model 字符串 + 额外 kwargs"""
        if self._is_local_model(model):
            bare = model.removeprefix("ollama/")
            return {"model": f"ollama/{bare}"}
        # API 模型：用 openai/ 前缀走 OpenAI 兼容协议
        api_base = settings.model_api_bases.get(model)
        if not api_base:
            raise ValueError(f"模型 {model!r} 未在 model_api_bases 中配置 base_url")
        api_key = settings.anthropic_api_key or "sk-placeholder"
        return {
            "model": f"openai/{model}",
            "api_base": api_base.rstrip("/") + "/v1",
            "api_key": api_key,
        }

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """非流式调用"""
        extra = self._resolve_model_and_kwargs(model)
        kwargs: Dict[str, Any] = {
            **extra,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        response = await litellm.acompletion(**kwargs)
        choice = response.choices[0]
        return {
            "content": choice.message.content or "",
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        }

    async def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """流式调用，逐块 yield 文本片段"""
        extra = self._resolve_model_and_kwargs(model)
        kwargs: Dict[str, Any] = {
            **extra,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        response = await litellm.acompletion(**kwargs)
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    async def list_models(self) -> List[str]:
        """获取可用模型列表（来自配置）"""
        return settings.available_models
