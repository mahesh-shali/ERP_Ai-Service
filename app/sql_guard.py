import re

import sqlglot
from sqlglot import exp


FORBIDDEN_EXPRESSIONS = tuple(
    expression_type
    for expression_type in (
        getattr(exp, "Alter", None),
        getattr(exp, "Command", None),
        getattr(exp, "Create", None),
        getattr(exp, "Delete", None),
        getattr(exp, "Drop", None),
        getattr(exp, "Insert", None),
        getattr(exp, "Merge", None),
        getattr(exp, "Truncate", None),
        getattr(exp, "TruncateTable", None),
        getattr(exp, "Update", None),
    )
    if expression_type is not None
)


def validate_read_only_sql(sql: str, max_rows: int) -> str:
    cleaned = sql.strip().rstrip(";")
    if not cleaned:
        raise ValueError("SQL query is empty.")

    if ";" in cleaned:
        raise ValueError("Only one SQL statement is allowed.")

    if not re.match(r"^(select|with)\b", cleaned, flags=re.IGNORECASE):
        raise ValueError("Only SELECT or WITH queries are allowed.")

    parsed = sqlglot.parse_one(cleaned, read="postgres")
    if any(parsed.find(expression_type) for expression_type in FORBIDDEN_EXPRESSIONS):
        raise ValueError("Write, schema, and administrative SQL statements are blocked.")

    if parsed.find(exp.Limit) is None:
        cleaned = f"{cleaned}\nLIMIT {max_rows}"

    return cleaned
