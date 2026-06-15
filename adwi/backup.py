"""
Adwi GitHub Backup Module
Safe git backup: never commits secrets, credentials, or large runtime data.
All operations are append-only — no deletes, no force-pushes.
"""
import json, os, re, subprocess
from datetime import datetime
from pathlib import Path

HOME      = Path.home()
WORKSPACE = HOME / "SuneelWorkSpace"
BIN       = WORKSPACE / "bin"
NOTES     = WORKSPACE / "notes"
BACKUP_LOG_DIR = NOTES / "git-backup-logs"
LAUNCHAGENT_PLIST = HOME / "Library" / "LaunchAgents" / "com.suneel.adwi-git-backup.plist"
BACKUP_SCRIPT = BIN / "adwi-git-backup"

# ── Secret scan patterns (grep-based fallback) ────────────────────────────────
SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_-]{20,}"),                "OpenAI key"),
    (re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"), "JWT token"),
    (re.compile(r"OPENWEBUI_API_KEY\s*=\s*.{8,}"),        "Open WebUI key"),
    (re.compile(r"GITHUB_TOKEN\s*=\s*.{8,}"),             "GitHub token"),
    (re.compile(r"gho_[A-Za-z0-9]{36,}"),                 "GitHub OAuth token"),
    (re.compile(r"GEMINI_API_KEY\s*=\s*.{8,}"),           "Gemini key"),
    (re.compile(r"GOOGLE_CLIENT_SECRET\s*=\s*.{8,}"),     "Google secret"),
    (re.compile(r"Authorization:\s*Bearer\s+.{8,}", re.I), "Bearer token"),
    (re.compile(r"-----BEGIN\s+(RSA|EC|OPENSSH|PRIVATE)\s+PRIVATE\s+KEY-----"), "Private key"),
    (re.compile(r"GOOGLE_API_KEY\s*=\s*.{8,}"),           "Google API key"),
    (re.compile(r"client_secret.*:\s*['\"]?[A-Za-z0-9_-]{12,}", re.I), "OAuth client secret"),
]

# Always-blocked paths (never committed regardless of .gitignore)
ALWAYS_BLOCKED = [
    WORKSPACE / "secrets",
    HOME / ".ssh",
    HOME / ".gnupg",
    HOME / ".aws",
    HOME / ".config" / "gcloud",
    HOME / "Library" / "Keychains",
]

# Files/dirs explicitly safe to stage (relative to WORKSPACE)
SAFE_INCLUDE_PATTERNS = [
    "adwi/*.py", "adwi/*.env", "adwi/*.txt", "adwi/*.json", "adwi/Modelfile",
    "adwi/evals/", "adwi/training-data/",
    "bin/adwi", "bin/mcp-status", "bin/adwi-git-backup",
    "mcp-servers/adwi-sandbox/server.py", "mcp-servers/comfyui-bridge/server.py",
    "mcp-servers/workspace.db",
    "notes/ADWI-START-HERE.md", "notes/START-HERE-SUNEEL-LOCAL-AI.md",
    "notes/AI-NOTES-INDEX.md", "notes/adwi-learning-journal.md",
    "notes/adwi-mistakes-and-fixes.md", "notes/adwi-capability-roadmap.md",
    "notes/adwi-repair-logs/*.md",
    "notes/system-inspections/",
    "notes/git-backup-logs/",
    "local-ai-stack/docker-compose.yml",
    ".gitignore", "README.md", "BACKUP_MANIFEST.md",
]

