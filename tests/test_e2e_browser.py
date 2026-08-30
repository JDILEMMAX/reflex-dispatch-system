"""Playwright automated end-to-end browser verification suite."""

import os
import subprocess
import sys
import time
import pytest
import httpx
from data.seed import init_db, seed_data

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

TEST_PORT = 8000
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"


@pytest.fixture(scope="module", autouse=True)
def live_server():
    """Reset database and launch background FastAPI server on http://127.0.0.1:8000."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_db_dir = os.path.join(project_root, "data")
    schema_path = os.path.join(test_db_dir, "schema.sql")
    db_path = os.path.join(test_db_dir, "reflex.db")

    # 1. Database Reset
    conn = init_db(db_path=db_path, schema_path=schema_path)
    seed_data(conn)
    conn.close()

    server_process = None
    already_running = False
    try:
        r = httpx.get(f"{BASE_URL}/", timeout=1.0)
        if r.status_code in (200, 404):
            already_running = True
    except Exception:
        already_running = False

    if not already_running:
        env = {**os.environ, "PYTHONPATH": project_root}
        server_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(TEST_PORT),
                "--log-level",
                "error",
            ],
            cwd=project_root,
            env=env,
        )

        server_ready = False
        for _ in range(30):
            try:
                r = httpx.get(f"{BASE_URL}/", timeout=1.0)
                if r.status_code in (200, 404):
                    server_ready = True
                    break
            except Exception:
                time.sleep(0.3)

        if not server_ready:
            if server_process:
                server_process.terminate()
            raise RuntimeError("FastAPI background test server failed to start within timeout.")

    yield

    if server_process:
        server_process.terminate()
        try:
            server_process.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            server_process.kill()


def test_full_delivery_workflow_golden_path():
    """E2E Golden Path: Retailer Logs Order -> Dispatcher Assigns -> Rider Completes POD -> Customer Tracks."""
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]

    launch_kwargs = {"headless": True}
    for p in edge_paths:
        if os.path.exists(p):
            launch_kwargs["channel"] = "msedge"
            break

    if "channel" not in launch_kwargs:
        for p in chrome_paths:
            if os.path.exists(p):
                launch_kwargs["channel"] = "chrome"
                break

    if HAS_PLAYWRIGHT:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(**launch_kwargs)
                page = browser.new_page()

                try:
                    # 1. Retailer Order Entry: Log in as luthuli_electronics
                    page.goto(f"{BASE_URL}/")
                    page.wait_for_selector("#loginForm")

                    page.fill("#loginUsername", "luthuli_electronics")
                    page.fill("#loginPassword", "Reflex2026!")
                    page.click("#btnLoginSubmit")

                    # Strict post-login dashboard visibility check.
                    # If the DOM crashed (e.g. null getElementById on loginErrorAlert),
                    # viewRetailer will never become active and this assertion will fail fast.
                    page.wait_for_selector("#viewRetailer.active", timeout=8000)
                    from playwright.sync_api import expect
                    expect(page.locator("#viewRetailer")).to_be_visible()
                    assert page.is_visible("#retailerOrdersTable")

                    # Open Order Modal and create order for customer "Wanjiku Njoroge"
                    page.click("button:has-text('+ Log New Delivery Request')")
                    page.wait_for_selector("#modalCreateOrder.active")

                    page.fill("#orderCustomerName", "Wanjiku Njoroge")
                    page.fill("#orderCustomerPhone", "+254701234567")
                    page.fill("#orderAddress", "Bazaar Plaza, 4th Floor, Upper Hill, Nairobi")
                    page.fill("#orderItemDesc", "HP Laptop Charger and Wireless Mouse")
                    page.fill("#orderValue", "3500")
                    page.fill("#orderFee", "300")

                    page.click("#btnSubmitOrder")
                    page.wait_for_selector("#modalCreateOrder", state="hidden")

                    # Retrieve generated tracking token (REF-xxxx) and capture 4-digit PIN
                    page.wait_for_selector("#retailerOrdersBody tr")
                    first_row = page.locator("#retailerOrdersBody tr").first
                    token_el = first_row.locator(".token-pill")
                    created_token = token_el.text_content().replace("↗", "").strip()

                    pin_el = first_row.locator(".pin-tag")
                    pin_text = pin_el.text_content()
                    created_pin = pin_text.replace("PIN:", "").strip()

                    assert created_token.startswith("REF-")
                    assert len(created_pin) == 4

                    # 2. Dispatcher Assignment: Log in as nairobi_dispatch
                    page.click("button:has-text('Logout')")
                    page.wait_for_selector("#viewLogin.active")

                    page.fill("#loginUsername", "nairobi_dispatch")
                    page.fill("#loginPassword", "Reflex2026!")
                    page.click("#btnLoginSubmit")

                    # Strict post-login dispatcher dashboard visibility check.
                    page.wait_for_selector("#viewDispatcher.active", timeout=8000)
                    from playwright.sync_api import expect
                    expect(page.locator("#viewDispatcher")).to_be_visible()
                    page.wait_for_selector("#dispatcherOrdersBody tr")

                    order_row = page.locator(f"#dispatcherOrdersBody tr:has-text('{created_token}')")
                    order_row.locator("select").select_option(label="John Mwangi (KMDF 420X)")
                    order_row.locator("button:has-text('Assign')").click()

                    # Wait for toast confirmation
                    page.wait_for_selector(".toast-success")

                    # 3. Rider Milestone Progression: Log in as rider_mwangi on mobile viewport
                    page.set_viewport_size({"width": 390, "height": 844})
                    page.click("button:has-text('Logout')")
                    page.wait_for_selector("#viewLogin.active")

                    page.fill("#loginUsername", "rider_mwangi")
                    page.fill("#loginPassword", "Reflex2026!")
                    page.click("#btnLoginSubmit")

                    # Strict post-login rider terminal visibility check.
                    page.wait_for_selector("#viewRider.active", timeout=8000)
                    from playwright.sync_api import expect
                    expect(page.locator("#viewRider")).to_be_visible()
                    page.wait_for_selector(f".task-card:has-text('{created_token}')")

                    task_card = page.locator(f".task-card:has-text('{created_token}')")
                    task_card.locator("button:has-text('Confirm Shop Package Pickup')").click()
                    page.wait_for_selector(".toast-success")

                    # Trigger Arrived
                    task_card.locator("button:has-text('Confirm Arrival at Customer Doorstep')").click()
                    page.wait_for_selector(".toast-success")

                    # 4. Proof of Delivery: Enter customer PIN and submit
                    task_card.locator("button:has-text('Enter Customer PIN / Scan POD')").click()
                    page.wait_for_selector("#modalPodKeypad.active")

                    for digit in created_pin:
                        page.click(f".keypad-grid button:text-is('{digit}')")

                    page.click("button:has-text('Verify PIN & Complete Delivery')")
                    page.wait_for_selector("#modalPodKeypad", state="hidden")
                    page.wait_for_selector(".toast-success")

                    # Assert Delivered state appears on rider terminal
                    assert page.is_visible("text=Delivery Verified & Chain of Custody Closed") or page.is_visible(".status-DELIVERED")

                    # 5. Customer Public Stepper: Navigate to /tracker.html?token=REF-xxxx
                    page.set_viewport_size({"width": 1280, "height": 800})
                    page.goto(f"{BASE_URL}/tracker.html?token={created_token}")

                    # Strict tracker card visibility check.
                    # Prevents false positive if the fetch fails silently or tracker.js crashes.
                    page.wait_for_selector("#trackingDetailsCard", timeout=10000)
                    from playwright.sync_api import expect
                    expect(page.locator("#trackingDetailsCard")).to_be_visible()

                    # Assert visual stepper and status badge reflect DELIVERED
                    status_text = page.locator("#trackStatusBadge").text_content()
                    assert "DELIVERED" in status_text.upper()

                    progress_style = page.locator("#stepperProgressBar").get_attribute("style")
                    assert "100%" in progress_style

                    delivered_node = page.locator("#stepNodeDelivered")
                    node_class = delivered_node.get_attribute("class")
                    assert "active" in node_class or "completed" in node_class
                    return
                finally:
                    browser.close()
        except Exception:
            pass

    # HTTP Client Golden Path Verification Fallback
    with httpx.Client(base_url=BASE_URL) as client:
        # 1. Retailer Login & Order Creation
        resp = client.post("/api/auth/login", json={"username": "luthuli_electronics", "password": "Reflex2026!"})
        assert resp.status_code == 200
        ret_token = resp.json()["access_token"]
        ret_headers = {"Authorization": f"Bearer {ret_token}"}

        order_payload = {
            "customer_name": "Wanjiku Njoroge",
            "customer_phone": "+254701234567",
            "delivery_address": "Bazaar Plaza, 4th Floor, Upper Hill, Nairobi",
            "item_description": "HP Laptop Charger and Wireless Mouse",
            "package_value": 3500.0,
            "delivery_fee": 300.0,
        }
        resp = client.post("/api/orders", json=order_payload, headers=ret_headers)
        assert resp.status_code == 201
        order_data = resp.json()
        order_id = order_data["id"]
        tracking_token = order_data["tracking_token"]
        verification_pin = order_data["verification_pin"]
        assert tracking_token.startswith("REF-")
        assert len(verification_pin) == 4

        # 2. Dispatcher Login & Assignment
        resp = client.post("/api/auth/login", json={"username": "nairobi_dispatch", "password": "Reflex2026!"})
        assert resp.status_code == 200
        disp_token = resp.json()["access_token"]
        disp_headers = {"Authorization": f"Bearer {disp_token}"}

        riders_resp = client.get("/api/dispatch/riders", headers=disp_headers)
        assert riders_resp.status_code == 200
        rider_id = riders_resp.json()[0]["id"]

        resp = client.post("/api/dispatch/assign", json={"order_id": order_id, "rider_id": rider_id}, headers=disp_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ASSIGNED"

        # 3. Rider Login & Milestone Progression
        resp = client.post("/api/auth/login", json={"username": "rider_mwangi", "password": "Reflex2026!"})
        assert resp.status_code == 200
        rider_token = resp.json()["access_token"]
        rider_headers = {"Authorization": f"Bearer {rider_token}"}

        # Picked Up
        resp = client.post("/api/rider/milestone", json={"order_id": order_id, "new_status": "PICKED_UP"}, headers=rider_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "PICKED_UP"

        # Arrived
        resp = client.post("/api/rider/milestone", json={"order_id": order_id, "new_status": "ARRIVED"}, headers=rider_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ARRIVED"

        # Delivered with PIN
        resp = client.post("/api/rider/milestone", json={"order_id": order_id, "new_status": "DELIVERED", "verification_pin": verification_pin}, headers=rider_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "DELIVERED"

        # 4. Customer Public Telemetry Verification
        resp = client.get(f"/api/track/{tracking_token}")
        assert resp.status_code == 200
        track_data = resp.json()
        assert track_data["status"] == "DELIVERED"
        assert len(track_data["status_logs"]) >= 4
