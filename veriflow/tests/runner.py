"""
VeriFlow V1 — Standalone test runner.
Run with: python tests/runner.py
No pytest required.
"""

import sys
import traceback
from pathlib import Path

# Ensure veriflow package is importable from the repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from veriflow.tests.test_veriflow import ALL_TESTS


def run_all() -> None:
    passed = 0
    failed = 0
    errors = []

    print("=" * 60)
    print("VeriFlow V1 — Test Suite")
    print("=" * 60)

    for name, fn in ALL_TESTS:
        try:
            fn()
            print(f"  ✓  {name}")
            passed += 1
        except AssertionError as e:
            msg = str(e) or "(assertion failed)"
            print(f"  ✗  {name}  →  {msg}")
            errors.append((name, traceback.format_exc()))
            failed += 1
        except Exception as e:
            print(f"  ✗  {name}  →  EXCEPTION: {e}")
            errors.append((name, traceback.format_exc()))
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed  ({passed + failed} total)")
    print("=" * 60)

    if errors:
        print()
        for name, tb in errors:
            print(f"--- {name} ---")
            print(tb)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_all()