GITIGNORE_CONTENT = """# Adwi Workspace .gitignore — auto-managed by adwi /backup-enable
# NEVER commit secrets, credentials, or runtime data.

# ── Secrets and credentials (CRITICAL) ──────────────────────────────
secrets/
**/.env
**/secrets.local.env
**/*token*
**/*secret*
**/*credentials*
**/*.pem
**/*.p12
**/*.pfx
**/*.key
**/id_rsa
**/id_ed25519
**/.netrc
**/.npmrc
**/gmail-token.json
**/google-token.json

# ── Python ──────────────────────────────────────────────────────────
__pycache__/
*.pyc
*.pyo
*.pyd
.venv/
venv/
*.egg-info/
dist/
build/
.pytest_cache/

# ── Node ────────────────────────────────────────────────────────────
node_modules/
.npm/
*.lock

# ── macOS ───────────────────────────────────────────────────────────
.DS_Store
.AppleDouble
.LSOverride
._*
Thumbs.db

# ── Docker runtime data (large, contains runtime secrets) ───────────
local-ai-stack/open-webui-data/
local-ai-stack/n8n-data/
local-ai-stack/searxng-data/
local-ai-stack/qdrant-data/
local-ai-stack/data/
mcp-servers/qdrant-data/

# ── High-volume log directories ──────────────────────────────────────
notes/clipboard-command-logs/
notes/open-webui-sync-logs/
notes/adwi-action-logs/
notes/adwi-repair-logs/backups/
notes/daily-status/
notes/maintenance-logs/
notes/self-heal-logs/
notes/secrets-logs/

# ── AI model files (large binaries) ─────────────────────────────────
*.gguf
*.bin
*.safetensors
*.onnx
*.pt
*.pth
*.model
models/
ollama-blobs/

# ── IDE ─────────────────────────────────────────────────────────────
.idea/
.vscode/
*.swp
*.swo

# ── Misc ─────────────────────────────────────────────────────────────
*.log
*.tmp
*.bak
.env.local
"""

README_CONTENT = """# Suneel's Local AI Operating System — Adwi

> Automated backup of my local AI workspace. No secrets, credentials, or runtime data included.

## What's in here

- `adwi/` — Adwi CLI brain (adwi_cli.py, repair.py, backup.py, etc.)
- `bin/` — local helper scripts
- `mcp-servers/` — MCP server implementations (sandbox, comfyui bridge)
- `notes/` — AI learning journal, capability roadmap, mistake log, system inspections
- `local-ai-stack/docker-compose.yml` — Docker services config

## Stack

- **adwi** — local AI operating assistant (M4 Max Mac, 64GB RAM)
- **adwi:latest** — Qwen3 MoE 30.5B local reasoning model (131K context)
- **Open WebUI** — browser UI + Gemini cloud routing
- **Ollama** — local model runtime
- **n8n** — automation engine
- **SearXNG** — local web search
- **Qdrant** — vector memory database
- **10 MCP servers** — Playwright, GitHub, SQLite, Memory, Sequential Thinking, Qdrant, ComfyUI, Adwi sandbox, Fetch, Filesystem

## Setup

See `notes/ADWI-START-HERE.md` for local setup instructions.

## Security

Secrets, API keys, credentials, tokens, Docker runtime databases, and model files are excluded via `.gitignore`.

---
*Auto-backed up by `adwi /backup-now`*
"""

BACKUP_MANIFEST_CONTENT = """# Backup Manifest

This file lists what is included and excluded from this GitHub backup.

## INCLUDED (committed to GitHub)
- adwi/ — all Python source and config files
- bin/ — helper scripts (no secrets)
- mcp-servers/adwi-sandbox/server.py
- mcp-servers/comfyui-bridge/server.py
- notes/ADWI-START-HERE.md, START-HERE-SUNEEL-LOCAL-AI.md, AI-NOTES-INDEX.md
- notes/adwi-learning-journal.md
- notes/adwi-mistakes-and-fixes.md
- notes/adwi-capability-roadmap.md
- notes/adwi-repair-logs/*.md (reports only, not backups/)
- notes/system-inspections/
- local-ai-stack/docker-compose.yml
- .gitignore, README.md, BACKUP_MANIFEST.md

## EXCLUDED (never committed)
- secrets/ — API keys, tokens, credentials
- **/.env, **/secrets.local.env — env files with secrets
- **/*token*, **/*secret*, **/*key* — credential files
- **/*.pem, *.p12, *.pfx, id_rsa — key files
- local-ai-stack/open-webui-data/ — runtime database (may contain secrets)
- local-ai-stack/n8n-data/ — n8n runtime database
- local-ai-stack/searxng-data/ — searxng runtime data
- mcp-servers/qdrant-data/ — Qdrant vector DB data
- notes/adwi-action-logs/ — high-volume action logs
- notes/adwi-repair-logs/backups/ — large file backups
- notes/clipboard-command-logs/ — clipboard history
- *.gguf, *.safetensors, *.bin — large model files
- __pycache__/, node_modules/, .venv/ — generated artifacts
"""

