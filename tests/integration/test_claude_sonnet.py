"""集成测试：验证 claude-sonnet-4-6 模型通过 LiteLLMService 能正常调用"""
import pytest
from src.infrastructure.llm.litellm_service import LiteLLMService


@pytest.fixture
def service() -> LiteLLMService:
    return LiteLLMService()


MODEL = "claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_claude_sonnet_chat(service: LiteLLMService) -> None:
    """非流式调用：能返回非空内容"""
    response = await service.chat(
        model=MODEL,
        messages=[{"role": "user", "content": "用一句话介绍你自己"}],
        temperature=0.0,
        max_tokens=128,
    )
    assert response["content"], "响应内容不应为空"
    assert response["model"], "响应应包含 model 字段"
    assert response["usage"]["total_tokens"] > 0, "token 数应大于 0"
    print(f"\n[非流式] 模型: {response['model']}")
    print(f"[非流式] 内容: {response['content']}")
    print(f"[非流式] tokens: {response['usage']}")


@pytest.mark.asyncio
async def test_claude_sonnet_chat_stream(service: LiteLLMService) -> None:
    """流式调用：能逐块 yield 文本，拼接后不为空"""
    chunks: list[str] = []
    async for chunk in service.chat_stream(
        model=MODEL,
        messages=[{"role": "user", "content": "用一句话介绍你自己"}],
        temperature=0.0,
        max_tokens=128,
    ):
        chunks.append(chunk)

    full_text = "".join(chunks)
    assert full_text, "流式响应拼接后不应为空"
    assert len(chunks) >= 1, "流式应至少返回一个 chunk"
    print(f"\n[流式] chunk 数: {len(chunks)}")
    print(f"[流式] 完整内容: {full_text}")
