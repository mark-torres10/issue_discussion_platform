from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware

from app.main import app


class TestCors:
    def test_cors_middleware_registered(self) -> None:
        middleware_classes = [middleware.cls for middleware in app.user_middleware]
        assert CORSMiddleware in middleware_classes

    def test_preflight_allows_local_origin_with_credentials(self) -> None:
        client = TestClient(app)
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-credentials") == "true"
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://localhost:3000"
        )

    def test_simple_request_reflects_allowed_origin(self) -> None:
        client = TestClient(app)
        response = client.get(
            "/health",
            headers={"Origin": "http://127.0.0.1:3000"},
        )

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-credentials") == "true"
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://127.0.0.1:3000"
        )
