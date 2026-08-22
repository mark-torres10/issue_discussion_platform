"""Tests for profile endpoints."""

from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_me_returns_current_user(client: TestClient) -> None:
    response = client.get("/api/me")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "user-me"
    assert body["photo_urls"] == ["/mock-photos/alex-1.jpg"]


def test_list_profiles_excludes_current_user(client: TestClient) -> None:
    response = client.get("/api/profiles")
    assert response.status_code == 200
    profiles = response.json()["profiles"]
    assert all(profile["id"] != "user-me" for profile in profiles)


def test_list_profiles_excludes_swiped(client: TestClient) -> None:
    swipe_response = client.post(
        "/api/swipes",
        json={"profile_id": "profile-alex", "direction": "like"},
    )
    assert swipe_response.status_code == 201

    response = client.get("/api/profiles")
    assert response.status_code == 200
    profile_ids = [profile["id"] for profile in response.json()["profiles"]]
    assert "profile-alex" not in profile_ids


def test_get_profile_by_id(client: TestClient) -> None:
    response = client.get("/api/profiles/profile-alex")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "profile-alex"
    assert body["name"] == "Alex Chen"
    assert body["photo_urls"] == ["/mock-photos/alex-1.jpg"]


def test_get_profile_not_found(client: TestClient) -> None:
    response = client.get("/api/profiles/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Profile not found"}
