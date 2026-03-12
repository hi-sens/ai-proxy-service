"""LLM 代理路由 - 统一调用本地/云端模型"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from src.application.use_cases.llm.chat import ChatCommand, ChatUseCase
from src.domain.shared.exceptions import TokenInvalidException, TokenRevokedException

from ..dependencies import get_chat_use_case

router = APIRouter(prefix="/api/v1/llm", tags=["llm"])

_api_key_bearer = HTTPBearer(scheme_name="API Key", description="在此填入你的 API Key")


class Message(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    model: str = Field(..., description="模型名称，如 ollama/qwen2.5:14b 或 claude-3-5-sonnet-20241022")
    messages: list[Message]
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    stream: bool = False


class ChatResponse(BaseModel):
    content: str
    model: str
    usage: dict[str, Any] = {}


class ModelListResponse(BaseModel):
    models: list[str]


def _extract_key(credentials: HTTPAuthorizationCredentials) -> str:
    """从 HTTPBearer 凭证提取 API Key"""
    return credentials.credentials


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    credentials: HTTPAuthorizationCredentials = Depends(_api_key_bearer),
    use_case: ChatUseCase = Depends(get_chat_use_case),
) -> ChatResponse:
    """调用大模型（非流式）。Authorization: Bearer <api_key>"""
    plain_key = _extract_key(credentials)
    try:
        result = await use_case.execute(
            ChatCommand(
                plain_key=plain_key,
                model=request.model,
                messages=[m.model_dump() for m in request.messages],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        )
        return ChatResponse(content=result.content, model=result.model, usage=result.usage)
    except (TokenInvalidException, TokenRevokedException) as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    credentials: HTTPAuthorizationCredentials = Depends(_api_key_bearer),
    use_case: ChatUseCase = Depends(get_chat_use_case),
) -> StreamingResponse:
    """流式调用大模型。返回 text/event-stream。"""
    plain_key = _extract_key(credentials)

    async def generate() -> Any:
        try:
            async for chunk in use_case.execute_stream(
                ChatCommand(
                    plain_key=plain_key,
                    model=request.model,
                    messages=[m.model_dump() for m in request.messages],
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                )
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except (TokenInvalidException, TokenRevokedException) as e:
            yield f"data: [ERROR] {e.message}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    credentials: HTTPAuthorizationCredentials = Depends(_api_key_bearer),
    use_case: ChatUseCase = Depends(get_chat_use_case),
) -> ModelListResponse:
    """获取可用模型列表（需要有效的 API Key）"""
    plain_key = _extract_key(credentials)
    try:
        # 验证 API Key 有效性
        await use_case._validate_api_key(plain_key)
        models = await use_case._llm_service.list_models()
        return ModelListResponse(models=models)
    except (TokenInvalidException, TokenRevokedException) as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)
