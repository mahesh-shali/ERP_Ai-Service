from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.settings import get_settings


def normalize_database_url(url: str) -> str:
    url = url.strip()
    if "=" in url and ";" in url and not url.startswith(("postgres://", "postgresql://", "postgresql+asyncpg://")):
        url = convert_npgsql_connection_string(url)

    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url.removeprefix("postgres://")
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url.removeprefix("postgresql://")

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if "sslmode" in query and "ssl" not in query:
        query["ssl"] = query.pop("sslmode")
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

    return url


def convert_npgsql_connection_string(connection_string: str) -> str:
    values: dict[str, str] = {}
    for part in connection_string.split(";"):
        if not part.strip() or "=" not in part:
            continue
        key, value = part.split("=", 1)
        values[key.strip().lower().replace(" ", "")] = value.strip()

    host = values.get("host") or values.get("server")
    database = values.get("database") or values.get("initialcatalog")
    username = values.get("username") or values.get("userid") or values.get("user")
    password = values.get("password", "")
    port = values.get("port", "5432")
    ssl_mode = values.get("sslmode", values.get("ssl", ""))

    if not host or not database or not username:
        raise ValueError("PostgreSQL connection string must include Host, Database, and Username.")

    auth = quote(username, safe="")
    if password:
        auth += f":{quote(password, safe='')}"

    query = ""
    if ssl_mode and ssl_mode.lower() not in {"disable", "false"}:
        query = "?ssl=require"

    return f"postgresql+asyncpg://{auth}@{host}:{port}/{quote(database, safe='')}{query}"


def get_engine() -> AsyncEngine:
    settings = get_settings()
    if not settings.postgres_url.strip():
        raise RuntimeError("DATABASE_URL or ConnectionStrings__DefaultConnection is not configured.")
    return create_async_engine(normalize_database_url(settings.postgres_url), pool_pre_ping=True)


async def fetch_schema(engine: AsyncEngine) -> str:
    query = text(
        """
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
        """
    )

    async with engine.connect() as connection:
        rows = (await connection.execute(query)).mappings().all()

    tables: dict[str, list[str]] = {}
    for row in rows:
        table = str(row["table_name"])
        column = f"{row['column_name']} {row['data_type']}"
        if row["is_nullable"] == "NO":
            column += " not null"
        tables.setdefault(table, []).append(column)

    return "\n".join(f"{table}({', '.join(columns)})" for table, columns in tables.items())


async def execute_read_query(engine: AsyncEngine, sql: str) -> list[Mapping[str, Any]]:
    async with engine.connect() as connection:
        async with connection.begin():
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            await connection.execute(text("SET LOCAL statement_timeout = '10s'"))
            result = await connection.execute(text(sql))
            return [dict(row) for row in result.mappings().all()]


def compact_rows(rows: Sequence[Mapping[str, Any]], max_rows: int) -> list[Mapping[str, Any]]:
    return list(rows[:max_rows])
