import pytest

from app.sql_guard import validate_read_only_sql


def test_validate_read_only_sql_adds_limit():
    sql = validate_read_only_sql("select id, name from users", 25)

    assert "LIMIT 25" in sql


def test_validate_read_only_sql_rejects_delete():
    with pytest.raises(ValueError):
        validate_read_only_sql("delete from users", 25)


def test_validate_read_only_sql_rejects_multiple_statements():
    with pytest.raises(ValueError):
        validate_read_only_sql("select * from users; select * from roles", 25)
