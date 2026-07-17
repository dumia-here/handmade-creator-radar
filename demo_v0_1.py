#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


MODULE_ROOT = Path(__file__).resolve().parent
SRC = MODULE_ROOT / "src"
sys.path.insert(0, str(SRC))

from dispatch_bridge_radar.demo_replay import generate_demo
from dispatch_bridge_radar.offline_workflow import create_state_dirs
from dispatch_bridge_radar.preflight import check_preflight
from dispatch_bridge_radar.workflow_demo import run_workflow_demo


def golden_summary() -> dict[str, Any]:
    demo = generate_demo()
    decisions = {name: sum(item["decision"] == name for item in demo["candidates"]) for name in ("accepted", "review", "rejected")}
    return {
        "status": "ready",
        "source_kind": demo["source_kind"],
        "observation_window": demo["observation_window"],
        "candidate_decisions": decisions,
        "platform_tiers": {item["platform"]: item["tier"] for item in demo["platform_scores"]},
        "portable_patterns": demo["portable_patterns"],
        "gungun_topics": demo["gungun_topics"],
        "low_cost_script": demo["low_cost_script"],
        "confidence_note": demo["confidence_note"],
    }


def run_default(*, bridge_root: Path | None = None, report_dir: Path | None = None, notification_config: Path | None = None, tests_passed: bool = True) -> dict[str, Any]:
    if bridge_root is None and report_dir is None and notification_config is None:
        with tempfile.TemporaryDirectory(prefix="radar-v0-1-demo-") as directory:
            demo_root = Path(directory)
            state_root = demo_root / "state"
            create_state_dirs(state_root)
            demo_reports = demo_root / "reports"
            demo_reports.mkdir()
            demo_config = demo_root / "notification-config-placeholder"
            demo_config.touch()
            return run_default(
                bridge_root=state_root,
                report_dir=demo_reports,
                notification_config=demo_config,
                tests_passed=tests_passed,
            )
    if bridge_root is None or report_dir is None or notification_config is None:
        raise ValueError("provide all preflight paths together")
    preflight = check_preflight(
        bridge_root=bridge_root,
        report_dir=report_dir,
        golden_path=MODULE_ROOT / "samples/golden-replay.v0.1.json",
        notification_config=notification_config,
        tests_passed=tests_passed,
    )
    return {"mode": "golden", "preflight": preflight, "golden": golden_summary() if preflight["status"] == "ready" else None}


def run_tests(runner: Callable[..., Any] = subprocess.run) -> tuple[dict[str, Any], int]:
    result = runner(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=str(MODULE_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    match = re.search(r"Ran (\d+) tests?", combined)
    count = int(match.group(1)) if match else None
    if result.returncode == 0:
        return {"mode": "tests", "status": "passed", "test_count": count}, 0
    return {"mode": "tests", "status": "failed", "reason_code": "tests_failed", "test_count": count}, 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch Bridge Radar V0.1 offline demo")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--workflow", action="store_true", help="run three offline terminal paths")
    group.add_argument("--tests", action="store_true", help="run the full offline test suite")
    args = parser.parse_args()
    try:
        if args.tests:
            payload, code = run_tests()
        elif args.workflow:
            payload = {"mode": "workflow", **run_workflow_demo()}
            code = 0 if payload["all_paths_terminal"] else 2
        else:
            payload = run_default()
            code = 0 if payload["preflight"]["status"] == "ready" else 2
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return code
    except Exception:
        print(json.dumps({"status": "failed", "reason_code": "safe_demo_error"}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
