"""Browser regression check against a running Vite preview, using isolated fixtures.

Run a preview first, then point the checker at it:
    pnpm --filter web preview --port 4178 --strictPort
    .venv/bin/python tools/check_dashboard.py
"""

import json
import os

from playwright.sync_api import sync_playwright

BASE = os.environ.get("DASHBOARD_URL", "http://localhost:4178")


def check():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1180, "height": 900})
        page.route(
            "**/auth/session",
            lambda route: route.fulfill(
                content_type="application/json",
                body=json.dumps({"user": {"email": "test@example.com"}, "configured": True}),
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
                        "room": "Sala de estudio 204BI [Capacidad espacio: 10]",
                        "account": "test",
                        "status": "success",
                        "pdf": "bookings/x.pdf",
                        "pdf_status": "captured",
                    }
                ],
                "summary": {"total": 1, "succeeded": 1, "failed": 0},
            }
            for day in ["2026-09-28", "2026-09-25"]
        ]
        page.route(
            "**/status.json",
            lambda route: route.fulfill(
                content_type="application/json", body=json.dumps({"runs": runs})
            ),
        )
        page.goto(BASE)
        page.get_by_role("heading", name="Reserved slots and confirmations").wait_for()

        # Sidebar replaced the topbar and every link resolves to a real section.
        assert page.locator(".sidebar").count() == 1
        assert page.locator(".sidebar-nav a").count() == 4
        for href in page.eval_on_selector_all(
            ".sidebar-nav a", "links => links.map((l) => l.getAttribute('href'))"
        ):
            assert page.locator(href).count() == 1, href

        # Calendar week navigation moves between weeks and marks the day.
        assert page.locator(".week-range").inner_text()
        first_range = page.locator(".week-range").inner_text()
        page.get_by_role("button", name="Previous week").click()
        assert page.locator(".week-range").inner_text() != first_range
        assert page.locator(".calendar-col.selected").count() == 1

        # Diagrams: the wide SVG on desktop, the readable stack on mobile.
        page.set_viewport_size({"width": 1180, "height": 900})
        assert page.locator(".diagram-wide").is_visible()
        assert not page.locator(".diagram-stack").is_visible()
        page.set_viewport_size({"width": 390, "height": 900})
        assert page.locator(".diagram-stack").is_visible()
        assert page.locator(".diagram-stack li").count() >= 6
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        # Fetch failures surface an alert instead of a blank dashboard.
        page.unroute("**/status.json")
        page.route("**/status.json", lambda route: route.fulfill(status=503))
        page.reload()
        page.get_by_role("alert").wait_for()
        browser.close()
    print("Dashboard checks passed: sidebar, week nav, responsive diagram, fetch errors.")


if __name__ == "__main__":
    check()
