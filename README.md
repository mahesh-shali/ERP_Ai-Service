# ERP AI Service

FastAPI service for a natural-language ERP PostgreSQL agent. It uses LangGraph to:

1. inspect the PostgreSQL schema,
2. generate a read-only SQL query,
3. validate that the SQL is safe,
4. execute it with a row limit,
5. answer in natural language.

## Setup

```powershell
cd E:\projects\codex\ai-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.development.example .env.development
```

Fill `.env.development` with your real `DATABASE_URL`, either `OPENAI_API_KEY` or `GROQ_API_KEY`, a long `AI_SERVICE_API_KEY`, and `REDIS_URL`.
The service also reads `..\Erp.Api\.env`, so it can reuse `ConnectionStrings__DefaultConnection` from the ASP.NET API when `DATABASE_URL` is not set in `ai-service`.

Example:

```env
DATABASE_URL=postgres://user:password@host:5432/database?sslmode=require
OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-4.1-mini
GROQ_API_KEY=gsk-your-groq-key
GROQ_MODEL=llama-3.3-70b-versatile
AI_SERVICE_API_KEY=replace-with-a-long-random-internal-key
REDIS_URL=rediss://:password@host:6379/0
```

## Run

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

The Next.js app calls this service through its server route at `/api/ai-chat`.

You can also run through the deployment entrypoint locally:

```powershell
python -m app.server
```

## Deploy To Render

Use `render.yaml` from this folder, or create a Render Python web service with:

```text
Build Command: pip install -r requirements.txt
Start Command: python -m app.server
Health Check Path: /health
```

Set these Render environment variables:

```env
DATABASE_URL=postgres://user:password@host:5432/database?sslmode=require
GROQ_API_KEY=gsk-your-production-groq-key
GROQ_MODEL=llama-3.3-70b-versatile
AI_SERVICE_API_KEY=replace-with-a-long-random-internal-key
SERPAPI_API_KEY=your-production-serpapi-key
REDIS_URL=rediss://:password@host:6379/0
ALLOWED_ORIGINS=https://erp-frontend-rust.vercel.app
```

Render provides `PORT` automatically. The app binds to `0.0.0.0:$PORT` when `PORT` exists, and keeps `127.0.0.1:8001` for local development.

On Vercel frontend, set:

```env
AI_SERVICE_URL=https://your-render-ai-service.onrender.com
AI_SERVICE_API_KEY=replace-with-the-same-key-used-on-render
```

## Debug In VS Code

Open `E:\projects\codex` in VS Code, install the Python extension if needed, then use Run and Debug:

- `AI Service: FastAPI Debug` for normal breakpoint debugging.
- `AI Service: FastAPI Debug Reload` when you want Uvicorn reload enabled.

The debugger uses `ai-service\.venv\Scripts\python.exe` and starts from the `ai-service` folder, while the app still loads env files from both `ai-service` and `Erp.Api`.

## Agent API

```powershell
curl -X POST http://127.0.0.1:8001/api/agent/search `
  -H "Content-Type: application/json" `
  -H "X-AI-Service-Key: replace-with-a-long-random-internal-key" `
  -d "{\"query\":\"How many users are registered by role?\"}"
```

The response includes the natural-language answer, SQL used, returned rows, and `thread_id`.
