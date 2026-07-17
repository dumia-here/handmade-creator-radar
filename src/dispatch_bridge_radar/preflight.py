from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .demo_replay import DEFAULT_GOLDEN, generate_demo
from .live_baseline import default_task
from .offline_workflow import STATE_DIRS
from .probes import ProbeRegistry
from .public_probes import BILIBILI_HOSTS, YOUTUBE_HOSTS, BilibiliPublicProbe, SafePublicHttpClient, YouTubePublicProbe


DEFAULT_NOTIFICATION_CONFIG = Path(".radar-demo-notification-config")


def check_preflight(*, bridge_root: Path, report_dir: Path, golden_path: Path, notification_config: Path, tests_passed: bool) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    checks["python_3_9_or_newer"] = sys.version_info >= (3, 9)
    try:
        import dispatch_bridge_radar  # noqa: F401
        checks["module_import"] = True
    except Exception:
        checks["module_import"] = False
    checks["state_directories"] = all((bridge_root / name).is_dir() for name in STATE_DIRS)
    checks["report_parent"] = report_dir.is_dir()
    try:
        registry = ProbeRegistry()
        registry.register(BilibiliPublicProbe(SafePublicHttpClient(BILIBILI_HOSTS)))
        registry.register(YouTubePublicProbe(SafePublicHttpClient(YOUTUBE_HOSTS)))
        task = default_task()
        checks["public_probes_registered"] = all(registry.get(request.platform) for request in task.probes)
    except Exception:
        checks["public_probes_registered"] = False
    try:
        demo = generate_demo(golden_path)
        checks["golden_replay"] = demo.get("source_kind") == "replay_golden"
    except Exception:
        checks["golden_replay"] = False
    checks["notification_config_exists"] = notification_config.exists()
    checks["tests_passed"] = tests_passed
    reasons = [name for name, passed in checks.items() if not passed]
    return {"status": "ready" if not reasons else "not_ready", "reason_codes": reasons, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline read-only Dispatch Bridge radar preflight")
    parser.add_argument("--bridge-root", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--notification-config", type=Path, default=DEFAULT_NOTIFICATION_CONFIG)
    parser.add_argument("--tests-passed", action="store_true")
    args = parser.parse_args()
    result = check_preflight(bridge_root=args.bridge_root, report_dir=args.report_dir, golden_path=args.golden, notification_config=args.notification_config, tests_passed=args.tests_passed)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
