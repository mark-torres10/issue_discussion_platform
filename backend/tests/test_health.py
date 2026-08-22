class TestHealthEndpoint:
    def test_health_returns_ok(self, client, commit_sha: str) -> None:
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "commit": commit_sha}


class TestReadyEndpoint:
    def test_ready_ok_in_memory_mode(self, client, memory_mode: None) -> None:
        response = client.get("/ready")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_ready_requires_database_url_in_postgres_mode(
        self, client, postgres_mode: None
    ) -> None:
        response = client.get("/ready")

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "degraded"
        assert "database" in body["reason"].lower()
