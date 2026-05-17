from app.settings import Settings


def test_settings_accepts_openai_alias():
    settings = Settings(OpenAI__ApiKey="test-key")

    assert settings.openai_api_key == "test-key"


def test_settings_accepts_groq_alias_and_prefers_groq_provider():
    settings = Settings(OpenAI__ApiKey="openai-key", Groq__ApiKey="groq-key")

    assert settings.groq_api_key == "groq-key"
    assert settings.llm_provider == "groq"
    assert settings.llm_model == "llama-3.3-70b-versatile"


def test_settings_accepts_groq_double_underscore_api_key_alias():
    settings = Settings(GROQ__API_KEY="groq-key")

    assert settings.groq_api_key == "groq-key"


def test_settings_accepts_connection_string_alias():
    settings = Settings(ConnectionStrings__DefaultConnection="Host=db;Database=erp;Username=user")

    assert settings.postgres_url == "Host=db;Database=erp;Username=user"


def test_settings_accepts_render_postgres_aliases():
    settings = Settings(POSTGRES_URL="postgres://user:pass@host:5432/db")

    assert settings.postgres_url == "postgres://user:pass@host:5432/db"


def test_settings_accepts_pg_connection_string_alias():
    settings = Settings(PG_CONNECTION_STRING="Host=db;Database=erp;Username=user")

    assert settings.postgres_url == "Host=db;Database=erp;Username=user"


def test_settings_accepts_serpapi_alias():
    settings = Settings(SERPAPI_API_KEY="serp-key")

    assert settings.serpapi_api_key == "serp-key"


def test_settings_accepts_openclaw_alias():
    settings = Settings(OPENCLAW_API_KEY="cmdop-key")

    assert settings.openclaw_api_key == "cmdop-key"


def test_settings_uses_default_ai_service_key():
    settings = Settings()

    assert settings.ai_service_api_key == "dev-internal-ai-key-change-me"


def test_settings_accepts_render_port_and_host():
    settings = Settings(PORT="10000", HOST="0.0.0.0")

    assert settings.port == 10000
    assert settings.uvicorn_host == "0.0.0.0"


def test_settings_uses_render_host_when_port_exists(monkeypatch):
    monkeypatch.setenv("PORT", "10000")
    settings = Settings()

    assert settings.uvicorn_host == "0.0.0.0"


def test_settings_keeps_local_host_without_render_port(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    settings = Settings()

    assert settings.uvicorn_host == "127.0.0.1"


def test_settings_accepts_allowed_origins_alias():
    settings = Settings(ALLOWED_ORIGINS="https://erp-frontend-rust.vercel.app,http://localhost:3000")

    assert settings.cors_origins == ["https://erp-frontend-rust.vercel.app", "http://localhost:3000"]
