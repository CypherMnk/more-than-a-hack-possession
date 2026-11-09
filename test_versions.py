"""Run synthetic checks against the saved algorithm versions."""

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    for version in ("v1_tracking", "v2_tagged"):
        load("possession", ROOT / "versions" / version / "possession.py")
        tests = load("version_tests", ROOT / "test_possession.py")
        tests.main()
        print(f"PASS: {version} synthetic checks.")
    for version in (3, 4, 5, 6):
        tests = load(f"v{version}_tests", ROOT / f"test_v{version}.py")
        tests.main()
    load("candidate_tests", ROOT / "test_candidate.py").main()
