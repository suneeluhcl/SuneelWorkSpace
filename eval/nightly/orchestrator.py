"""
Adwi Nightly Eval Orchestrator
Runs at 3:00 AM via LaunchAgent (after nightly.py at 2:00 AM).
Coordinates all eval layers and publishes a morning report.

Safety contract:
- Reads/evaluates only — no production-code patches
- Writes only to logs/nightly/ and eval/scenarios/generated/
- Does not touch secrets/, config/.env, or BLOCKED_PATHS
- Lock file prevents concurrent runs
- Aborts on battery power or high load
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

LOG_DIR = REPO_ROOT / "logs" / "nightly"
LOCK_FILE = REPO_ROOT / "logs" / "nightly-eval.lock"
CONFIG_PATH = REPO_ROOT / "config" / "eval" / "nightly.yaml"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("nightly-eval")


# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

def _check_battery() -> bool:
    """Return True if on AC power (not battery)."""
    try:
        import subprocess
        out = subprocess.check_output(["pmset", "-g", "ps"], text=True)
        return "AC Power" in out
    except Exception:
        return True  # non-mac: assume OK


def _check_load() -> bool:
    """Return True if system load is acceptable."""
    import os
    try:
        load = os.getloadavg()[0]
        cpu_count = os.cpu_count() or 4
        return (load / cpu_count) < 0.75
    except Exception:
        return True


def _check_ollama(base_url: str) -> bool:
    import urllib.request
    try:
        urllib.request.urlopen(f"{base_url}/api/tags", timeout=5)
        return True
    except Exception:
        return False


def preflight(config: dict) -> list[str]:
    issues = []
    if not _check_battery():
        issues.append("Battery power — aborting to preserve battery")
    if not _check_load():
        issues.append("System load too high (>75% per core)")
    if LOCK_FILE.exists():
        issues.append(f"Lock file exists: {LOCK_FILE} — another session may be running")
    if not _check_ollama(config.get("ollama_base", "http://localhost:11434")):
        issues.append("Ollama not reachable — cannot run NLU eval")
    return issues


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_config() -> dict:
    import yaml  # pyyaml required
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


# ---------------------------------------------------------------------------
# Phase runners (each returns a result dict)
# ---------------------------------------------------------------------------

async def phase_generate_scenarios(config: dict, session_dir: Path) -> dict:
    log.info("Phase 1 — scenario generation")
    from eval.nightly.scenario_generator import ScenarioGenerator
    gen = ScenarioGenerator(config)
    scenarios = await gen.generate(session_dir)
    out = session_dir / "scenarios.jsonl"
    with open(out, "w") as f:
        for s in scenarios:
            f.write(json.dumps(s) + "\n")
    log.info(f"  Generated {len(scenarios)} scenarios → {out}")
    return {"count": len(scenarios), "path": str(out)}


async def phase_run_nlu_eval(config: dict, session_dir: Path, scenarios_path: Path) -> dict:
    """Run scenarios through the standalone NLU harness (subprocess)."""
    log.info("Phase 2 — NLU eval harness")
    import subprocess

    harness = REPO_ROOT / "logs" / "simeval" / "run_large_eval.py"
    if not harness.exists():
        log.warning("  run_large_eval.py not found — skipping")
        return {"skipped": True}

    result_file = session_dir / "nlu_results.jsonl"
    cmd = [
        sys.executable, str(harness),
        "--scenarios", str(scenarios_path),
        "--output", str(result_file),
        "--workers", str(config.get("nlu_workers", 5)),
    ]
    t0 = time.time()
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    elapsed = time.time() - t0

    log_file = session_dir / "nlu_eval.log"
    log_file.write_bytes(stdout)

    passed = failed = 0
    if result_file.exists():
        with open(result_file) as f:
            for line in f:
                row = json.loads(line)
                if row.get("result") == "pass":
                    passed += 1
                else:
                    failed += 1

    rate = passed / (passed + failed) if (passed + failed) > 0 else 0.0
    log.info(f"  NLU eval: {passed} pass / {failed} fail ({rate:.1%}) in {elapsed:.0f}s")
    return {"passed": passed, "failed": failed, "rate": rate, "elapsed": elapsed, "path": str(result_file)}


async def phase_deepeval_score(config: dict, session_dir: Path, nlu_results: Path) -> dict:
    """Run DeepEval semantic quality metrics on a sample of results."""
    log.info("Phase 3 — DeepEval semantic scoring")
    try:
        from eval.nightly.grader import DeepEvalGrader
        grader = DeepEvalGrader(config)
        results = await grader.score_file(nlu_results, session_dir)
        log.info(f"  DeepEval: {results.get('scored', 0)} samples scored")
        return results
    except ImportError as e:
        log.warning(f"  DeepEval not available: {e}")
        return {"skipped": True, "reason": str(e)}
    except Exception as e:
        log.error(f"  DeepEval error: {e}")
        return {"error": str(e)}


async def phase_giskard_scan(config: dict, session_dir: Path) -> dict:
    """Run Giskard adversarial vulnerability scan."""
    log.info("Phase 4 — Giskard adversarial scan")
    try:
        from eval.giskard.adversarial_scan import run_giskard_scan
        results = await asyncio.get_event_loop().run_in_executor(
            None, run_giskard_scan, config, session_dir
        )
        log.info(f"  Giskard: {results.get('issues_found', 0)} issues found")
        return results
    except ImportError as e:
        log.warning(f"  Giskard not available: {e}")
        return {"skipped": True, "reason": str(e)}
    except Exception as e:
        log.error(f"  Giskard error: {e}")
        return {"error": str(e)}


async def phase_promptfoo(config: dict, session_dir: Path) -> dict:
    """Run promptfoo matrix eval (requires node/npx)."""
    log.info("Phase 5 — promptfoo matrix eval")
    import shutil, subprocess

    if not shutil.which("npx"):
        log.warning("  npx not found — skipping promptfoo")
        return {"skipped": True, "reason": "npx not found"}

    pf_config = REPO_ROOT / "eval" / "promptfoo" / "promptfooconfig.yaml"
    if not pf_config.exists():
        return {"skipped": True, "reason": "promptfooconfig.yaml not found"}

    out_dir = session_dir / "promptfoo"
    out_dir.mkdir(exist_ok=True)
    cmd = [
        "npx", "--yes", "promptfoo@latest", "eval",
        "--config", str(pf_config),
        "--output", str(out_dir / "results.json"),
        "--no-progress-bar",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(REPO_ROOT / "eval" / "promptfoo"),
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=600)
        (out_dir / "promptfoo.log").write_bytes(stdout)
        log.info(f"  promptfoo completed (exit {proc.returncode})")
        return {"exit_code": proc.returncode, "output": str(out_dir)}
    except asyncio.TimeoutError:
        proc.kill()
        return {"error": "timeout after 10 min"}


async def phase_playwright(config: dict, session_dir: Path) -> dict:
    """Run Playwright browser smoke tests."""
    log.info("Phase 6 — Playwright UI smoke tests")
    import shutil

    if not shutil.which("npx"):
        return {"skipped": True, "reason": "npx not found"}

    pw_dir = REPO_ROOT / "eval" / "playwright"
    out = session_dir / "playwright"
    out.mkdir(exist_ok=True)
    cmd = [
        "npx", "--yes", "playwright@latest", "test",
        "--reporter=json",
        f"--output={out}",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(pw_dir),
            env={**os.environ, "PLAYWRIGHT_JSON_OUTPUT_NAME": str(out / "results.json")},
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=300)
        (out / "playwright.log").write_bytes(stdout)
        log.info(f"  Playwright completed (exit {proc.returncode})")
        return {"exit_code": proc.returncode, "output": str(out)}
    except asyncio.TimeoutError:
        proc.kill()
        return {"error": "timeout after 5 min"}
    except Exception as e:
        return {"error": str(e)}


async def phase_k6(config: dict, session_dir: Path) -> dict:
    """Run k6 API load test."""
    log.info("Phase 7 — k6 performance test")
    import shutil

    if not shutil.which("k6"):
        return {"skipped": True, "reason": "k6 not found"}

    script = REPO_ROOT / "eval" / "k6" / "api_load.js"
    out = session_dir / "k6_results.json"
    cmd = ["k6", "run", "--out", f"json={out}", str(script)]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=300)
        (session_dir / "k6.log").write_bytes(stdout)
        log.info(f"  k6 completed (exit {proc.returncode})")
        return {"exit_code": proc.returncode, "output": str(out)}
    except asyncio.TimeoutError:
        proc.kill()
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}


async def phase_cluster_failures(config: dict, session_dir: Path, nlu_results_path: str) -> dict:
    """Cluster failure cases by embedding similarity."""
    log.info("Phase 8 — failure clustering")
    try:
        from eval.nightly.failure_cluster import cluster_failures
        result = await asyncio.get_event_loop().run_in_executor(
            None, cluster_failures, config, nlu_results_path, str(session_dir)
        )
        log.info(f"  Clustered into {result.get('num_clusters', 0)} groups")
        return result
    except Exception as e:
        log.error(f"  Clustering error: {e}")
        return {"error": str(e)}


async def phase_regression(config: dict, session_dir: Path, nlu_result: dict) -> dict:
    """Compare tonight's results to previous nights."""
    log.info("Phase 9 — regression comparison")
    try:
        from eval.nightly.regression_compare import compare_to_history
        result = compare_to_history(LOG_DIR, nlu_result, session_dir)
        log.info(f"  Regression: delta={result.get('delta', 0):+.1%}")
        return result
    except Exception as e:
        log.error(f"  Regression error: {e}")
        return {"error": str(e)}


