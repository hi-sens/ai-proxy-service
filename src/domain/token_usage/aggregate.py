"""TokenUsage 聚合根 - 记录单次 LLM 调用的 token 消耗"""
from dataclasses import dataclass

from ..shared.value_objects import Timestamp, TokenId, UserId
from .value_objects import TokenUsageId


@dataclass
class TokenUsage:
    """
    TokenUsage 聚合根

    职责：
    1. 记录一次 LLM 调用消耗的 prompt / completion / total tokens
    2. 关联 API Key 和用户，便于按维度查询
    3. 记录调用模型名称，支持按模型统计
    """
    id: TokenUsageId
    user_id: UserId
    api_key_id: TokenId
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    created_at: Timestamp

    @classmethod
    def record(
        cls,
        user_id: UserId,
        api_key_id: TokenId,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
    ) -> 'TokenUsage':
        """工厂方法 - 创建一条 token 消耗记录"""
        return cls(
            id=TokenUsageId.generate(),
            user_id=user_id,
            api_key_id=api_key_id,
            model=model,
            prompt_tokens=max(0, prompt_tokens),
            completion_tokens=max(0, completion_tokens),
            total_tokens=max(0, total_tokens),
            created_at=Timestamp.now(),
        )
