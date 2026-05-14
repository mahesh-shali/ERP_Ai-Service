from enum import StrEnum


class AgentIntent(StrEnum):
    CONVERSATION = "conversation"
    DATABASE = "database"
    WEB = "web"


GREETING_TERMS = {
    "hello",
    "hi",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
    "thanks",
    "thank you",
}

DATABASE_TERMS = {
    "department",
    "departments",
    "erp",
    "inventory",
    "maintenance",
    "navigation",
    "permission",
    "permissions",
    "planning",
    "production",
    "refresh token",
    "role",
    "roles",
    "sales",
    "side nav",
    "side navbar",
    "sidenav",
    "user",
    "users",
}

DATABASE_ACTION_TERMS = {
    "count",
    "fetch",
    "find",
    "get",
    "how many",
    "list",
    "report",
    "show",
    "total",
}

WEB_TERMS = {
    "current",
    "google",
    "internet",
    "latest",
    "news",
    "online",
    "recent",
    "search the web",
    "today",
    "web",
    "website",
}


def classify_intent_from_text(message: str) -> AgentIntent | None:
    text = " ".join(message.lower().strip().split())
    if not text:
        return AgentIntent.CONVERSATION

    if text in GREETING_TERMS or any(text.startswith(f"{term} ") for term in GREETING_TERMS):
        return AgentIntent.CONVERSATION

    has_database_subject = any(term in text for term in DATABASE_TERMS)
    has_database_action = any(term in text for term in DATABASE_ACTION_TERMS)
    if has_database_subject and has_database_action:
        return AgentIntent.DATABASE

    if any(term in text for term in WEB_TERMS):
        return AgentIntent.WEB

    return None
