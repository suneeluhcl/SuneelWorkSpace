"""
screenshot_manager.py
Takes, organizes, archives, and manages all workspace screenshots.
NEVER saves screenshots to workspace root — always to visual/screenshots/.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

_HERE = Path(__file__).parent
WORKSPACE = _HERE.parent

SCREENSHOT_DIR = WORKSPACE / "visual/screenshots/dashboard"
UPLOAD_DIR     = WORKSPACE / "visual/screenshots/user_uploads"
ARCHIVE_DIR    = WORKSPACE / "visual/screenshots/archive"
STATE_PATH     = WORKSPACE / "visual/visual_state.json"
REPAIR_LOG     = WORKSPACE / "visual/visual_repair_log.jsonl"

MAX_DASHBOARD_SCREENSHOTS = 50
ARCHIVE_AFTER_DAYS = 7
DASHBOARD_URL = "http://localhost:7777"


def ensure_dirs() -> None:
    for d in (SCREENSHOT_DIR, UPLOAD_DIR, ARCHIVE_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _find_chrome() -> str | None:
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "chromium",
        "google-chrome",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
        try:
            if subprocess.run(["which", c], capture_output=True).returncode == 0:
                return c
        except Exception:
            pass
    return None


def take_screenshot(label: str = "auto", url: str = DASHBOARD_URL) -> str | None:
    """Take a screenshot of the dashboard. Returns path to saved file or None."""
    ensure_dirs()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"dashboard_{label}_{ts}.png"
    filepath = SCREENSHOT_DIR / filename
    success = False

    chrome = _find_chrome()
    if chrome:
        # Method 1: Chrome/Chromium headless
        try:
            result = subprocess.run([
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--window-size=1920,1080",
                "--hide-scrollbars",
                f"--screenshot={filepath}",
                url,
            ], capture_output=True, timeout=30)
            if result.returncode == 0 and filepath.exists():
                success = True
        except Exception:
            pass

    if not success:
        # Method 2: playwright fallback
        try:
            script = f"""
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={{'width': 1920, 'height': 1080}})
    page.goto('{url}', wait_until='networkidle', timeout=15000)
    page.wait_for_timeout(2000)
    page.screenshot(path='{filepath}', full_page=False)
    browser.close()
"""
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True, timeout=60,
            )
            if result.returncode == 0 and filepath.exists():
                success = True
        except Exception:
            pass

    if not success:
        return None

    _update_state({
        "last_screenshot": str(filepath),
        "last_screenshot_at": datetime.now(timezone.utc).isoformat(),
        "last_label": label,
    })
    _cleanup_old_screenshots()
    _log_event("screenshot_taken", {"path": str(filepath), "label": label, "success": True})
    return str(filepath)


def save_user_upload(image_path: str, description: str = "") -> str:
    """Save a user-uploaded image to the organized upload directory."""
    ensure_dirs()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ext = Path(image_path).suffix or ".png"
    filename = f"upload_{ts}{ext}"
    dest = UPLOAD_DIR / filename
    shutil.copy2(image_path, dest)
    meta_path = Path(str(dest) + ".json")
    meta_path.write_text(json.dumps({
        "original_path": image_path,
        "description": description,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))
    return str(dest)


def _cleanup_old_screenshots() -> None:
    ensure_dirs()
    cutoff = time.time() - (ARCHIVE_AFTER_DAYS * 86400)
    screenshots = sorted(SCREENSHOT_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime)
    for f in screenshots:
        if f.stat().st_mtime < cutoff:
            shutil.move(str(f), str(ARCHIVE_DIR / f.name))

    screenshots = sorted(SCREENSHOT_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime)
    if len(screenshots) > MAX_DASHBOARD_SCREENSHOTS:
        for f in screenshots[:-MAX_DASHBOARD_SCREENSHOTS]:
            shutil.move(str(f), str(ARCHIVE_DIR / f.name))


def get_latest_screenshot() -> dict | None:
    shots = list_screenshots(1)
    return shots[0] if shots else None


def list_screenshots(limit: int = 10) -> list:
    if not SCREENSHOT_DIR.exists():
        return []
    files = sorted(SCREENSHOT_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    result = []
    for f in files[:limit]:
        st = f.stat()
        result.append({
            "path": str(f),
            "filename": f.name,
            "size_kb": round(st.st_size / 1024, 1),
            "taken_at": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
        })
    return result


def _update_state(updates: dict) -> None:
    state: dict = {}
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    state.update(updates)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def _log_event(event: str, data: dict = None) -> None:
    try:
        entry = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **(data or {})}
        with open(REPAIR_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    import json as _json
    print("Taking screenshot...")
    path = take_screenshot(label="manual")
    print(f"Result: {path}")
    print(_json.dumps(list_screenshots(5), indent=2))
