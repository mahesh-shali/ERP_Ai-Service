from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from openai import AuthenticationError, OpenAIError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.agent import build_chat_graph
from app.cache import build_cache
from app.database import fetch_schema, get_engine
from app.openclaw_integration import openclaw_status
from app.schemas import ChatRequest, ChatResponse
from app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    cache = build_cache(settings.redis_url)
    engine = get_engine() if settings.postgres_url else None
    app.state.engine = engine
    app.state.cache = cache
    app.state.chat_graph = None
    if engine is not None and settings.llm_configured:
        api_key = settings.groq_api_key or settings.openai_api_key
        base_url = "https://api.groq.com/openai/v1" if settings.groq_api_key else None
        app.state.chat_graph = build_chat_graph(
            engine=engine,
            model=settings.llm_model,
            api_key=api_key,
            base_url=base_url,
            max_rows=settings.max_result_rows,
            cache=cache,
            schema_cache_seconds=settings.schema_cache_seconds,
            query_cache_seconds=settings.query_cache_seconds,
            serpapi_api_key=settings.serpapi_api_key,
        )
    yield
    await cache.close()
    if engine is not None:
        await engine.dispose()


app = FastAPI(title="ERP AI Service", version="0.1.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-AI-Service-Key"],
)


def require_service_key(
    request: Request,
    x_ai_service_key: Annotated[str | None, Header()] = None,
) -> None:
    configured_key = get_settings().ai_service_api_key
    client_host = request.client.host if request.client else ""
    if client_host in {"127.0.0.1", "::1", "localhost"}:
        return

    if configured_key and x_ai_service_key != configured_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid AI service key.")


def engine() -> AsyncEngine:
    configured_engine = app.state.engine
    if configured_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL is not configured for the AI service.",
        )
    return configured_engine


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/agent/status", dependencies=[Depends(require_service_key)])
async def agent_status():
    settings = get_settings()
    return {
        "agent": "erp-postgres-agent",
        "openaiConfigured": bool(settings.openai_api_key),
        "groqConfigured": bool(settings.groq_api_key),
        "llmProvider": settings.llm_provider,
        "postgresConfigured": bool(settings.postgres_url),
        "configuredDatabaseEnvNames": settings.configured_database_env_names,
        "redisConfigured": bool(settings.redis_url),
        "serpApiConfigured": bool(settings.serpapi_api_key),
        "openClaw": openclaw_status(settings.openclaw_api_key),
        "model": settings.llm_model,
        "loadedEnvFiles": settings.loaded_env_files,
        "checkedEnvFiles": settings.checked_env_files,
        "missing": [
            name
            for name, configured in {
                "OPENAI_API_KEY or GROQ_API_KEY": settings.llm_configured,
                "DATABASE_URL or ConnectionStrings__DefaultConnection": bool(settings.postgres_url),
            }.items()
            if not configured
        ],
    }


@app.get("/api/openclaw/status", dependencies=[Depends(require_service_key)])
async def get_openclaw_status():
    return openclaw_status(get_settings().openclaw_api_key)


@app.get("/api/schema", dependencies=[Depends(require_service_key)])
async def schema(db: Annotated[AsyncEngine, Depends(engine)]):
    schema_text = await app.state.cache.get_or_create(
        "erp-ai:schema",
        get_settings().schema_cache_seconds,
        lambda: fetch_schema(db),
    )
    return {"schema": schema_text}


async def run_agent(request: ChatRequest):
    if app.state.chat_graph is None:
        settings = get_settings()
        missing = []
        if not settings.postgres_url:
            missing.append("DATABASE_URL or ConnectionStrings__DefaultConnection")
        if not settings.llm_configured:
            missing.append("OPENAI_API_KEY or GROQ_API_KEY")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI agent is not configured. Missing: {', '.join(missing) or 'agent graph'}.",
        )

    try:
        result = await app.state.chat_graph.ainvoke({"question": request.message, "thread_id": request.thread_id})
    except AuthenticationError as exc:
        provider = get_settings().llm_provider
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{provider.upper()} rejected the API key. Update the key in the AI service .env file and restart Uvicorn.",
        ) from exc
    except OpenAIError as exc:
        provider = get_settings().llm_provider
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{provider.upper()} request failed: {exc.__class__.__name__}",
        ) from exc

    return ChatResponse(
        answer=result["answer"],
        sql=result["sql"],
        rows=result["rows"],
        thread_id=result["thread_id"],
    )


@app.post("/api/agent/chat", response_model=ChatResponse, dependencies=[Depends(require_service_key)])
async def agent_chat(request: ChatRequest):
    return await run_agent(request)


@app.post("/api/agent/search", response_model=ChatResponse, dependencies=[Depends(require_service_key)])
async def agent_search(request: ChatRequest):
    return await run_agent(request)


@app.post("/api/chat", response_model=ChatResponse, dependencies=[Depends(require_service_key)])
async def chat(request: ChatRequest):
    return await run_agent(request)
