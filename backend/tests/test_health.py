from backend.app.api.routes.health import health_check


def test_health_endpoint_returns_ok() -> None:
    response = health_check()

    assert response["status"] == "ok"
    assert response["service"] == "padelpulse-api"
