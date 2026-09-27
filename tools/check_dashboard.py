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

        # Week navigation moves the range but must NOT move the reservations
        # day, or the bookings table would blank out for weeks without bookings.
        assert page.locator(".week-range").inner_text()
        first_range = page.locator(".week-range").inner_text()
        bookings_before = page.locator("#bookings tbody tr").count()
        assert bookings_before >= 1
        page.get_by_role("button", name="Previous week").click()
        assert page.locator(".week-range").inner_text() != first_range
        assert page.locator("#bookings tbody tr").count() == bookings_before
        page.get_by_role("button", name="This week").click()
        this_week = page.locator(".week-range").inner_text()
        assert this_week
        page.get_by_role("button", name="This week").click()
        assert page.locator(".week-range").inner_text() == this_week

        # Diagrams: the wide SVG on desktop, the readable stack on mobile.
        page.set_viewport_size({"width": 1180, "height": 900})
        assert page.locator(".diagram-wide").is_visible()
        assert not page.locator(".diagram-stack").is_visible()
        page.set_viewport_size({"width": 390, "height": 900})
        assert page.locator(".diagram-stack").is_visible()
        assert page.locator(".diagram-stack li").count() >= 6
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        # Glass: one plate per optical panel, on every viewport.
        for width in (1180, 768, 390):
            page.set_viewport_size({"width": width, "height": 900})
            targets = page.evaluate("document.querySelectorAll('[data-optical]').length")
            plates = page.locator(".optical-plate").count()
            assert targets >= 4, targets
            assert plates == targets, (width, targets, plates)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        # Phones: weekends drop out of the week grid and the table stacks with
        # its labels, so nothing is clipped or pushed sideways.
        page.set_viewport_size({"width": 390, "height": 900})
        assert page.locator(".calendar-col.weekend").first.is_hidden()
        assert page.locator(".table-wrap thead").first.is_hidden()
        assert page.locator(".table-wrap td[data-label='Room']").count() >= 1
        assert (
            page.evaluate(
                """() => [...document.querySelectorAll('.page *')]
                    .filter((el) => el.getBoundingClientRect().right > innerWidth + 1
                        && !el.closest('.calendar-scroll, .diagram-wide, .diagram')).length"""
            )
            == 0
        )

        # Stat grid steps 4 / 2 / 1 without orphan cells.
        for width, expected in ((1180, 4), (768, 2), (320, 1)):
            page.set_viewport_size({"width": width, "height": 900})
            columns = page.evaluate(
                "getComputedStyle(document.querySelector('.card-grid'))"
                ".gridTemplateColumns.split(' ').length"
            )
            assert columns == expected, (width, columns, expected)

        # Clicking a day header selects exactly that day and highlights its
        # column; the bookings table follows it.
        page.set_viewport_size({"width": 1180, "height": 900})
        page.locator(".calendar-head").nth(2).click()
        assert page.locator(".calendar-col.selected").count() == 1

        # Fetch failures surface an alert instead of a blank dashboard.
        page.unroute("**/status.json")
        page.route("**/status.json", lambda route: route.fulfill(status=503))
        page.reload()
        page.get_by_role("alert").wait_for()
        browser.close()
    print(
        "Dashboard checks passed: sidebar, week nav, glass plates, "
        "responsive grid/table/calendar, fetch errors."
    )


if __name__ == "__main__":
    check()
