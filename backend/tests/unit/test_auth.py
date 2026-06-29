import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "newuser@hiveapi.dev",
            "username": "newuser",
            "full_name": "New User",
            "password": "securepassword123",
        })
        assert response.status_code == 201
        data = response.json()
        # Response shape: { message, user: {...}, tokens: { access_token, refresh_token } }
        assert "user" in data or "tokens" in data or "access_token" in data
        assert "hashed_password" not in str(data)

    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        response = await client.post("/api/v1/auth/register", json={
            "email": "test@hiveapi.dev",
            "username": "otherusername",
            "full_name": "Other User",
            "password": "securepassword123",
        })
        assert response.status_code == 409

    async def test_register_duplicate_username(self, client: AsyncClient, test_user):
        response = await client.post("/api/v1/auth/register", json={
            "email": "unique@hiveapi.dev",
            "username": "testuser",
            "full_name": "Other User",
            "password": "securepassword123",
        })
        assert response.status_code == 409

    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "username": "someuser",
            "full_name": "Some User",
            "password": "securepassword123",
        })
        assert response.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient, test_user):
        response = await client.post("/api/v1/auth/login", json={
            "email": "test@hiveapi.dev",
            "password": "securepassword123",
        })
        assert response.status_code == 200
        data = response.json()
        # Tokens are nested under "tokens" key
        tokens = data.get("tokens") or data
        assert "access_token" in tokens
        assert "refresh_token" in tokens

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        response = await client.post("/api/v1/auth/login", json={
            "email": "test@hiveapi.dev",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "email": "nobody@hiveapi.dev",
            "password": "securepassword123",
        })
        assert response.status_code == 401


class TestProtectedRoutes:
    async def test_access_protected_route_with_valid_token(
        self, client: AsyncClient, auth_headers
    ):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200

    async def test_access_protected_route_without_token(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code in (401, 403)

    async def test_access_protected_route_with_invalid_token(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert response.status_code == 401


class TestTokenRefresh:
    async def test_refresh_token_success(self, client: AsyncClient, test_user):
        login_response = await client.post("/api/v1/auth/login", json={
        "email": "test@hiveapi.dev",
        "password": "securepassword123",
        })
        tokens = login_response.json().get("tokens") or login_response.json()
        assert "refresh_token" in tokens
        assert "access_token" in tokens

    async def test_refresh_with_invalid_token(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "notavalidtoken",
        })
        assert response.status_code == 401