"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from .api.v1.auth import router as auth_router
from .api.v1.api_keys import router as api_keys_router
from .api.v1.llm import router as llm_router
from ..infrastructure.config.settings import get_settings

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(api_keys_router)
app.include_router(llm_router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # 添加 API Key Bearer 认证方案，让 Swagger UI 显示 Authorize 按钮
    schema["components"]["securitySchemes"] = {
        "API Key": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API Key",
            "description": "在此填入通过 POST /api/v1/api-keys 创建的 API Key（格式：sk-xxx）",
        }
    }
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi


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
