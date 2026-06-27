"""Widget: visual approval queue — items awaiting Suneel's OK."""
import json
import os

WORKSPACE = os.path.expanduser("~/SuneelWorkSpace")
APPROVAL_QUEUE_PATH = os.path.join(WORKSPACE, "eyes/visual/visual_approval_queue.json")


def get_data() -> dict:
    if not os.path.exists(APPROVAL_QUEUE_PATH):
        return {"items": [], "total": 0}
    try:
        queue = json.load(open(APPROVAL_QUEUE_PATH))
        pending = [i for i in queue if i.get("status") == "awaiting_approval"]
        return {"items": pending[:5], "total": len(pending)}
    except Exception:
        return {"items": [], "total": 0}


def render_html() -> str:
    data = get_data()
    items = data.get("items", [])
    total = data.get("total", 0)
    if not items:
        return '<div style="color:var(--text-dim);font-size:11px">No pending approvals</div>'
    rows = ""
    for item in items:
        imp = item.get("improvement", item.get("issue", {}))
        title = imp.get("title", imp.get("description", "Unknown"))[:50]
        qat = item.get("queued_at", "")
        rows += (
            f'<div class="cc-approval-row">'
            f'<span class="cc-approval-title">{title}</span>'
            f'<button class="cc-approval-btn cc-approve" onclick="approveItem(\'{qat}\')">✅</button>'
            f'<button class="cc-approval-btn cc-reject" onclick="rejectItem(\'{qat}\')">✕</button>'
            f'</div>'
        )
    badge = f'<div style="color:var(--text-dim);font-size:10px;margin-top:4px">{total} total pending</div>'
    return f'<div class="cc-approval-list">{rows}</div>{badge}'


if __name__ == "__main__":
    print(render_html())
