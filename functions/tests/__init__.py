"""Ensure the `functions` directory is importable when running unit tests."""

from __future__ import annotations

import pathlib
import sys

FUNCTIONS_ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
if FUNCTIONS_ROOT not in sys.path:
    sys.path.insert(0, FUNCTIONS_ROOT)
