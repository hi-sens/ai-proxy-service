"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from ..infrastructure.config.settings import get_settings
from .api.v1.anthropic_compat import router as anthropic_compat_router
from .api.v1.api_keys import router as api_keys_router
from .api.v1.auth import router as auth_router
from .api.v1.llm import router as llm_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI 代理网关服务 - 统一接入本地模型和闭源大模型 API",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(api_keys_router)
app.include_router(llm_router)
app.include_router(anthropic_compat_router)  # Anthropic Messages API 兼容层


def custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # -----------------------------------------------------------------------
    # 安全方案定义
    # -----------------------------------------------------------------------
    schema.setdefault("components", {})
    schema["components"]["securitySchemes"] = {
        # 1. OAuth2 用户名+密码登录（Swagger UI Authorize 弹窗）
        #    点击 Authorize -> 填入 username/password -> 自动获取 JWT token
        "OAuth2Password": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/api/v1/auth/token",
                    "scopes": {},
                }
            },
            "description": "使用用户名（邮箱）和密码登录，自动获取 JWT Token",
        },
        # 2. JWT Bearer Token（登录后获取的 access_token）
        "BearerJWT": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "登录后获取的 JWT access_token",
        },
        # 3. LLM API Key（通过 x-api-key header 传递）
        "LLMApiKey": {
            "type": "apiKey",
            "in": "header",
            "name": "x-api-key",
            "description": "通过 POST /api/v1/api-keys 创建的 API Key（格式：sk-xxx）",
        },
    }

    # -----------------------------------------------------------------------
    # 按 tag 绑定安全方案
    # -----------------------------------------------------------------------
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            tags = operation.get("tags", [])

            if "llm" in tags:
                # LLM 接口：通过 x-api-key header 鉴权
                operation["security"] = [{"LLMApiKey": []}]
            elif "auth" in tags:
                # auth 接口：无需鉴权
                operation["security"] = []
            elif "anthropic-proxy" in tags:
                # Anthropic 透传接口：通过 x-api-key header 鉴权
                operation["security"] = [{"LLMApiKey": []}]
            else:
                # 其余接口（api-keys 管理等）：使用 OAuth2 / JWT 登录
                operation["security"] = [{"OAuth2Password": []}, {"BearerJWT": []}]

    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi  # type: ignore[method-assign]


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
