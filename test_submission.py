"""Synthetic release checks; never read Tactical or saved match results."""

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

from prepare_candidate import COMMON_SOURCES, FRAME_COUNT, ROOT, SOURCES, build_bundle
from prepare_submission import create_submission, official_format_check


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name in SOURCES["v6_control"] + COMMON_SOURCES + (
            "MODEL_CARD_V6.md", "evaluation_tools/possession_metrics.py",
        ):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())
        small = root / "invented.csv"
        small.write_text("frame,label\n0,H\n1,A\n2,D\n3,X\n", encoding="utf-8")
        checked = official_format_check(small, 4, source_root=root)
        assert checked["status"] == "passed"
        assert checked["result_sha256"] == hashlib.sha256(small.read_bytes()).hexdigest()
        # Even a valid replacement must not inherit another file's format check.
        small.write_text("frame,label\n0,A\n1,H\n2,D\n3,X\n", encoding="utf-8")
        try:
            build_bundle(
                small, root / "stale-check.zip", 4, source_root=root,
                verification={"official_format_validator": checked},
            )
            raise AssertionError("A stale validator check was reused.")
        except ValueError:
            assert not (root / "stale-check.zip").exists()
        small.write_text("frame,label\n0,H\n1,A\n1,D\n3,X\n", encoding="utf-8")
        try:
            official_format_check(small, 4, source_root=root)
            raise AssertionError("Invalid frame sequence passed the official validator.")
        except ValueError:
            pass

        # Entirely invented full-length timeline; no possession reference table.
        data = root / "synthetic_inputs"
        data.mkdir()
        tracking = data / "BAR-ATH_tactical_atd.txt"
        with tracking.open("w", encoding="utf-8") as stream:
            for frame in range(1, FRAME_COUNT + 1):
                stream.write(f"{frame}:NaN,NaN,NaN;NaN,NaN,NaN:NaN,NaN,NaN\n")
        (data / "BAR-ATH_tactical_atd.xml").write_text(
            '<root><Team id="home"/><Team id="away"/>'
            '<Player teamId="home"/><Player teamId="away"/></root>', encoding="utf-8",
        )
        (data / "BAR-ATH_tactical_smart_tagging.xml").write_text("<root/>", encoding="utf-8")
        output = create_submission(data, source_root=root)
        saved = output.read_bytes()
        with zipfile.ZipFile(output) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            checks = manifest["verification"]
            assert checks["fresh_inference_from_bundled_source"] and checks["frozen_defaults"]
            assert checks["official_format_validator"]["status"] == "passed"
            assert checks["official_format_validator"]["ground_truth_used"] is False
            assert checks["official_format_validator"]["result_sha256"] == manifest["files_sha256"]["possession.csv"]
            for name, digest in manifest["files_sha256"].items():
                assert hashlib.sha256(archive.read(name)).hexdigest() == digest
        create_submission(data, source_root=root)
        assert output.read_bytes() == saved
        # Failed source integrity and inference checks must preserve the last bundle.
        metric = root / "evaluation_tools/possession_metrics.py"
        original_metric = metric.read_bytes()
        metric.write_bytes(original_metric + b"\n# invented change\n")
        try:
            create_submission(data, source_root=root)
            raise AssertionError("A modified validator was accepted.")
        except ValueError:
            assert output.read_bytes() == saved
        metric.write_bytes(original_metric)
        tracking.write_text("malformed synthetic record\n", encoding="utf-8")
        try:
            create_submission(data, source_root=root)
            raise AssertionError("Malformed tracking created a release.")
        except subprocess.CalledProcessError:
            assert output.read_bytes() == saved
        try:
            create_submission(root, source_root=root)
            raise AssertionError("Input/output directory overlap accepted.")
        except ValueError:
            assert output.read_bytes() == saved
    print("PASS: synthetic full release, pinned format validation, provenance, reproducibility, and failed-run preservation.")


if __name__ == "__main__":
    main()