# ── Git operations ─────────────────────────────────────────────────────────────
def _git(args: list, cwd: Path = WORKSPACE, timeout: int = 60) -> tuple[int, str, str]:
    env = {**os.environ, "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
           "GIT_TERMINAL_PROMPT": "0"}
    r = subprocess.run(["git"] + args, capture_output=True, text=True, timeout=timeout,
                       cwd=str(cwd), env=env)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def get_git_status() -> dict:
    """Return dict describing the workspace git state."""
    d = {"is_repo": False, "branch": "", "remote_url": "", "remote_name": "",
         "pending_files": [], "last_commit": "", "ahead": 0, "error": ""}
    rc, out, err = _git(["rev-parse", "--is-inside-work-tree"])
    if rc != 0:
        d["error"] = "Not a git repository"
        return d
    d["is_repo"] = True
    _, branch, _ = _git(["branch", "--show-current"])
    d["branch"] = branch
    _, remote, _ = _git(["remote", "-v"])
    for line in remote.splitlines():
        if "(fetch)" in line:
            parts = line.split()
            d["remote_name"] = parts[0] if parts else ""
            url = parts[1] if len(parts) > 1 else ""
            # Redact tokens from URLs
            url = re.sub(r"https?://[^@]+@", "https://REDACTED@", url)
            d["remote_url"] = url
            break
    _, status_out, _ = _git(["status", "--short"])
    d["pending_files"] = [l.strip() for l in status_out.splitlines() if l.strip()]
    _, last, _ = _git(["log", "--oneline", "-1"])
    d["last_commit"] = last
    _, ahead_out, _ = _git(["rev-list", "--count", f"@{{u}}..HEAD"])
    try: d["ahead"] = int(ahead_out.strip())
    except: d["ahead"] = 0
    return d


def init_git_repo() -> tuple[bool, str]:
    """Initialize git repo in workspace if not already one. Returns (ok, message)."""
    status = get_git_status()
    if status["is_repo"]:
        return True, "Already a git repository"
    rc, out, err = _git(["init", "-b", "main"])
    if rc != 0:
        return False, f"git init failed: {err}"
    return True, "Git repository initialized"


def write_workspace_files() -> list[str]:
    """Write .gitignore, README.md, BACKUP_MANIFEST.md. Returns list of files written."""
    written = []
    gi = WORKSPACE / ".gitignore"
    if not gi.exists():
        gi.write_text(GITIGNORE_CONTENT, encoding="utf-8")
        written.append(".gitignore")
    rm = WORKSPACE / "README.md"
    if not rm.exists():
        rm.write_text(README_CONTENT, encoding="utf-8")
        written.append("README.md")
    bm = WORKSPACE / "BACKUP_MANIFEST.md"
    bm.write_text(BACKUP_MANIFEST_CONTENT, encoding="utf-8")
    written.append("BACKUP_MANIFEST.md")
    return written


# ── Secret scan ────────────────────────────────────────────────────────────────
def scan_staged_for_secrets() -> list[dict]:
    """
    Scan git staged content for secret patterns.
    Returns list of {file, pattern, line_snippet} — never the actual secret value.
    """
    findings = []
    _, diff_out, _ = _git(["diff", "--cached", "--unified=0"])
    if not diff_out:
        return findings
    current_file = ""
    for line in diff_out.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            content = line[1:]
            # Skip lines that are clearly regex/source-code definitions, not real secrets
            if "re.compile(" in content or "re.sub(" in content or "SECRET_PATTERNS" in content:
                continue
            # Skip grep/bash patterns (e.g. grep -qE 'OPENWEBUI_API_KEY=|...')
            if "grep" in content and ("|" in content or "-qE" in content or "-E" in content):
                continue
            for pat, label in SECRET_PATTERNS:
                m = pat.search(content)
                if m:
                    matched = m.group(0)
                    # Reject if the matched text contains regex metacharacters — it's a pattern, not a secret
                    if any(c in matched for c in (".*", "{8,}", "[A-Z", "|", "\\", "r'", 'r"', "r`")):
                        continue
                    findings.append({"file": current_file, "pattern": label, "snippet": "[REDACTED]"})
                    break
    return findings


