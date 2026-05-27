"""Tests for /auth/* routes."""

from __future__ import annotations


def test_register_creates_developer_and_api_key(client):
    response = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "supersecret123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["tier"] == "free"
    assert body["api_key"].startswith("af_")
    assert len(body["api_key"]) > 16


def test_register_duplicate_email_is_409(client):
    payload = {"email": "bob@example.com", "password": "supersecret123"}
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409


def test_register_rejects_short_password(client):
    response = client.post(
        "/auth/register",
        json={"email": "carol@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_login_returns_jwt(client, registered_developer):
    email, password, _ = registered_developer
    response = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0


def test_login_wrong_password_is_401(client, registered_developer):
    email, _, _ = registered_developer
    response = client.post(
        "/auth/login", json={"email": email, "password": "wrong-password-1"}
    )
    assert response.status_code == 401


def test_me_requires_api_key(client):
    assert client.get("/auth/me").status_code == 401


def test_me_returns_current_developer(client, registered_developer):
    email, _, api_key = registered_developer
    response = client.get("/auth/me", headers={"X-API-Key": api_key})
    assert response.status_code == 200
    assert response.json()["email"] == email


def test_keys_listing_includes_prefix_only(client, registered_developer):
    _, _, api_key = registered_developer
    response = client.get("/auth/keys", headers={"X-API-Key": api_key})
    assert response.status_code == 200
    keys = response.json()
    assert len(keys) == 1
    assert keys[0]["key_prefix"] == api_key[:10]
    assert "key_hash" not in keys[0]
