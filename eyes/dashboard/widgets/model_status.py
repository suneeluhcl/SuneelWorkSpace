"""Widget: live model quota and availability status."""
import os
import sys

WORKSPACE = os.path.expanduser("~/SuneelWorkSpace")


def get_data() -> dict:
    try:
        sys.path.insert(0, WORKSPACE)
        from heart.model_router.quota_tracker import get_status
        return get_status()
    except Exception as e:
        return {"models": [], "error": str(e)[:100]}


def render_html() -> str:
    data = get_data()
    models = data.get("models", [])
    if not models:
        return '<div style="color:var(--text-dim);font-size:11px">Model router not initialized</div>'
    rows = ""
    for m in models:
        icon = "🟢" if m["available"] else "🔴"
        rows += (
            f'<div class="cc-model-row">'
            f'<span class="cc-model-icon">{icon}</span>'
            f'<span class="cc-model-name">{m["id"]}</span>'
            f'<span class="cc-model-tokens">{m["tokens_used_today"]:,}</span>'
            f'<span class="cc-model-calls">{m["calls_today"]}x</span>'
            f'</div>'
        )
    return f'<div class="cc-model-list">{rows}</div>'


if __name__ == "__main__":
    print(render_html())
