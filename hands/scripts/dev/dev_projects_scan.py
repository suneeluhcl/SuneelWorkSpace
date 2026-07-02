#!/usr/bin/env python3
"""
hands/scripts/dev/dev_projects_scan.py
Scans the MacBook for Java, Maven, Gradle, Spring Boot, and Node.js projects and
catalogs them in spine/system-context/developer_projects.json.

Run: dev-projects-scan [--roots DIR ...]
Safe: read-only scan, writes only the catalog JSON.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/SuneelWorkSpace"))
OUT = WORKSPACE / "spine/system-context/developer_projects.json"

DEFAULT_ROOTS = [
    WORKSPACE / "projects",
    Path.home() / "Documents",
    Path.home() / "Developer",
    Path.home() / "IdeaProjects",
    Path.home() / "workspace",
    Path.home() / "eclipse-workspace",
]
SKIP_DIRS = {".git", "node_modules", "target", "build", ".gradle", "__pycache__",
             ".venv", "venv", "Library", "go", ".npm", ".cache", ".agent-backups"}
MAX_DEPTH = 4


def classify(project_dir: Path) -> dict | None:
    """Return project metadata if project_dir is a recognized project root."""
    markers = {
        "maven": project_dir / "pom.xml",
        "gradle": project_dir / "build.gradle",
        "gradle-kts": project_dir / "build.gradle.kts",
        "node": project_dir / "package.json",
    }
    kinds = [k for k, p in markers.items() if p.exists()]
    if not kinds:
        return None

    info: dict = {
        "name": project_dir.name,
        "path": str(project_dir),
        "kinds": kinds,
        "git": (project_dir / ".git").exists(),
        "spring_boot": False,
        "has_wrapper": (project_dir / "mvnw").exists() or (project_dir / "gradlew").exists(),
        "docker_compose": any((project_dir / f).exists() for f in
                              ("docker-compose.yml", "docker-compose.yaml", "compose.yaml", "compose.yml")),
        "migrations": None,
    }

    try:
        if "maven" in kinds:
            pom = (project_dir / "pom.xml").read_text(errors="ignore")
            info["spring_boot"] = "spring-boot" in pom
        elif "gradle" in kinds or "gradle-kts" in kinds:
            for g in ("build.gradle", "build.gradle.kts"):
                f = project_dir / g
                if f.exists() and "org.springframework.boot" in f.read_text(errors="ignore"):
                    info["spring_boot"] = True
    except Exception:
        pass

    for mig in ("src/main/resources/db/migration", "src/main/resources/db/changelog"):
        if (project_dir / mig).is_dir():
            info["migrations"] = mig
            break
    return info


def scan(roots: list[Path]) -> list[dict]:
    found: dict[str, dict] = {}
    for root in roots:
        if not root.is_dir():
            continue
        root_depth = len(root.parts)
        for dirpath, dirnames, _ in os.walk(root):
            d = Path(dirpath)
            if len(d.parts) - root_depth > MAX_DEPTH:
                dirnames[:] = []
                continue
            dirnames[:] = [n for n in dirnames if n not in SKIP_DIRS and not n.startswith(".")]
            info = classify(d)
            if info:
                found[info["path"]] = info
                dirnames[:] = []  # don't descend into a recognized project
    return sorted(found.values(), key=lambda p: p["path"])


def main() -> int:
    roots = DEFAULT_ROOTS
    if "--roots" in sys.argv:
        idx = sys.argv.index("--roots")
        roots = [Path(p).expanduser() for p in sys.argv[idx + 1:]] or DEFAULT_ROOTS

    projects = scan(roots)
    catalog = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "scanned_roots": [str(r) for r in roots],
        "project_count": len(projects),
        "projects": projects,
        "rescan_command": "dev-projects-scan",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(catalog, indent=2) + "\n")
    print(f"[dev-projects-scan] {len(projects)} project(s) cataloged → {OUT}")
    for p in projects:
        tags = "+".join(p["kinds"]) + (" spring-boot" if p["spring_boot"] else "")
        print(f"  - {p['name']} ({tags}) {p['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
