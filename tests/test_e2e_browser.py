"""Playwright automated end-to-end browser verification suite."""

import os
import threading
import time
import pytest
import uvicorn
from data.seed import init_db, seed_data
from backend.main import app

# Port for local test server
TEST_PORT = 8877
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"


@pytest.fixture(scope="session", autouse=True)
def live_server():
    """Launch live uvicorn ASGI server in background thread for browser testing."""
    test_db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    schema_path = os.path.join(test_db_dir, "schema.sql")
    db_path = os.path.join(test_db_dir, "reflex.db")

    conn = init_db(db_path=db_path, schema_path=schema_path)
    seed_data(conn)
    conn.close()

    config = uvicorn.Config(app=app, host="127.0.0.1", port=TEST_PORT, log_level="error")
    server = uvicorn.Server(config=config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    time.sleep(1.2)
    yield
    server.should_exit = True
    thread.join(timeout=2.0)


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Detect system Edge or Chrome if standalone chromium binary is not installed."""
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]

    for p in edge_paths:
        if os.path.exists(p):
            return {**browser_type_launch_args, "channel": "msedge"}

    for p in chrome_paths:
        if os.path.exists(p):
            return {**browser_type_launch_args, "channel": "chrome"}

    return browser_type_launch_args


def test_full_delivery_workflow_journey(page):
    """E2E Test: Retailer Logs Order -> Dispatcher Assigns -> Rider Completes POD -> Customer Tracks."""
    # 1. Open Application Login Screen
    page.goto(f"{BASE_URL}/")
    page.wait_for_selector("#loginForm")

    # 2. Login as Retailer (Luthuli Electronics)
    page.fill("#loginUsername", "luthuli_electronics")
    page.fill("#loginPassword", "Reflex2026!")
    page.click("#btnLoginSubmit")

    # Wait for Retailer View to activate
    page.wait_for_selector("#viewRetailer.active")
    assert page.is_visible("#retailerOrdersTable")

    # 3. Create New Delivery Order via Modal
    page.click("button:has-text('+ Log New Delivery Request')")
    page.wait_for_selector("#modalCreateOrder.active")

    page.fill("#orderCustomerName", "Wanjiku Kamau")
    page.fill("#orderCustomerPhone", "+254701234567")
    page.fill("#orderAddress", "Bazaar Plaza, 4th Floor, Upper Hill, Nairobi")
    page.fill("#orderItemDesc", "HP Laptop Charger and Wireless Mouse")
    page.fill("#orderValue", "3500")
    page.fill("#orderFee", "300")

    page.click("#btnSubmitOrder")
    page.wait_for_selector("#modalCreateOrder:not(.active)")

    # Retrieve generated order row from table
    page.wait_for_selector("#retailerOrdersBody tr")
    first_row = page.locator("#retailerOrdersBody tr").first
    token_el = first_row.locator(".token-pill")
    created_token = token_el.text_content().replace("↗", "").strip()

    pin_el = first_row.locator(".pin-tag")
    pin_text = pin_el.text_content()
    created_pin = pin_text.replace("PIN:", "").strip()

    assert created_token.startswith("REF-")
    assert len(created_pin) == 4

    # 4. Switch Session to Central Dispatcher
    page.click("button:has-text('Logout')")
    page.wait_for_selector("#viewLogin.active")

    page.fill("#loginUsername", "nairobi_dispatch")
    page.fill("#loginPassword", "Reflex2026!")
    page.click("#btnLoginSubmit")

    # Wait for Dispatcher View
    page.wait_for_selector("#viewDispatcher.active")
    page.wait_for_selector("#dispatcherOrdersBody tr")

    # Locate the created order and assign to rider John Mwangi
    order_row = page.locator(f"#dispatcherOrdersBody tr:has-text('{created_token}')")
    order_row.locator("select").select_option(label="John Mwangi (KMDF 420X)")
    order_row.locator("button:has-text('Assign')").click()

    # Wait for toast confirmation
    page.wait_for_selector(".toast-success")

    # 5. Switch Session to Rider John Mwangi
    page.click("button:has-text('Logout')")
    page.wait_for_selector("#viewLogin.active")

    page.fill("#loginUsername", "rider_mwangi")
    page.fill("#loginPassword", "Reflex2026!")
    page.click("#btnLoginSubmit")

    # Wait for Rider View
    page.wait_for_selector("#viewRider.active")
    page.wait_for_selector(f".task-card:has-text('{created_token}')")

    task_card = page.locator(f".task-card:has-text('{created_token}')")

    # 6. Confirm Pickup at Shop
    task_card.locator("button:has-text('Confirm Shop Package Pickup')").click()
    page.wait_for_selector(".toast-success")

    # 7. Confirm Arrival at Customer Doorstep
    task_card.locator("button:has-text('Confirm Arrival at Customer Doorstep')").click()
    page.wait_for_selector(".toast-success")

    # 8. Open POD Modal and enter Customer PIN
    task_card.locator("button:has-text('Enter Customer PIN / Scan POD')").click()
    page.wait_for_selector("#modalPodKeypad.active")

    # Enter 4-digit PIN via keypad buttons
    for digit in created_pin:
        page.click(f".keypad-grid button:text-is('{digit}')")

    page.click("button:has-text('Verify PIN & Complete Delivery')")
    page.wait_for_selector("#modalPodKeypad:not(.active)")
    page.wait_for_selector(".toast-success")

    # 9. Open Public Customer Tracker and verify final state
    page.goto(f"{BASE_URL}/track/{created_token}")
    page.wait_for_selector("#trackingDetailsCard")

    # Check status badge and completed stepper
    status_text = page.locator("#trackStatusBadge").text_content()
    assert "DELIVERED" in status_text.upper()

    progress_style = page.locator("#stepperProgressBar").get_attribute("style")
    assert "100%" in progress_style

    delivered_node = page.locator("#stepNodeDelivered")
    node_class = delivered_node.get_attribute("class")
    assert "active" in node_class or "completed" in node_class
