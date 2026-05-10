from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    message: str | None = Field(default=None, min_length=1, max_length=2000)
    query: str | None = Field(default=None, min_length=1, max_length=2000)
    question: str | None = Field(default=None, min_length=1, max_length=2000)
    thread_id: str | None = None

    @model_validator(mode="after")
    def require_natural_language_input(self):
        text = self.message or self.query or self.question
        if not text or not text.strip():
            raise ValueError("Provide a natural language message, query, or question.")
        self.message = text.strip()
        return self


class ChatResponse(BaseModel):
    answer: str
    sql: str
    rows: list[dict]
    thread_id: str
