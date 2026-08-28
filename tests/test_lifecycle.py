"""Automated verification suite for Delivery Lifecycle State Machine and Dual-Factor POD."""

import os
import pytest
from httpx import ASGITransport, AsyncClient
from data.seed import init_db, seed_data
from backend.main import app


@pytest.fixture(autouse=True)
def setup_lifecycle_db(tmp_path, monkeypatch):
    """Set up temporary isolated SQLite database for lifecycle tests."""
    test_db_path = str(tmp_path / "test_lifecycle.db")
    schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "schema.sql")

    conn = init_db(db_path=test_db_path, schema_path=schema_path)
    seed_data(conn)
    conn.close()

    monkeypatch.setattr("backend.database.DB_PATH", test_db_path)
    yield test_db_path


@pytest.mark.asyncio
async def test_complete_linear_delivery_lifecycle_with_pin():
    """Verify complete end-to-end milestone lifecycle with customer PIN verification."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Retailer logs in and creates order
        ret_login = await client.post("/api/auth/login", json={"username": "luthuli_electronics", "password": "Reflex2026!"})
        retailer_token = ret_login.json()["access_token"]

        create_res = await client.post(
            "/api/orders",
            headers={"Authorization": f"Bearer {retailer_token}"},
            json={
                "customer_name": "Faith Wambui",
                "customer_phone": "+254712000111",
                "delivery_address": "Kimathi Chambers, 3rd Floor, Nairobi",
                "item_description": "Wireless Keyboard and Mouse Combo",
                "package_value": 4500.0,
                "delivery_fee": 350.0,
            },
        )
        assert create_res.status_code == 201
        order = create_res.json()
        order_id = order["id"]
        tracking_token = order["tracking_token"]
        verification_pin = order["verification_pin"]
        assert order["status"] == "ORDER_LOGGED"

        # 2. Dispatcher logs in and assigns order to John Mwangi (rider_id 1)
        disp_login = await client.post("/api/auth/login", json={"username": "nairobi_dispatch", "password": "Reflex2026!"})
        disp_token = disp_login.json()["access_token"]

        assign_res = await client.post(
            "/api/dispatch/assign",
            headers={"Authorization": f"Bearer {disp_token}"},
            json={"order_id": order_id, "rider_id": 1},
        )
        assert assign_res.status_code == 200
        assert assign_res.json()["status"] == "ASSIGNED"

        # 3. Rider John Mwangi logs in and confirms package pickup
        rider_login = await client.post("/api/auth/login", json={"username": "rider_mwangi", "password": "Reflex2026!"})
        rider_token = rider_login.json()["access_token"]

        pickup_res = await client.post(
            "/api/rider/milestone",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={"order_id": order_id, "new_status": "PICKED_UP"},
        )
        assert pickup_res.status_code == 200
        assert pickup_res.json()["status"] == "PICKED_UP"

        # 4. Rider updates status to ARRIVED at customer location
        arrived_res = await client.post(
            "/api/rider/milestone",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={"order_id": order_id, "new_status": "ARRIVED"},
        )
        assert arrived_res.status_code == 200
        assert arrived_res.json()["status"] == "ARRIVED"

        # 5. Rider submits customer 4-digit PIN to verify Proof of Delivery
        deliver_res = await client.post(
            "/api/rider/milestone",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={
                "order_id": order_id,
                "new_status": "DELIVERED",
                "verification_pin": verification_pin,
            },
        )
        assert deliver_res.status_code == 200
        delivered_order = deliver_res.json()
        assert delivered_order["status"] == "DELIVERED"
        assert delivered_order["delivered_at"] is not None

        # 6. Check Public Tracking endpoint reflects completed status
        track_res = await client.get(f"/api/track/{tracking_token}")
        assert track_res.status_code == 200
        track_data = track_res.json()
        assert track_data["status"] == "DELIVERED"
        assert len(track_data["status_logs"]) >= 5


@pytest.mark.asyncio
async def test_dual_factor_qr_verification():
    """Verify Proof of Delivery succeeds when scanning valid parcel QR tracking token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Use seeded order REF-3094-M3 which is in PICKED_UP state assigned to rider_otieno (rider_id 2)
        rider_login = await client.post("/api/auth/login", json={"username": "rider_otieno", "password": "Reflex2026!"})
        rider_token = rider_login.json()["access_token"]

        # 1. Update to ARRIVED
        res_arr = await client.post(
            "/api/rider/milestone",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={"order_id": 3, "new_status": "ARRIVED"},
        )
        assert res_arr.status_code == 200

        # 2. Finalize POD using QR token match
        res_del = await client.post(
            "/api/rider/milestone",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={
                "order_id": 3,
                "new_status": "DELIVERED",
                "qr_token": "REF-3094-M3",
            },
        )
        assert res_del.status_code == 200
        assert res_del.json()["status"] == "DELIVERED"


@pytest.mark.asyncio
async def test_illegal_state_jump_rejection():
    """Verify that jumping milestones (e.g. ORDER_LOGGED to DELIVERED) is strictly rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rider_login = await client.post("/api/auth/login", json={"username": "rider_mwangi", "password": "Reflex2026!"})
        rider_token = rider_login.json()["access_token"]

        # Order #1 is in ORDER_LOGGED state; rider cannot jump directly to DELIVERED
        res = await client.post(
            "/api/rider/milestone",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={
                "order_id": 1,
                "new_status": "DELIVERED",
                "verification_pin": "4829",
            },
        )
        assert res.status_code == 400
        assert "Illegal state transition" in res.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_pin_rejection():
    """Verify that submitting incorrect PIN fails verification with 400 Bad Request."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Order 2 is ASSIGNED to rider_mwangi
        rider_login = await client.post("/api/auth/login", json={"username": "rider_mwangi", "password": "Reflex2026!"})
        rider_token = rider_login.json()["access_token"]

        await client.post("/api/rider/milestone", headers={"Authorization": f"Bearer {rider_token}"}, json={"order_id": 2, "new_status": "PICKED_UP"})
        await client.post("/api/rider/milestone", headers={"Authorization": f"Bearer {rider_token}"}, json={"order_id": 2, "new_status": "ARRIVED"})

        # Submit wrong PIN
        res = await client.post(
            "/api/rider/milestone",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={
                "order_id": 2,
                "new_status": "DELIVERED",
                "verification_pin": "0000",
            },
        )
        assert res.status_code == 400
        assert "Invalid Proof of Delivery" in res.json()["detail"]


@pytest.mark.asyncio
async def test_unauthorized_rider_mutation_rejection():
    """Verify that a rider cannot update tasks assigned to another courier."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Order 2 is assigned to rider_mwangi; rider_otieno cannot update it
        rider_login = await client.post("/api/auth/login", json={"username": "rider_otieno", "password": "Reflex2026!"})
        rider_token = rider_login.json()["access_token"]

        res = await client.post(
            "/api/rider/milestone",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={"order_id": 2, "new_status": "PICKED_UP"},
        )
        assert res.status_code == 403
        assert "not the assigned rider" in res.json()["detail"]
