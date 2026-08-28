"""Automated verification suite for Authentication, JWT Token Issuance and RBAC Security."""

import os
import pytest
from httpx import ASGITransport, AsyncClient
from backend.auth import create_access_token
from data.seed import init_db, seed_data
from backend.main import app


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Set up temporary isolated SQLite database for authentication tests."""
    test_db_path = str(tmp_path / "test_auth.db")
    schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "schema.sql")

    conn = init_db(db_path=test_db_path, schema_path=schema_path)
    seed_data(conn)
    conn.close()

    monkeypatch.setattr("backend.database.DB_PATH", test_db_path)
    yield test_db_path


@pytest.mark.asyncio
async def test_valid_login_returns_jwt_token():
    """Verify that valid credentials return signed Bearer JWT token with user profile."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            json={"username": "luthuli_electronics", "password": "Reflex2026!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "ROLE_RETAILER"
        assert data["username"] == "luthuli_electronics"
        assert data["full_name"] == "Maina K. (Luthuli Electronics)"


@pytest.mark.asyncio
async def test_invalid_login_rejection():
    """Verify that invalid password returns 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            json={"username": "luthuli_electronics", "password": "WrongPassword123"},
        )
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auth_me_with_valid_bearer_token():
    """Verify GET /api/auth/me returns profile for authenticated user."""
    token = create_access_token({
        "sub": "nairobi_dispatch",
        "role": "ROLE_DISPATCHER",
        "user_id": 3,
        "full_name": "Kamau N. (Nairobi Central Hub)",
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "nairobi_dispatch"
        assert data["role"] == "ROLE_DISPATCHER"


@pytest.mark.asyncio
async def test_auth_me_unauthorized_without_token():
    """Verify GET /api/auth/me rejects requests missing Bearer token with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/auth/me")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_role_based_access_controls():
    """Verify that unauthorized roles are rejected with 403 Forbidden."""
    rider_token = create_access_token({
        "sub": "rider_mwangi",
        "role": "ROLE_RIDER",
        "user_id": 4,
        "rider_id": 1,
    })
    retailer_token = create_access_token({
        "sub": "luthuli_electronics",
        "role": "ROLE_RETAILER",
        "user_id": 1,
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Rider cannot create retailer orders
        res1 = await client.post(
            "/api/orders",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={
                "customer_name": "Test",
                "customer_phone": "0700000000",
                "delivery_address": "Test Address",
                "item_description": "Test Item",
                "package_value": 1000.0,
                "delivery_fee": 200.0,
            },
        )
        assert res1.status_code == 403

        # Retailer cannot access dispatcher order queue
        res2 = await client.get(
            "/api/dispatch/orders",
            headers={"Authorization": f"Bearer {retailer_token}"},
        )
        assert res2.status_code == 403

        # Retailer cannot access rider task queue
        res3 = await client.get(
            "/api/rider/tasks",
            headers={"Authorization": f"Bearer {retailer_token}"},
        )
        assert res3.status_code == 403