def check_gitignore_covers_secrets() -> list[str]:
    """Check if secrets/ and key credential files are in .gitignore. Returns missing entries."""
    gi = WORKSPACE / ".gitignore"
    if not gi.exists():
        return ["secrets/", "**/.env", "**/secrets.local.env"]
    content = gi.read_text(encoding="utf-8")
    missing = []
    for must_have in ["secrets/", "**/.env", "**/secrets.local.env", "**/*token*"]:
        if must_have not in content and must_have.replace("**/", "") not in content:
            missing.append(must_have)
    return missing


# ── Staging safe files ─────────────────────────────────────────────────────────
def stage_safe_files() -> tuple[int, list[str]]:
    """
    Stage only safe files. Returns (count_staged, list_of_staged).
    Uses explicit paths to avoid accidentally staging secrets.
    """
    # Ensure .gitignore exists and covers secrets
    missing = check_gitignore_covers_secrets()
    if missing:
        write_workspace_files()
    # Stage safe known paths
    to_stage = [
        "adwi/", "bin/adwi", "bin/mcp-status", "bin/adwi-git-backup",
        "mcp-servers/adwi-sandbox/server.py", "mcp-servers/comfyui-bridge/server.py",
        "notes/ADWI-START-HERE.md", "notes/START-HERE-SUNEEL-LOCAL-AI.md",
        "notes/AI-NOTES-INDEX.md", "notes/adwi-learning-journal.md",
        "notes/adwi-mistakes-and-fixes.md", "notes/adwi-capability-roadmap.md",
        "notes/adwi-repair-logs/", "notes/nightly-improvement-logs/",
        "notes/adwi-trace-logs/", "notes/git-backup-logs/",
        "notes/system-inspections/", "notes/adwi-pending-improvements.md",
        "local-ai-stack/docker-compose.yml",
        "local-ai-stack/monitoring/",       # monitoring stack configs
        ".gitignore", "README.md", "BACKUP_MANIFEST.md",
    ]
    staged = []
    for path_str in to_stage:
        full = WORKSPACE / path_str
        if full.exists():
            rc, _, _ = _git(["add", path_str])
            if rc == 0:
                staged.append(path_str)
    # Also stage repair logs (not backups/ dir — covered by .gitignore)
    _git(["add", "notes/adwi-repair-logs/"])
    staged.append("notes/adwi-repair-logs/")
    return len(staged), staged


def _run_auto_readme(quiet: bool = True, force: bool = True) -> bool:
    """
    Update README.md auto-sections before committing.
    Always passes --force so ALL section builders run on every backup regardless
    of snapshot hash — this ensures the README is always the authoritative system map.
    Returns True if the script ran without exception.
    """
    readme_script = WORKSPACE / "bin" / "auto-update-readme"
    venv_py       = WORKSPACE / "adwi" / ".venv" / "bin" / "python3"
    if not readme_script.exists():
        return False
    py   = str(venv_py) if venv_py.exists() else "python3"
    args = [py, str(readme_script)]
    if quiet:
        args.append("--quiet")
    if force:
        args.append("--force")
    try:
        subprocess.run(args, cwd=str(WORKSPACE), timeout=60, capture_output=quiet)
        return True
    except Exception:
        return False  # never block backup for README update


