class TestApiErrorShape:
    def test_validation_error_maps_to_400(self, client) -> None:
        response = client.post("/_test/validation", json={"name": 123})

        assert response.status_code == 400
        body = response.json()
        assert body["error_code"] == "validation_error"
        assert body["retryable"] is False
        assert isinstance(body["request_id"], str)
        assert body["request_id"]
        assert isinstance(body["message"], str)
        assert body["message"]
        assert body["retry_after_seconds"] is None
        assert body["session_status"] is None
        assert body["current_version"] is None

    def test_unknown_fields_rejected(self, client) -> None:
        response = client.post(
            "/_test/validation",
            json={"name": "alice", "unexpected": "field"},
        )

        assert response.status_code == 400
        body = response.json()
        assert body["error_code"] == "validation_error"
        assert body["retryable"] is False
        assert isinstance(body["request_id"], str)
        assert body["request_id"]