async def phase_phoenix(config: dict, session_dir: Path, nlu_results_path: str) -> dict:
    """Push traces to Phoenix dataset."""
    log.info("Phase 10 — Phoenix trace upload")
    try:
        from eval.nightly.phoenix_tracer import push_to_phoenix
        result = push_to_phoenix(config, nlu_results_path, session_dir)
        log.info(f"  Phoenix: {result.get('pushed', 0)} traces pushed")
        return result
    except Exception as e:
        log.warning(f"  Phoenix upload skipped: {e}")
        return {"skipped": True, "reason": str(e)}


async def phase_report(config: dict, session_dir: Path, all_results: dict) -> dict:
    """Generate markdown report and repair backlog."""
    log.info("Phase 11 — report publishing")
    from eval.nightly.report_publisher import publish_report
    return publish_report(session_dir, all_results, LOG_DIR)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def main():
    config = load_config()
    session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    session_dir = LOG_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"Adwi Nightly Eval — session {session_id}")
    log.info(f"Output: {session_dir}")

    # Pre-flight
    issues = preflight(config)
    if issues:
        for issue in issues:
            log.error(f"  ABORT: {issue}")
        sys.exit(1)

    # Acquire lock
    LOCK_FILE.write_text(str(os.getpid()))
    t_start = time.time()
    all_results: dict = {"session_id": session_id, "started_at": datetime.utcnow().isoformat()}

    try:
        # Phase 1: scenario generation
        gen_result = await phase_generate_scenarios(config, session_dir)
        all_results["scenario_generation"] = gen_result
        scenarios_path = Path(gen_result["path"])

        # Phase 2: NLU eval
        nlu_result = await phase_run_nlu_eval(config, session_dir, scenarios_path)
        all_results["nlu_eval"] = nlu_result
        nlu_results_path = nlu_result.get("path", "")

        # Phases 3-7: scoring, adversarial, UI, perf (run in parallel where safe)
        deepeval_task = asyncio.create_task(
            phase_deepeval_score(config, session_dir, Path(nlu_results_path) if nlu_results_path else Path("/dev/null"))
        )
        giskard_task = asyncio.create_task(phase_giskard_scan(config, session_dir))
        promptfoo_task = asyncio.create_task(phase_promptfoo(config, session_dir))
        playwright_task = asyncio.create_task(phase_playwright(config, session_dir))
        k6_task = asyncio.create_task(phase_k6(config, session_dir))

        results = await asyncio.gather(
            deepeval_task, giskard_task, promptfoo_task, playwright_task, k6_task,
            return_exceptions=True,
        )
        all_results["deepeval"] = results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])}
        all_results["giskard"] = results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])}
        all_results["promptfoo"] = results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])}
        all_results["playwright"] = results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])}
        all_results["k6"] = results[4] if not isinstance(results[4], Exception) else {"error": str(results[4])}

        # Phases 8-11: analysis + reporting (sequential, depend on prior results)
        all_results["failure_clusters"] = await phase_cluster_failures(config, session_dir, nlu_results_path)
        all_results["regression"] = await phase_regression(config, session_dir, nlu_result)
        all_results["phoenix"] = await phase_phoenix(config, session_dir, nlu_results_path)

        all_results["elapsed_total"] = round(time.time() - t_start, 1)
        all_results["completed_at"] = datetime.utcnow().isoformat()

        # Phase 11: report
        report_result = await phase_report(config, session_dir, all_results)
        all_results["report"] = report_result

        # Write master session JSON
        (session_dir / "session.json").write_text(json.dumps(all_results, indent=2))

        # Update latest symlink
        latest_link = LOG_DIR / "latest"
        if latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(session_dir.name)

        rate = all_results.get("nlu_eval", {}).get("rate", 0)
        log.info(f"Session complete — NLU {rate:.1%} — {all_results['elapsed_total']}s")
        log.info(f"Report: {session_dir}/00_morning_brief.md")

    except Exception as e:
        log.exception(f"Orchestrator fatal error: {e}")
        (session_dir / "FATAL_ERROR.txt").write_text(str(e))
        raise
    finally:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()


if __name__ == "__main__":
    asyncio.run(main())
