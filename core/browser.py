"""Playwright browser factory.

One place for the headless flag, the default timeout and the user agent so
every reservation block starts from the same browser configuration.
"""

from __future__ import annotations

from playwright.sync_api import Browser, Playwright, sync_playwright

DEFAULT_TIMEOUT_MS = 15_000
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class BrowserSession:
    """Context manager yielding a fresh Chromium browser per run.

    Every reservation block opens its own browser context so sessions never
    bleed into each other.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright: Playwright | None = None
        self.browser: Browser | None = None

    def __enter__(self) -> Browser:
        self._playwright = sync_playwright().start()
        self.browser = self._playwright.chromium.launch(headless=self.headless)
        return self.browser

    def new_context(self):
        if self.browser is None:
            raise RuntimeError("BrowserSession must be entered before use")
        return self.browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1366, "height": 900},
        )

    def __exit__(self, *_exc_info) -> None:
        if self.browser is not None:
            self.browser.close()
        if self._playwright is not None:
            self._playwright.stop()
