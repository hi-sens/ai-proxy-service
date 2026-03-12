# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **AI Agent Gateway Service** — a unified gateway that allows users to access both local inference models (Ollama) and closed-source LLM APIs (Claude, GPT-4, etc.) through a single API.

### Core Business Flow

1. User registers and logs in → receives a JWT access token
2. User creates an API Token (long-lived key for LLM access)
3. User calls `/api/v1/llm/chat` with the API Token in `Authorization: Bearer <token>`
4. The gateway validates the token and transparently routes the request to the target model (Ollama or Claude/GPT)

### Key Domain Concepts

- **User** (`src/domain/user/`): Aggregate root. Handles registration and identity. Password hashing is done in the application layer before calling `User.register()`.
- **ApiToken** (`src/domain/token/`): Aggregate root. Only `token_hash` (SHA-256) is persisted — the plain token is returned once at creation and never stored.
- **ILLMService** (`src/domain/services/llm_service.py`): Domain interface. Infrastructure implements it via LiteLLM, which routes to Ollama (`ollama/<model>`) or cloud APIs transparently.

## DDD Architecture

Strict dependency direction:
```
Presentation → Application → Domain ← Infrastructure
```

**Critical Rule**: Domain layer has zero framework dependencies — pure Python, pure business logic. Infrastructure implements domain interfaces.

### Layer Locations

- **Domain** `src/domain/`: `user/`, `token/`, `services/`, `shared/`
- **Application** `src/application/use_cases/`: `user/`, `token/`, `llm/`
- **Infrastructure** `src/infrastructure/`: `persistence/`, `llm/`, `auth/`, `cache/`, `config/`
- **Presentation** `src/presentation/`: `api/v1/` (auth, tokens, llm routers), `api/dependencies.py`

## Development Commands

### Environment Setup

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
make pre-commit   # install pre-commit hooks
```

### Infrastructure

```bash
make docker-up        # start PostgreSQL, Redis, Ollama, LiteLLM
make init-db          # create database tables
docker exec -it ai-agent-ollama ollama pull qwen2.5:14b
```

### Running the Application

```bash
# Development
uvicorn src.presentation.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn src.presentation.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Testing

```bash
pytest                          # all tests
pytest tests/unit               # unit tests only
pytest tests/integration        # integration tests only
pytest tests/unit/domain/test_user.py                          # single file
pytest tests/unit/domain/test_user.py::TestUser::test_register # single test
pytest --cov=src --cov-report=html                             # with coverage
```

### Code Quality

```bash
make format      # autoflake + isort + black
make lint        # ruff
make type-check  # mypy
make check       # all of the above + tests

# Or individually:
autoflake --in-place --remove-all-unused-imports --remove-unused-variables -r src/ tests/
isort src/ tests/
black src/ tests/
ruff check src/ tests/
mypy src/
```

### Pre-commit Hooks

```bash
make pre-commit          # install
pre-commit run --all-files  # run manually
```

Pre-commit runs: autoflake → isort → black → ruff → mypy → basic file checks.

## Architecture Patterns

### Dependency Injection

Constructor injection via FastAPI `Depends`. All wiring is in `src/presentation/api/dependencies.py`.

```python
class CreateTokenUseCase:
    def __init__(self, token_repository: ITokenRepository) -> None:
        self._token_repo = token_repository

@router.post("")
async def create_token(
    use_case: CreateTokenUseCase = Depends(get_create_token_use_case),
):
    ...
```

### Token Security

API tokens are hashed with SHA-256 before storage. Only the hash is persisted. The plain token is held transiently in `ApiToken._plain_token` and returned once from `CreateTokenUseCase`.

### LLM Model Naming

LiteLLM routes based on model name prefix:
- `ollama/qwen2.5:14b` → local Ollama
- `claude-3-5-sonnet-20241022` → Anthropic API
- `gpt-4o` → OpenAI API

### Domain Events

Aggregates collect events internally and expose them via `.events`. Application layer is responsible for dispatching them after persistence.

```python
user = User.register(email, hashed_pw, username)
await user_repo.save(user)
# user.events contains [UserRegistered(...)]
```

## API Routes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/register` | None | Register new user |
| POST | `/api/v1/auth/login` | None | Login, get JWT |
| POST | `/api/v1/tokens` | JWT | Create API token |
| GET | `/api/v1/tokens` | JWT | List user's tokens |
| DELETE | `/api/v1/tokens/{id}` | JWT | Revoke token |
| POST | `/api/v1/llm/chat` | API Token | Non-streaming LLM call |
| POST | `/api/v1/llm/chat/stream` | API Token | Streaming LLM call (SSE) |
| GET | `/api/v1/llm/models` | API Token | List available models |

## Configuration

All config via `.env` (see `.env.example`). Key settings in `src/infrastructure/config/settings.py`:

- `DATABASE_URL`: PostgreSQL async connection string
- `REDIS_URL`: Redis connection
- `LITELLM_BASE_URL` / `LITELLM_API_KEY`: LiteLLM gateway
- `ANTHROPIC_API_KEY`: For Claude models
- `JWT_SECRET_KEY`: Must be changed in production
- `AVAILABLE_MODELS`: List of routable model names

## Adding New Functionality

### New Use Case
1. Create command/result dataclasses + use case class in `src/application/use_cases/<domain>/`
2. Wire dependencies in `src/presentation/api/dependencies.py`
3. Add route in `src/presentation/api/v1/`

### New Domain Repository
1. Define abstract interface in `src/domain/<domain>/repository.py`
2. Create ORM model in `src/infrastructure/persistence/models/`
3. Implement repository in `src/infrastructure/persistence/repositories/`
4. Register in `src/scripts/init_db.py` imports so tables are created

## Important Notes

- Python version: 3.11+
- Line length: 100 characters
- All functions require type annotations (mypy `disallow_untyped_defs = true`)
- pytest runs with `asyncio_mode = "auto"`
- Database migrations: Alembic is installed but not yet configured — currently using `init_db.py` with `create_all`
