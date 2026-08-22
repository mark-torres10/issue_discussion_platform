"""Tests for swipe endpoints."""

from fastapi.testclient import TestClient


def test_swipe_like_creates_record(client: TestClient) -> None:
    response = client.post(
        "/api/swipes",
        json={"profile_id": "profile-jordan", "direction": "like"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["profile_id"] == "profile-jordan"
    assert body["direction"] == "like"
    assert body["swiped_at"]


def test_swipe_duplicate_returns_400(client: TestClient) -> None:
    payload = {"profile_id": "profile-sam", "direction": "pass"}
    first = client.post("/api/swipes", json=payload)
    assert first.status_code == 201

    second = client.post("/api/swipes", json=payload)
    assert second.status_code == 400


def test_swipe_self_returns_400(client: TestClient) -> None:
    response = client.post(
        "/api/swipes",
        json={"profile_id": "user-me", "direction": "like"},
    )
    assert response.status_code == 400


def test_swipe_unknown_profile_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/swipes",
        json={"profile_id": "missing", "direction": "like"},
    )
    assert response.status_code == 404


def test_list_swipes_after_post(client: TestClient) -> None:
    post_response = client.post(
        "/api/swipes",
        json={"profile_id": "profile-alex", "direction": "like"},
    )
    assert post_response.status_code == 201

    list_response = client.get("/api/swipes")
    assert list_response.status_code == 200
    swipes = list_response.json()["swipes"]
    assert len(swipes) == 1
    assert swipes[0]["profile_id"] == "profile-alex"
    assert swipes[0]["direction"] == "like"
    assert swipes[0]["swiped_at"]
