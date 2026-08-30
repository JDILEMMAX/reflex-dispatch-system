"""Automated Verification: Ensure ZERO horizontal overflow across all mobile viewports."""
import pytest

@pytest.mark.parametrize("width", [320, 360, 375, 390, 414, 768])
def test_mobile_overflow_all_viewports(page, width):
    """Verify document.documentElement.scrollWidth === window.innerWidth at every width."""
    page.set_viewport_size({"width": width, "height": 800})
    page.goto("http://127.0.0.1:8000")
    page.wait_for_selector("#loginForm")

    # 1. Login Page check
    sw_login, iw_login = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    assert sw_login == iw_login, f"Login page overflow at {width}px! scrollWidth ({sw_login}) > innerWidth ({iw_login})"

    # 2. Rider Mobile Terminal View check
    page.fill("#loginUsername", "rider_mwangi")
    page.fill("#loginPassword", "Reflex2026!")
    page.click("#btnLoginSubmit")
    page.wait_for_selector("#viewRider.active", timeout=8000)
    page.wait_for_timeout(300)

    sw_rider, iw_rider = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    assert sw_rider == iw_rider, f"Rider view overflow at {width}px! scrollWidth ({sw_rider}) > innerWidth ({iw_rider})"
