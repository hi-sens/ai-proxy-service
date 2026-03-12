"""LLM 领域服务接口"""
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional


class ILLMService(ABC):
    """
    LLM 服务接口

    职责：
    - 统一封装对本地模型（Ollama）和闭源 API（Claude 等）的调用
    - 不关心具体实现（LiteLLM / LangGraph 等）
    - 基础设施层负责实现
    """

    @abstractmethod
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        调用大模型（非流式）

        参数：
            model: 模型名称，如 "qwen2.5:14b" 或 "claude-3-5-sonnet-20241022"
            messages: OpenAI 格式消息列表
            temperature: 采样温度
            max_tokens: 最大输出 token 数

        返回：
            {"content": str, "model": str, "usage": {...}}
        """
        ...

    @abstractmethod
    def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        流式调用大模型，逐块 yield 文本片段
        返回 AsyncIterator[str]，实现类应为 async def（异步生成器）
        """
        ...

    @abstractmethod
    async def list_models(self) -> List[str]:
        """
        获取当前可用模型列表（本地 + 云端）
        """
        ...
