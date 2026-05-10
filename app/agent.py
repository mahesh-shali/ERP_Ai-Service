import json
import uuid
from hashlib import sha256
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncEngine

from app.cache import Cache
from app.database import compact_rows, execute_read_query, fetch_schema
from app.sql_guard import validate_read_only_sql


class ChatState(TypedDict, total=False):
    question: str
    thread_id: str
    schema: str
    sql: str
    rows: list[dict]
    answer: str


SQL_SYSTEM_PROMPT = """You are an ERP reporting SQL assistant.
Generate exactly one PostgreSQL SELECT query for the user's question.
Use only tables and columns from the schema.
Never write INSERT, UPDATE, DELETE, ALTER, DROP, CREATE, TRUNCATE, or administrative commands.
Prefer explicit column names instead of SELECT *.
Use simple joins when relationships are clear from column names.
Return only SQL, no markdown."""


ANSWER_SYSTEM_PROMPT = """You are an ERP assistant.
Answer the user's question in plain business language using only the SQL result rows.
If the result is empty, say that no matching ERP data was found."""


def build_chat_graph(
    engine: AsyncEngine,
    model: str,
    api_key: str,
    base_url: str | None,
    max_rows: int,
    cache: Cache,
    schema_cache_seconds: int,
    query_cache_seconds: int,
):
    llm = ChatOpenAI(model=model, api_key=api_key, base_url=base_url, temperature=0)

    async def load_schema(state: ChatState) -> ChatState:
        schema = await cache.get_or_create("erp-ai:schema", schema_cache_seconds, lambda: fetch_schema(engine))
        return {**state, "schema": schema}

    async def generate_sql(state: ChatState) -> ChatState:
        response = await llm.ainvoke(
            [
                ("system", SQL_SYSTEM_PROMPT),
                ("human", f"Schema:\n{state['schema']}\n\nQuestion:\n{state['question']}"),
            ]
        )
        sql = str(response.content).strip().removeprefix("```sql").removeprefix("```").removesuffix("```").strip()
        return {**state, "sql": validate_read_only_sql(sql, max_rows)}

    async def run_sql(state: ChatState) -> ChatState:
        sql_hash = sha256(state["sql"].encode("utf-8")).hexdigest()
        rows = await cache.get_or_create(
            f"erp-ai:query:{sql_hash}",
            query_cache_seconds,
            lambda: execute_read_query(engine, state["sql"]),
        )
        return {**state, "rows": compact_rows(rows, max_rows)}

    async def generate_answer(state: ChatState) -> ChatState:
        response = await llm.ainvoke(
            [
                ("system", ANSWER_SYSTEM_PROMPT),
                (
                    "human",
                    "Question:\n"
                    f"{state['question']}\n\nSQL:\n{state['sql']}\n\nRows:\n"
                    f"{json.dumps(state['rows'], default=str)}",
                ),
            ]
        )
        return {**state, "answer": str(response.content).strip(), "thread_id": state.get("thread_id") or str(uuid.uuid4())}

    graph = StateGraph(ChatState)
    graph.add_node("load_schema", load_schema)
    graph.add_node("generate_sql", generate_sql)
    graph.add_node("run_sql", run_sql)
    graph.add_node("generate_answer", generate_answer)
    graph.set_entry_point("load_schema")
    graph.add_edge("load_schema", "generate_sql")
    graph.add_edge("generate_sql", "run_sql")
    graph.add_edge("run_sql", "generate_answer")
    graph.add_edge("generate_answer", END)
    return graph.compile()
