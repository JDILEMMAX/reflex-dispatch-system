"""Route sanity verification suite validating all REST API endpoints and static assets."""

import os
import pytest
from starlette.testclient import TestClient
from backend.auth import create_access_token
from data.seed import init_db, seed_data
from backend.main import app


@pytest.fixture(autouse=True)
def setup_sanity_db(tmp_path, monkeypatch):
    """Set up temporary isolated SQLite database for sanity tests."""
    test_db_path = str(tmp_path / "test_sanity.db")
    schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "schema.sql")

    conn = init_db(db_path=test_db_path, schema_path=schema_path)
    seed_data(conn)
    conn.close()

    monkeypatch.setattr("backend.database.DB_PATH", test_db_path)
    yield test_db_path


def test_static_asset_serving_routes():
    """Verify static frontend assets (HTML, CSS, JS) respond with HTTP 200."""
    with TestClient(app) as client:
        res_index = client.get("/")
        assert res_index.status_code == 200

        res_css = client.get("/styles.css")
        assert res_css.status_code == 200

        res_js = client.get("/app.js")
        assert res_js.status_code == 200

        res_tracker = client.get("/tracker.html")
        assert res_tracker.status_code == 200


def test_public_tracking_endpoint():
    """Verify public tracking endpoint for valid and non-existent tokens."""
    with TestClient(app) as client:
        # Valid token
        res_valid = client.get("/api/track/REF-8492-X1")
        assert res_valid.status_code == 200
        data = res_valid.json()
        assert data["tracking_token"] == "REF-8492-X1"
        assert data["status"] == "ORDER_LOGGED"
        assert "retailer_name" in data

        # Invalid token returns 404
        res_invalid = client.get("/api/track/REF-NON-EXISTENT")
        assert res_invalid.status_code == 404


def test_dispatch_riders_endpoint():
    """Verify dispatcher can query active fleet roster."""
    disp_token = create_access_token({
        "sub": "nairobi_dispatch",
        "role": "ROLE_DISPATCHER",
        "user_id": 3,
    })

    with TestClient(app) as client:
        res = client.get(
            "/api/dispatch/riders",
            headers={"Authorization": f"Bearer {disp_token}"},
        )
        assert res.status_code == 200
        riders = res.json()
        assert len(riders) >= 2
        assert any(r["username"] == "rider_mwangi" for r in riders)
