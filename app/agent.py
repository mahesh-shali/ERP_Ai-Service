import json
import uuid
from hashlib import sha256
from typing import TypedDict

from httpx import HTTPError
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncEngine

from app.cache import Cache
from app.database import compact_rows, execute_read_query, fetch_schema
from app.intent import AgentIntent, classify_intent_from_text
from app.sql_guard import validate_read_only_sql
from app.web_search import search_web


class ChatState(TypedDict, total=False):
    question: str
    thread_id: str
    intent: str
    schema: str
    sql: str
    rows: list[dict]
    answer: str
    web_results: list[dict]


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


INTENT_SYSTEM_PROMPT = """Classify the user's message for an ERP assistant.
Return only one word:
conversation - greetings, small talk, help, general questions that do not require ERP database data or the public web.
database - questions that need the ERP/Postgres database, such as users, roles, permissions, departments, side navigation, inventory, sales, production, or reports.
web - questions that need current/public internet information, latest news, external websites, or online search.
Do not choose database for greetings like hello."""


CONVERSATION_SYSTEM_PROMPT = """You are a helpful ERP assistant.
Reply naturally and briefly.
Do not invent database facts.
If the user asks for ERP data, tell them you can look it up when they ask a specific ERP data question."""


WEB_ANSWER_SYSTEM_PROMPT = """You are a web research assistant.
Answer using only the provided web search snippets.
If the snippets are empty or insufficient, say that you could not find enough web results."""


def build_chat_graph(
    engine: AsyncEngine,
    model: str,
    api_key: str,
    base_url: str | None,
    max_rows: int,
    cache: Cache,
    schema_cache_seconds: int,
    query_cache_seconds: int,
    serpapi_api_key: str = "",
):
    llm = ChatOpenAI(model=model, api_key=api_key, base_url=base_url, temperature=0)

    async def classify_intent(state: ChatState) -> ChatState:
        heuristic_intent = classify_intent_from_text(state["question"])
        if heuristic_intent is not None:
            return {**state, "intent": heuristic_intent.value}

        response = await llm.ainvoke(
            [
                ("system", INTENT_SYSTEM_PROMPT),
                ("human", state["question"]),
            ]
        )
        intent = str(response.content).strip().lower()
        if intent not in {item.value for item in AgentIntent}:
            intent = AgentIntent.CONVERSATION.value

        return {**state, "intent": intent}

    def route_by_intent(state: ChatState) -> str:
        return state.get("intent", AgentIntent.CONVERSATION.value)

    async def normal_answer(state: ChatState) -> ChatState:
        response = await llm.ainvoke(
            [
                ("system", CONVERSATION_SYSTEM_PROMPT),
                ("human", state["question"]),
            ]
        )
        return {
            **state,
            "answer": str(response.content).strip(),
            "sql": "",
            "rows": [],
            "thread_id": state.get("thread_id") or str(uuid.uuid4()),
        }

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

    async def run_web_search(state: ChatState) -> ChatState:
        try:
            results = await cache.get_or_create(
                f"erp-ai:web:{sha256(state['question'].encode('utf-8')).hexdigest()}",
                query_cache_seconds,
                lambda: search_web(state["question"], serpapi_api_key=serpapi_api_key),
            )
        except HTTPError:
            results = []

        return {**state, "web_results": results, "sql": "", "rows": []}

    async def generate_web_answer(state: ChatState) -> ChatState:
        response = await llm.ainvoke(
            [
                ("system", WEB_ANSWER_SYSTEM_PROMPT),
                (
                    "human",
                    "Question:\n"
                    f"{state['question']}\n\nWeb snippets:\n"
                    f"{json.dumps(state.get('web_results', []), default=str)}",
                ),
            ]
        )
        return {**state, "answer": str(response.content).strip(), "thread_id": state.get("thread_id") or str(uuid.uuid4())}

    graph = StateGraph(ChatState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("normal_answer", normal_answer)
    graph.add_node("load_schema", load_schema)
    graph.add_node("generate_sql", generate_sql)
    graph.add_node("run_sql", run_sql)
    graph.add_node("generate_answer", generate_answer)
    graph.add_node("run_web_search", run_web_search)
    graph.add_node("generate_web_answer", generate_web_answer)
    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            AgentIntent.CONVERSATION.value: "normal_answer",
            AgentIntent.DATABASE.value: "load_schema",
            AgentIntent.WEB.value: "run_web_search",
        },
    )
    graph.add_edge("normal_answer", END)
    graph.add_edge("load_schema", "generate_sql")
    graph.add_edge("generate_sql", "run_sql")
    graph.add_edge("run_sql", "generate_answer")
    graph.add_edge("generate_answer", END)
    graph.add_edge("run_web_search", "generate_web_answer")
    graph.add_edge("generate_web_answer", END)
    return graph.compile()
