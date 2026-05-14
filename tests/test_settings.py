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


def test_settings_accepts_serpapi_alias():
    settings = Settings(SERPAPI_API_KEY="serp-key")

    assert settings.serpapi_api_key == "serp-key"


def test_settings_accepts_openclaw_alias():
    settings = Settings(OPENCLAW_API_KEY="cmdop-key")

    assert settings.openclaw_api_key == "cmdop-key"
