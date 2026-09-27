"""Browser regression check against a running Vite preview, using isolated fixtures."""

import json

from playwright.sync_api import sync_playwright


def check():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1180, "height": 900})
        page.route(
            "**/auth/session",
            lambda route: route.fulfill(
                content_type="application/json",
                body=json.dumps({"user": {"email": "test@example.com"}}),
            ),
        )
        runs = [
            {
                "run_at": "2026-09-25T23:59:00-05:00",
                "target_date": day,
                "blocks": [
                    {
                        "start": "08:00",
                        "end": "10:00",
                        "room": "204BI",
                        "account": "test",
                        "status": "success",
                        "pdf": ".",
                    }
                ],
            }
            for day in ["2026-09-28", "2026-09-25"]
        ]
        page.route(
            "**/status.json",
            lambda route: route.fulfill(
                content_type="application/json", body=json.dumps({"runs": runs})
            ),
        )
        page.goto("http://127.0.0.1:4178/")
        page.get_by_role("heading", name="Reserved slots and confirmations").wait_for()
        assert page.locator("#bookings tbody tr").count() == 1
        assert page.locator("#bookings a").count() == 0
        assert page.get_by_text("Not captured", exact=True).count() == 1
        assert page.get_by_text("17%", exact=True).count() == 1
        assert page.get_by_role("button", name="Download PDF").count() == 0
        assert page.locator(".calendar-col").nth(1).locator(".booked").count() == 1
        page.locator("#booking-date").select_option("2026-09-25")
        assert page.locator(".calendar-col").nth(5).locator(".booked").count() == 1
        for width in (1180, 390):
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.unroute("**/status.json")
        page.route("**/status.json", lambda route: route.fulfill(status=503))
        page.reload()
        page.get_by_role("alert").wait_for()
        browser.close()
    print(
        "Dashboard checks passed: date coverage, calendar columns, "
        "no fake PDFs, mobile, fetch errors."
    )


if __name__ == "__main__":
    check()
