import argparse
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright


def verify_demo(url):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get("CYBERTWIN_CHROMIUM")
        )
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url, wait_until="domcontentloaded")
        score = page.locator("#demo-score")
        expect(score).to_have_text("63 / 100")

        email = page.get_by_role("button", name="Email account", exact=True)
        email.focus()
        email.press("Enter")
        expect(email).to_have_attribute("aria-pressed", "true")
        expect(page.locator("#demo-detail")).to_contain_text("Adds 30 points")

        mfa = page.locator('[data-action="mfa"]')
        mfa.check()
        expect(score).to_have_text("33 / 100")
        remaining = page.locator("#demo-priorities li")
        expect(remaining.first).to_contain_text("Set a unique forum password")

        with page.expect_download() as download_event:
            page.get_by_role("button", name="Download report").click()
        download = download_event.value
        assert download.suggested_filename == "cybertwin-demo-report.txt"
        report = Path(download.path()).read_text(encoding="utf-8")
        assert "Current score: 33/100" in report
        assert "Completed actions\n- Enable email MFA" in report
        assert "Set a unique forum password (23 points)" in report

        mfa.uncheck()
        expect(score).to_have_text("63 / 100")
        for signal in ("mfa", "password", "contact"):
            page.locator(f'[data-action="{signal}"]').check()
        expect(score).to_have_text("0 / 100")
        expect(remaining).to_have_count(0)

        page.get_by_role("button", name="Reset example").click()
        expect(score).to_have_text("63 / 100")
        expect(remaining).to_have_count(3)
        expect(page.get_by_role("button", name="Alex Rivera")).to_have_attribute(
            "aria-pressed", "true"
        )
        reference = {"name": "reference.txt", "mimeType": "text/plain", "buffer": b"known bytes"}
        page.locator("#media-reference").set_input_files(reference)
        candidate = page.locator("#media-candidate")
        candidate.set_input_files(reference)
        compare = page.get_by_role("button", name="Compare files")
        compare.click()
        expect(page.locator("#media-result")).to_contain_text("Fingerprints match")
        candidate.set_input_files({**reference, "buffer": b"changed bytes"})
        compare.click()
        expect(page.locator("#media-result")).to_contain_text("Fingerprints differ")

        page.get_by_role("button", name="Run compression test").click()
        result = page.locator("#media-compression")
        expect(result).to_contain_text("Mean RGB channel change")
        high = float(result.inner_text().split(": ")[1].split(" / ")[0])
        page.locator("#media-quality").select_option("0.35")
        page.get_by_role("button", name="Run compression test").click()
        expect(result).to_contain_text("Mean RGB channel change")
        low = float(result.inner_text().split(": ")[1].split(" / ")[0])
        assert low > high > 0, (high, low)
        assert not errors, errors
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="Test an existing CyberTwin deployment")
    args = parser.parse_args()
    if args.url:
        verify_demo(args.url)
    else:
        handler = partial(SimpleHTTPRequestHandler, directory="_site")
        with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
            worker = Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                verify_demo(f"http://127.0.0.1:{server.server_port}/#demo")
            finally:
                server.shutdown()
                worker.join()
    print("CyberTwin browser checks passed.")
