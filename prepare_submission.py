"""Generate and validate a private V6 delivery bundle; never submit automatically."""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType

from prepare_candidate import COMMON_SOURCES, FRAME_COUNT, ROOT, SOURCES, build_bundle


def official_format_check(result, expected_rows=FRAME_COUNT, *, source_root=ROOT):
    """Pinned format validation only. Never load or compare possession references."""
    source_root = Path(source_root)
    provenance = json.loads((source_root / "evaluation_tools/SOURCE.json").read_text(encoding="utf-8"))
    source = source_root / "evaluation_tools/possession_metrics.py"
    source_contents = source.read_bytes()
    if hashlib.sha256(source_contents).hexdigest() != provenance["sha256"]:
        raise ValueError("Pinned validator source changed.")
    # Execute only the exact verified local source bytes, not a cached module.
    # Its numpy/pandas imports require the separate evaluation environment.
    metrics = ModuleType("submission_format_metrics")
    exec(compile(source_contents, str(source), "exec"), metrics.__dict__)
    contents = Path(result).read_bytes()
    if metrics.validate_submission(metrics.read_label_csv(io.BytesIO(contents)), expected_rows) is not None:
        raise ValueError("Pinned official format validation failed; inspect locally.")
    return {
        "status": "passed", "commit": provenance["commit"], "sha256": provenance["sha256"],
        "ground_truth_used": False, "accuracy_assessed": False,
        "result_sha256": hashlib.sha256(contents).hexdigest(), "expected_frames": expected_rows,
    }


def create_submission(data_dir, *, source_root=ROOT):
    """Run the exact source snapshot that is packaged, using unchanged defaults."""
    source_root = Path(source_root).resolve()
    data_dir = Path(data_dir).resolve()
    packages = source_root / "packages"
    if (
        not packages.resolve().is_relative_to(source_root)
        or packages.resolve().is_relative_to(data_dir)
        or any(part.casefold() in {".git", ".venv", "venv", "node_modules"} for part in packages.resolve().parts)
    ):
        raise ValueError("Unsafe private package directory.")
    if not all((data_dir / name).is_file() for name in (
        "BAR-ATH_tactical_atd.txt", "BAR-ATH_tactical_atd.xml",
        "BAR-ATH_tactical_smart_tagging.xml",
    )):
        raise ValueError("Missing authorised Tactical input files.")
    packages.mkdir(exist_ok=True)
    output = packages / "v6_submission_candidate.zip"
    with tempfile.TemporaryDirectory(prefix=".submission-", dir=packages) as directory:
        stage = Path(directory).resolve()
        if not stage.is_relative_to(packages.resolve()):
            raise ValueError("Unsafe temporary directory.")
        for name in SOURCES["v6_control"] + COMMON_SOURCES + ("MODEL_CARD_V6.md",):
            destination = stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((source_root / name).read_bytes())
        # Tests run against the same snapshot, without any match inputs.
        subprocess.run(
            [sys.executable, str(stage / "test_v6.py")], cwd=stage,
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        result = stage / "possession.csv"
        subprocess.run([
            sys.executable, str(stage / "versions/v6_control/possession.py"),
            "--data-dir", str(data_dir), "--out", str(result),
        ], cwd=stage, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        validation = official_format_check(result, source_root=source_root)
        temporary_bundle = stage / "delivery.zip"
        build_bundle(
            result, temporary_bundle, version="v6_control", source_root=stage,
            verification={
                "fresh_inference_from_bundled_source": True,
                "frozen_defaults": True, "synthetic_tests": "passed",
                "official_format_validator": validation,
            },
        )
        os.replace(temporary_bundle, output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "Tactical")
    args = parser.parse_args()
    try:
        create_submission(args.data_dir)
    except (OSError, ValueError, ImportError, subprocess.CalledProcessError):
        parser.exit(
            1, "Submission preparation failed locally. Check inputs and use the evaluation "
            "environment for the pinned validator; no data or predictions disclosed.\n",
        )
    print("PASS: fresh V6 delivery bundle and pinned official CSV-format check. Unscored; not submitted.")


if __name__ == "__main__":
    main()
