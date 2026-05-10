from app.database import convert_npgsql_connection_string, normalize_database_url


def test_normalize_postgres_uri_uses_asyncpg_and_ssl():
    url = normalize_database_url("postgres://user:pass@example.com:5432/erp?sslmode=require")

    assert url == "postgresql+asyncpg://user:pass@example.com:5432/erp?ssl=require"


def test_convert_npgsql_connection_string_to_asyncpg_url():
    url = convert_npgsql_connection_string(
        "Host=example.com;Port=5432;Database=erp_db;Username=erp_user;Password=p@ss word;SSL Mode=Require"
    )

    assert url == "postgresql+asyncpg://erp_user:p%40ss%20word@example.com:5432/erp_db?ssl=require"
