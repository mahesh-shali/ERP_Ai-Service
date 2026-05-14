from app.openclaw_integration import openclaw_status


def test_openclaw_status_shape():
    status = openclaw_status("")

    assert set(status) == {"installed", "importable", "configured", "version", "client", "error"}
    assert status["configured"] is False
    assert status["client"] == "OpenClaw.local"


def test_openclaw_status_marks_api_key_configured():
    status = openclaw_status("cmdop_live_test")

    assert status["configured"] is True
    assert status["client"] == "OpenClaw.remote"
