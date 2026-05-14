from app.intent import AgentIntent, classify_intent_from_text


def test_greeting_is_conversation():
    assert classify_intent_from_text("hello") == AgentIntent.CONVERSATION


def test_erp_data_question_is_database():
    assert classify_intent_from_text("show users by role") == AgentIntent.DATABASE


def test_current_public_question_is_web():
    assert classify_intent_from_text("search the web for latest PostgreSQL news") == AgentIntent.WEB
