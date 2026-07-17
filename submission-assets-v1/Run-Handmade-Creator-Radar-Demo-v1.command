#!/bin/zsh
set -euo pipefail
ASSET_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ASSET_DIR"
exec /usr/bin/env python3 run_safe_demo_v1.py
