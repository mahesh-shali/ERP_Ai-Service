import pytest
from pydantic import ValidationError

from app.schemas import ChatRequest


def test_chat_request_accepts_query_alias():
    request = ChatRequest(query="  Show users by role  ")

    assert request.message == "Show users by role"


def test_chat_request_requires_input():
    with pytest.raises(ValidationError):
        ChatRequest()
