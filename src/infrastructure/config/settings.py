"""应用配置"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    app_name: str = "AI Agent Gateway Service"
    app_version: str = "0.1.0"
    debug: bool = True
    log_level: str = "INFO"

    # 数据库配置
    database_url: str = "postgresql+asyncpg://agent_user:agent_pass@localhost:5432/ai_agent_db"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis配置
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600

    # LiteLLM 配置（统一代理网关）
    litellm_base_url: str = "http://localhost:4000"
    litellm_api_key: str = "sk-1234"

    # Anthropic API Key 和上游地址（Claude）
    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"

    # API 模型的 base_url 映射（ollama/ 开头的模型自动路由，无需配置）
    # 格式：{"模型名": "base_url"}
    # 示例：{"claude-3-5-sonnet-20241022": "https://api.anthropic.com"}
    model_api_bases: dict = {
        "claude-sonnet-4-6": "http://claude.deepmanufactory.com/",
    }

    # JWT 配置
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 天

    # 本地 Ollama 模型列表（业务方用裸名如 "qwen2.5:14b"，自动补 ollama/ 前缀）
    local_models: List[str] = [
        "qwen2.5:14b",
        "llama3.2",
    ]

    # 可用模型列表（本地 + 云端，对外暴露的名称）
    available_models: List[str] = [
        "qwen2.5:14b",
        "llama3.2",
        "claude-sonnet-4-6",
    ]

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
