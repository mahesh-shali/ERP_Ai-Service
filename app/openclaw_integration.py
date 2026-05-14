from importlib.metadata import PackageNotFoundError, version
from typing import Any


def load_openclaw() -> tuple[Any | None, str | None]:
    try:
        import cmdop.exceptions as cmdop_exceptions

        if not hasattr(cmdop_exceptions, "TimeoutError") and hasattr(cmdop_exceptions, "ConnectionTimeoutError"):
            cmdop_exceptions.TimeoutError = cmdop_exceptions.ConnectionTimeoutError

        import openclaw

        return openclaw, None
    except Exception as exc:
        return None, f"{exc.__class__.__name__}: {exc}"


def openclaw_version() -> str | None:
    try:
        return version("openclaw")
    except PackageNotFoundError:
        return None


def openclaw_status(api_key: str = "") -> dict:
    module, error = load_openclaw()
    return {
        "installed": openclaw_version() is not None,
        "importable": module is not None,
        "configured": bool(api_key.strip()),
        "version": openclaw_version(),
        "client": "OpenClaw.remote" if api_key.strip() else "OpenClaw.local",
        "error": error,
    }