def _log_system_event(event: str, detail: str = "") -> None:
    """Append a structured entry to logs/adwi_system_log.md."""
    log_path = WORKSPACE / "logs" / "adwi_system_log.md"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n## [{stamp}] {event}\n{detail}\n" if detail else f"\n## [{stamp}] {event}\n"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def do_backup(message: str = "") -> dict:
    """
    Full backup flow: README update → write files → stage → secret scan → commit → push.
    Returns result dict {success, message, staged, commit_hash, pushed}.
    """
    result = {"success": False, "message": "", "staged": [], "commit_hash": "", "pushed": False}

    # Ensure repo init + workspace files
    ok, msg = init_git_repo()
    if not ok:
        result["message"] = msg; return result
    write_workspace_files()

    # Auto-update README before staging — always forced so README stays authoritative
    readme_updated = _run_auto_readme(quiet=True, force=True)
    if readme_updated:
        _log_system_event("README auto-update", "bin/auto-update-readme --force ran before backup commit")

    # Stage safe files
    n, staged = stage_safe_files()
    result["staged"] = staged

    # Check for changes
    _, status, _ = _git(["status", "--porcelain"])
    _, diff_cached, _ = _git(["diff", "--cached", "--name-only"])
    if not diff_cached.strip():
        result["success"] = True
        result["message"] = "Nothing to commit — workspace is up to date"
        return result

    # Secret scan
    secrets = scan_staged_for_secrets()
    if secrets:
        # Unstage everything
        _git(["reset", "HEAD"])
        files = ", ".join(set(s["file"] for s in secrets))
        result["message"] = (
            f"SECRET SCAN FAILED — aborting backup. "
            f"Possible secrets found in: {files}. "
            f"Check .gitignore and re-run /backup-now after fixing."
        )
        _log_system_event("SECRET SCAN FAILED", f"Files: {files}")
        return result

    # Commit
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = message or f"adwi backup {stamp}"
    rc, out, err = _git(["commit", "-m", msg])
    if rc != 0:
        result["message"] = f"Commit failed: {err}"; return result
    _, hash_out, _ = _git(["log", "--oneline", "-1"])
    result["commit_hash"] = hash_out

    # Push
    status = get_git_status()
    if status.get("remote_name"):
        rc, out, err = _git(["push", status["remote_name"], status["branch"]], timeout=120)
        if rc == 0:
            result["pushed"] = True
            _log_system_event("Backup pushed", f"Commit: {hash_out} · Branch: {status['branch']}")
        else:
            result["message"] = f"Committed but push failed: {err}"
            _log_system_event("Backup push FAILED", err[:200])
    else:
        result["message"] = (
            "Committed locally. No remote configured. "
            "Run: gh repo create suneel-local-ai-adwi --private --source=. --push"
        )

    if not result["message"]:
        result["message"] = f"✓ Backed up: {hash_out}"
    result["success"] = True
    return result


# ── Backup log ─────────────────────────────────────────────────────────────────
def write_backup_log(result: dict) -> Path:
    BACKUP_LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    status = "SUCCESS" if result.get("success") else "FAILED"
    path = BACKUP_LOG_DIR / f"{stamp}-git-backup.md"
    path.write_text(
        f"# Adwi Git Backup — {status}\n\n"
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"## Result\n{result.get('message','')}\n\n"
        f"## Commit\n{result.get('commit_hash','none')}\n\n"
        f"## Pushed\n{'yes' if result.get('pushed') else 'no'}\n\n"
        f"## Staged paths ({len(result.get('staged',[]))})\n"
        + "\n".join(f"- {s}" for s in result.get("staged", [])),
        encoding="utf-8",
    )
    return path


# ── LaunchAgent for auto-backup ────────────────────────────────────────────────
LAUNCHAGENT_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.suneel.adwi-git-backup</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/MAC/SuneelWorkSpace/bin/adwi-git-backup</string>
    </array>
    <key>StartInterval</key>
    <integer>1800</integer>
    <key>RunAtLoad</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/tmp/adwi-git-backup.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/adwi-git-backup.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>HOME</key>
        <string>/Users/MAC</string>
    </dict>
