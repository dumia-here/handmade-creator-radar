#!/usr/bin/env python3
"""Path-free, offline, screen-recording-friendly demo for the public package."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ASSET_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = ASSET_ROOT.parent


def _clear() -> None:
    print("\033[2J\033[H\033]0;Handmade Creator Radar Demo\007", end="", flush=True)


def _stage(title: str, lines: list[str], seconds: float) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    for line in lines:
        print(line)
    time.sleep(seconds)


def _run_json(arguments: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, *arguments],
        cwd=str(PACKAGE_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("offline demo command did not complete")
    return json.loads(result.stdout)


def main() -> int:
    try:
        _clear()
        _stage(
            "HANDMADE CREATOR RADAR V0.1",
            [
                "Cross-platform public-evidence research for independent handmade creators.",
                "Offline, reproducible, and safety-first.",
            ],
            7,
        )
        _stage(
            "1. CANDIDATE INPUT",
            [
                "A natural-language brief becomes a versioned research task.",
                "Requested probes: Bilibili and YouTube public sources.",
                "No login, private API, posting, or account automation.",
            ],
            7,
        )
        _stage(
            "2. STRICT TRACK GATE",
            [
                "ACCEPTED = making term + doll or toy object term.",
                "Generic craft content does not enter the accepted lane.",
                "Fact, inference, and missing data remain distinct.",
            ],
            8,
        )
        _stage(
            "3. EVIDENCE AND SCORING",
            [
                "A single viral post cannot decide a platform strategy.",
                "At most one main platform and one experiment are allowed.",
                "Weak or tied evidence stays insufficient instead of forcing a winner.",
            ],
            8,
        )
        golden = _run_json(["demo_v0_1.py"])
        summary = golden["golden"]
        decisions = summary["candidate_decisions"]
        tiers = summary["platform_tiers"]
        _stage(
            "4. OFFLINE GOLDEN REPLAY",
            [
                "Preflight: " + golden["preflight"]["status"],
                "Source: " + summary["source_kind"],
                "Candidates: accepted={accepted}, review={review}, rejected={rejected}".format(**decisions),
                "Bilibili: {bilibili} | YouTube: {youtube}".format(**tiers),
                "Replay is never presented as live evidence.",
            ],
            13,
        )
        workflow = _run_json(["demo_v0_1.py", "--workflow"])
        _stage(
            "5. EXPLICIT TERMINAL PATHS",
            [
                "Success: " + workflow["success_path"],
                "Human confirmation and resume: " + workflow["confirmation_resume_path"],
                "Failure: " + workflow["failure_path"],
                "All paths terminal: " + str(workflow["all_paths_terminal"]).lower(),
            ],
            13,
        )
        tests = _run_json(["demo_v0_1.py", "--tests"])
        _stage(
            "6. REPRODUCIBILITY AND PRIVACY",
            [
                "Offline tests: " + str(tests["test_count"]) + " passed.",
                "This recording prints no account, local-path, or notification data.",
                "V0.1 supports two public-source probes; long-term trends need another window.",
            ],
            10,
        )
        print("\nDEMO COMPLETE — Evidence before platform hype.")
        return 0
    except Exception:
        _clear()
        print("DEMO NEEDS ATTENTION — run the offline tests before recording.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
