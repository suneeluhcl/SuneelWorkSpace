"""
visual_monitor.py
Randomly takes screenshots of the dashboard in the background.
Interval: random between 15-45 minutes.
After each screenshot, triggers vision_analyzer.py.
"""
import asyncio
import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE.parent))

MIN_INTERVAL_MINUTES = 15
MAX_INTERVAL_MINUTES = 45
STATE_PATH = _HERE / "visual_state.json"


async def monitor_loop() -> None:
    print(f"✅ Visual Monitor started — screenshots every {MIN_INTERVAL_MINUTES}-{MAX_INTERVAL_MINUTES} min")
    while True:
        interval = random.randint(MIN_INTERVAL_MINUTES * 60, MAX_INTERVAL_MINUTES * 60)
        print(f"⏰ Next screenshot in {interval // 60}m {interval % 60}s")
        await asyncio.sleep(interval)

        print("📸 Taking dashboard screenshot…")
        from eyes.visual.screenshot_manager import take_screenshot
        screenshot_path = take_screenshot(label="monitor")

        if screenshot_path:
            print(f"✅ Screenshot saved: {screenshot_path}")
            from eyes.visual.vision_analyzer import analyze_screenshot
            analysis = analyze_screenshot(screenshot_path)
            issues = analysis.get("issues", [])
            if issues:
                print(f"⚠️  Found {len(issues)} visual issues — queuing for repair")
                _queue_visual_issues(issues, screenshot_path)
            else:
                print("✅ No visual issues detected")
        else:
            print("⚠️  Screenshot failed — dashboard may not be running")


def _queue_visual_issues(issues: list, screenshot_path: str) -> None:
    queue_path = _HERE / "visual_repair_queue.json"
    queue: list = []
    if queue_path.exists():
        try:
            queue = json.loads(queue_path.read_text())
        except Exception:
            pass
    queue.append({
        "screenshot": screenshot_path,
        "issues": issues,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    })
    queue_path.write_text(json.dumps(queue, indent=2))


if __name__ == "__main__":
    asyncio.run(monitor_loop())
