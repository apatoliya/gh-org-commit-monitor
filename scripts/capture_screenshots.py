"""Capture dashboard screenshots using Playwright."""

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright


PAGES = [
    ("/", "overview"),
    ("/repos", "repos"),
    ("/authors", "authors"),
    ("/details", "details"),
]

OUTPUT_DIR = Path("docs/screenshots")
BASE_URL = "http://127.0.0.1:8050"


def wait_for_server(url, timeout=30):
    """Poll until the server responds."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Start the Dash server
    print("Starting dashboard server...")
    server = subprocess.Popen(
        [sys.executable, "run.py", "dashboard"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if not wait_for_server(BASE_URL):
        server.terminate()
        print("ERROR: Dashboard server failed to start within 30s")
        sys.exit(1)

    print("Server is ready.")

    console_errors = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})

            # Capture console messages
            page.on("console", lambda msg: console_errors.append(
                f"[{msg.type}] {msg.text}"
            ) if msg.type in ("error", "warning") else None)

            for path, name in PAGES:
                url = f"{BASE_URL}{path}"
                print(f"Capturing {name} ({url})...")
                page.goto(url, wait_until="networkidle")
                # Wait for Dash callbacks to render + animations to settle
                page.wait_for_timeout(5000)

                # Check if content loaded
                content = page.content()
                has_content = "kpi-card" in content or "dash-table" in content or "plotly" in content.lower()
                print(f"  Content loaded: {has_content}")

                page.screenshot(
                    path=str(OUTPUT_DIR / f"{name}.png"),
                    full_page=True,
                )
                print(f"  Saved {name}.png")

            browser.close()
    finally:
        server.terminate()
        server.wait()

    if console_errors:
        print("\nBrowser console errors/warnings:")
        for err in console_errors:
            print(f"  {err}")
    else:
        print("\nNo browser console errors.")

    print(f"\nAll screenshots saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
