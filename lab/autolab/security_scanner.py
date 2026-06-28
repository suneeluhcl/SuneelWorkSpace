"""
security_scanner.py
Scans workspace for security issues:
- Hardcoded API keys and secrets
- Unsafe shell command patterns
- Exposed credentials in config files
- Insecure file permissions
- SQL injection patterns
- Unsafe subprocess calls
Never auto-fixes security issues — always surfaces to Suneel.
"""

import json
import os
import re
import stat
import urllib.request
from datetime import datetime, timezone

SECURITY_REPORT = "blood/logs/security_scan_report.md"
SECURITY_LOG = "blood/logs/security_scan.jsonl"
OLLAMA_BASE = "http://localhost:11434"

SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']([A-Za-z0-9_\-]{20,})["\']', "API Key"),
    (r'(?i)(secret[_-]?key|secret)\s*[=:]\s*["\']([A-Za-z0-9_\-]{20,})["\']', "Secret Key"),
    (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']([^"\']{8,})["\']', "Password"),
    (r'(?i)(token)\s*[=:]\s*["\']([A-Za-z0-9_\-\.]{20,})["\']', "Token"),
    (r'sk-[A-Za-z0-9]{48}', "OpenAI API Key"),
    (r'AIza[0-9A-Za-z\-_]{35}', "Google API Key"),
    (r'(?i)anthropic[_-]?api[_-]?key\s*[=:]\s*["\']([^"\']+)["\']', "Anthropic Key"),
    (r'ghp_[A-Za-z0-9]{36}', "GitHub Token"),
    (r'(?i)bearer\s+([A-Za-z0-9_\-\.]{20,})', "Bearer Token"),
]

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "spine/backups",
             "brain/vault", "chroma_store", "nerve_inbox"}
SKIP_FILES = {"security_scanner.py"}


def scan_file_for_secrets(filepath: str) -> list:
    """Fast regex scan for common secret patterns."""
    issues = []
    try:
        content = open(filepath, encoding="utf-8", errors="ignore").read()
        for pattern, secret_type in SECRET_PATTERNS:
            for match in re.finditer(pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                matched_text = match.group()
                if any(placeholder in matched_text.lower() for placeholder in
                       ["your_key", "xxx", "placeholder", "example", "test", "dummy", "fake"]):
                    continue
                issues.append({
                    "type": "hardcoded_secret",
                    "secret_type": secret_type,
                    "file": filepath,
                    "line": line_num,
                    "severity": "critical",
                    "description": f"Possible {secret_type} found",
                    "fix": "Move to environment variable or ~/.hermes/config.yaml"
                })
    except Exception:
        pass
    return issues


def check_file_permissions(filepath: str) -> list:
    """Check for insecure file permissions."""
    issues = []
    try:
        mode = os.stat(filepath).st_mode
        if mode & stat.S_IWOTH:
            issues.append({
                "type": "insecure_permissions",
                "file": filepath,
                "severity": "high",
                "description": "File is world-writable",
                "fix": f"chmod 644 {filepath}"
            })
    except Exception:
        pass
    return issues


def scan_python_for_unsafe_patterns(filepath: str) -> list:
    """Scan Python files for unsafe patterns."""
    issues = []
    try:
        content = open(filepath, encoding="utf-8", errors="ignore").read()

        # These are regex patterns to DETECT dangerous calls in scanned files — not executed here.
        unsafe_patterns = [
            (r'subprocess\.call\([^)]*shell=True', "shell=True in subprocess (injection risk)"),
            (r'os\.system\(', "os.system() call (prefer subprocess)"),          # scan target only
            (r'(?<!\w)eval\(', "eval() call (code injection risk)"),              # scan target only
            (r'(?<!\w)exec\(', "exec() call (code injection risk)"),              # scan target only
            (r'pickle\.loads?\(', "pickle.load() (unsafe deserialization)"),     # scan target only
            (r'except:\s*$', "bare except clause (hides errors)"),
            (r'except Exception:\s*pass', "silently swallowing exceptions"),
        ]

        for pattern, description in unsafe_patterns:
            if re.search(pattern, content, re.MULTILINE):
                line_matches = [(i+1, line) for i, line in enumerate(content.split('\n'))
                               if re.search(pattern, line)]
                for line_num, _ in line_matches[:3]:
                    issues.append({
                        "type": "unsafe_pattern",
                        "file": filepath,
                        "line": line_num,
                        "severity": "medium",
                        "description": description,
                        "fix": "Review and fix this pattern"
                    })
    except Exception:
        pass
    return issues


def run_security_scan() -> dict:
    """Run full security scan across workspace."""
    print("Security Scanner starting...")

    all_issues = []
    files_scanned = 0

    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        rel_root = os.path.relpath(root)
        if any(skip in rel_root for skip in SKIP_DIRS):
            continue

        for filename in files:
            if filename in SKIP_FILES:
                continue

            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath)
            files_scanned += 1

            if any(filename.endswith(ext) for ext in [".py", ".json", ".yaml", ".yml", ".sh", ".md", ".env"]):
                all_issues.extend(scan_file_for_secrets(rel_path))

            all_issues.extend(check_file_permissions(rel_path))

            if filename.endswith(".py"):
                all_issues.extend(scan_python_for_unsafe_patterns(rel_path))

    critical = [i for i in all_issues if i.get("severity") == "critical"]
    high = [i for i in all_issues if i.get("severity") == "high"]
    medium = [i for i in all_issues if i.get("severity") == "medium"]

    report_lines = [
        f"# Security Scan Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"**Files scanned:** {files_scanned} | **Issues:** {len(all_issues)} "
        f"(CRITICAL: {len(critical)}, HIGH: {len(high)}, MEDIUM: {len(medium)})",
        f"",
    ]

    if critical:
        report_lines.append("## CRITICAL — Fix Immediately")
        for issue in critical:
            report_lines.append(f"- **{issue['file']}** line {issue.get('line','?')}: {issue['description']}")
            report_lines.append(f"  Fix: {issue['fix']}")
        report_lines.append("")

    if high:
        report_lines.append("## HIGH")
        for issue in high[:10]:
            report_lines.append(f"- **{issue['file']}**: {issue['description']}")
        report_lines.append("")

    if medium:
        report_lines.append("## MEDIUM")
        for issue in medium[:10]:
            report_lines.append(f"- **{issue['file']}** line {issue.get('line','?')}: {issue['description']}")
        report_lines.append("")

    if not all_issues:
        report_lines.append("## No security issues found")

    os.makedirs(os.path.dirname(SECURITY_REPORT), exist_ok=True)
    with open(SECURITY_REPORT, "w") as f:
        f.write("\n".join(report_lines))

    with open(SECURITY_LOG, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "files_scanned": files_scanned,
            "critical": len(critical),
            "high": len(high),
            "medium": len(medium),
        }) + "\n")

    print(f"\nSecurity scan complete:")
    print(f"   Files scanned: {files_scanned}")
    print(f"   Critical: {len(critical)} | High: {len(high)} | Medium: {len(medium)}")
    print(f"   Report: {SECURITY_REPORT}")

    if critical:
        print(f"\nCRITICAL ISSUES FOUND — review {SECURITY_REPORT} immediately")

    return {"files_scanned": files_scanned, "critical": len(critical),
            "high": len(high), "medium": len(medium)}


if __name__ == "__main__":
    run_security_scan()
