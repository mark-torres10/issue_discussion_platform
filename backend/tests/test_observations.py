from datetime import UTC, datetime
from uuid import uuid4

from tests.conftest import OBSERVATIONS_PATH, auth_headers, exchange_invitation, start_session


class TestObservations:
    def test_unknown_observation_type_rejected(self, client) -> None:
        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]

        response = client.post(
            OBSERVATIONS_PATH,
            headers=auth_headers(exchange.csrf_token, "obs-bad-type"),
            cookies=exchange.cookies,
            json={
                "expected_version": version,
                "observations": [
                    {
                        "observation_id": str(uuid4()),
                        "observation_type": "not_a_real_type",
                        "occurred_at": datetime.now(UTC).isoformat(),
                    }
                ],
            },
        )

        assert response.status_code == 400
        assert response.json()["error_code"] == "validation_error"

    def test_batch_size_limit_enforced(self, client) -> None:
        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]
        observations = [
            {
                "observation_id": str(uuid4()),
                "observation_type": "session_opened",
                "occurred_at": datetime.now(UTC).isoformat(),
            }
            for _ in range(21)
        ]

        response = client.post(
            OBSERVATIONS_PATH,
            headers=auth_headers(exchange.csrf_token, "obs-batch"),
            cookies=exchange.cookies,
            json={"expected_version": version, "observations": observations},
        )

        assert response.status_code == 400
        assert response.json()["error_code"] == "validation_error"
