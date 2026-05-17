import uvicorn

from app.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.uvicorn_host,
        port=settings.port,
        reload=settings.reload,
    )


if __name__ == "__main__":
    main()
