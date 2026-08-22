"""Tests for verification upload endpoints."""

from fastapi.testclient import TestClient

LINKEDIN_PATH = "/api/verifications/linkedin"
TRUST_SOURCE_PATH = "/api/verifications/trust_source"

MINIMAL_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xd9"
)
MINIMAL_MP4 = (
    b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom\x00\x00\x00\x08free"
)


def _upload(
    client: TestClient,
    path: str,
    *,
    photo: bytes | None = None,
    video: bytes | None = None,
    photo_content_type: str = "image/jpeg",
    video_content_type: str = "video/mp4",
) -> object:
    files: list[tuple[str, tuple[str, bytes, str]]] = []
    if photo is not None:
        files.append(("photo", ("test.jpg", photo, photo_content_type)))
    if video is not None:
        files.append(("video", ("test.mp4", video, video_content_type)))
    return client.post(path, files=files)


def test_linkedin_verification_requires_file(client: TestClient) -> None:
    response = client.post(LINKEDIN_PATH)
    assert response.status_code == 400


def test_linkedin_verification_photo_sets_flag(client: TestClient) -> None:
    response = _upload(client, LINKEDIN_PATH, photo=MINIMAL_JPEG)
    assert response.status_code == 200
    body = response.json()
    assert body["linkedin_verified"] is True
    assert body["id"] == "user-me"


def test_trust_source_verification_video_sets_flag(client: TestClient) -> None:
    response = _upload(client, TRUST_SOURCE_PATH, video=MINIMAL_MP4)
    assert response.status_code == 200
    body = response.json()
    assert body["trust_source_verified"] is True
    assert body["id"] == "user-me"


def test_get_me_reflects_verification_after_post(client: TestClient) -> None:
    upload_response = _upload(client, LINKEDIN_PATH, photo=MINIMAL_JPEG)
    assert upload_response.status_code == 200

    me_response = client.get("/api/me")
    assert me_response.status_code == 200
    assert me_response.json()["linkedin_verified"] is True


def test_reject_invalid_mime(client: TestClient) -> None:
    response = _upload(
        client,
        LINKEDIN_PATH,
        photo=b"not an image",
        photo_content_type="text/plain",
    )
    assert response.status_code == 400
