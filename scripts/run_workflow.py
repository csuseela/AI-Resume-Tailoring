#!/usr/bin/env python3
"""Run the workflow manually from the command line."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.logging import setup_logging

setup_logging()

from app.main import build_container

container = build_container()
wf = container["workflow_service"]
result = wf.run_daily_workflow()
print(json.dumps(result, indent=2, default=str))