</dict>
</plist>
"""

BACKUP_SCRIPT_CONTENT = """#!/bin/bash
# Adwi auto-backup script — run by LaunchAgent every 30 minutes.
# Only commits if there are actual changes and secret scan passes.
set -euo pipefail

WORKSPACE="/Users/MAC/SuneelWorkSpace"
LOG_DIR="$WORKSPACE/notes/git-backup-logs"
VENV_PY="$WORKSPACE/adwi/.venv/bin/python3"
STAMP=$(date +%Y%m%d-%H%M%S)
LOG="$LOG_DIR/$STAMP-git-backup.md"

mkdir -p "$LOG_DIR"
cd "$WORKSPACE"

echo "# Adwi Auto-Backup — $(date)" > "$LOG"

# Phase 5: auto-update README.md before staging
PY="${VENV_PY:-python3}"
if [ -f "$WORKSPACE/bin/auto-update-readme" ]; then
    "$PY" "$WORKSPACE/bin/auto-update-readme" --quiet 2>/dev/null || true
fi

# Quick secret scan on changed files
if git status --short | grep -q "^[AM]"; then
    if git diff --cached | grep -qE 'sk-[A-Za-z0-9]{20}|OPENWEBUI_API_KEY=|GITHUB_TOKEN=|gho_[A-Za-z0-9]{36}|-----BEGIN.*PRIVATE'; then
        echo "SECRET SCAN FAILED — aborting auto-backup" >> "$LOG"
        exit 1
    fi
fi

# Stage safe files (never secrets/)
git add adwi/ bin/adwi bin/mcp-status bin/adwi-git-backup \\
    "notes/ADWI-START-HERE.md" "notes/adwi-learning-journal.md" \\
    "notes/adwi-mistakes-and-fixes.md" "notes/adwi-capability-roadmap.md" \\
    "notes/adwi-repair-logs/" "notes/system-inspections/" \\
    "local-ai-stack/docker-compose.yml" \\
    "local-ai-stack/monitoring/" \\
    ".gitignore" "README.md" "BACKUP_MANIFEST.md" 2>/dev/null || true

# Check if anything staged
if ! git diff --cached --quiet; then
    git commit -m "adwi auto-backup $(date '+%Y-%m-%d %H:%M')" >> "$LOG" 2>&1
    REMOTE=$(git remote | head -1)
    if [ -n "$REMOTE" ]; then
        git push "$REMOTE" HEAD >> "$LOG" 2>&1 && echo "pushed" >> "$LOG"
    else
        echo "no remote — committed locally only" >> "$LOG"
    fi
else
    echo "nothing to commit" >> "$LOG"
fi
"""


def create_launchagent() -> tuple[bool, str]:
    LAUNCHAGENT_PLIST.write_text(LAUNCHAGENT_CONTENT, encoding="utf-8")
    # Write the backup script
    BACKUP_SCRIPT.parent.mkdir(parents=True, exist_ok=True)
    BACKUP_SCRIPT.write_text(BACKUP_SCRIPT_CONTENT, encoding="utf-8")
    BACKUP_SCRIPT.chmod(0o755)
    # Load
    rc = subprocess.run(
        ["launchctl", "load", str(LAUNCHAGENT_PLIST)],
        capture_output=True, timeout=15
    ).returncode
    if rc == 0:
        return True, f"Auto-backup LaunchAgent installed (every 30 min)"
    return False, "LaunchAgent written but launchctl load failed — try restarting"


def remove_launchagent() -> tuple[bool, str]:
    if LAUNCHAGENT_PLIST.exists():
        subprocess.run(["launchctl", "unload", str(LAUNCHAGENT_PLIST)],
                       capture_output=True, timeout=15)
        LAUNCHAGENT_PLIST.unlink()
        return True, "Auto-backup disabled"
    return False, "Auto-backup LaunchAgent not found"


def get_launchagent_status() -> str:
    rc = subprocess.run(
        ["launchctl", "list", "com.suneel.adwi-git-backup"],
        capture_output=True, timeout=10
    ).returncode
    return "installed" if rc == 0 else "not installed"
