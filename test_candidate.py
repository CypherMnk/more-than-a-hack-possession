"""Candidate packaging checks with a tiny invented CSV; no real match outputs."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
import zipfile

from prepare_candidate import COMMON_SOURCES, SOURCES, build_bundle, validated_result
from versions.v2_tagged.possession import write_csv


def main():
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        result, output = directory / "invented.csv", directory / "candidate.zip"
        write_csv(result, list("HADX"), 4)
        for version, sources in SOURCES.items():
            build_bundle(result, output, 4, version=version)
            saved = output.read_bytes()
            with zipfile.ZipFile(output) as archive:
                assert set(archive.namelist()) == set(sources) | set(COMMON_SOURCES) | {
                    "METHOD.md", "README.md", "possession.csv", "manifest.json",
                }
                assert archive.read("possession.csv") == result.read_bytes()
                manifest = json.loads(archive.read("manifest.json"))
                assert manifest["candidate"] == version
                assert manifest["accuracy_status"] == "not_assessed" and manifest["not_a_submission"]
                assert set(manifest["files_sha256"]) == set(archive.namelist()) - {"manifest.json"}
                for name, digest in manifest["files_sha256"].items():
                    assert hashlib.sha256(archive.read(name)).hexdigest() == digest
                extracted = directory / version
                archive.extractall(extracted)  # Own archive; exact allowlist checked above.
            subprocess.run(
                [sys.executable, str(extracted / sources[-1])], cwd=extracted,
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            build_bundle(result, output, 4, version=version)
            assert output.read_bytes() == saved
        # Preserve the old default: existing V5 packaging callers keep V5.
        build_bundle(result, output, 4)
        with zipfile.ZipFile(output) as archive:
            assert json.loads(archive.read("manifest.json"))["candidate"] == "v5_control"
        saved = output.read_bytes()
        # Swapping the original after validation must not alter the archived bytes.
        original = result.read_bytes()
        def swap_after_read(path, rows):
            contents = validated_result(path, rows)
            Path(path).write_text("frame,label\n0,Z\n", encoding="utf-8")
            return contents
        with patch("prepare_candidate.validated_result", side_effect=swap_after_read):
            build_bundle(result, output, 4)
        with zipfile.ZipFile(output) as archive:
            assert archive.read("possession.csv") == original
        result.write_bytes(original)
        saved = output.read_bytes()
        result.write_text("frame,label\n0,H\n", encoding="utf-8")
        try:
            build_bundle(result, output, 4)
            raise AssertionError("An invalid result was packaged.")
        except ValueError:
            assert output.read_bytes() == saved
        for contents in (
            b"frame,label\n0,H\n1,A\n1,D\n3,X\n",
            b"frame,label\n0,H\n1,A\n2,D\n3,\n",
            b"frame,label\n0,H\n1,A\n2,D\n3,Z\n",
            b"frame,label\n0,H\n1,A\n2,D\n3,X\n4,H\n",
        ):
            result.write_bytes(contents)
            try:
                build_bundle(result, output, 4)
                raise AssertionError("Malformed output was packaged.")
            except ValueError:
                assert output.read_bytes() == saved
        try:
            build_bundle(result, output, 4, version="unknown")
            raise AssertionError("An unknown candidate version was accepted.")
        except ValueError:
            assert output.read_bytes() == saved
    print("PASS: synthetic candidate allowlist, extracted-code tests, result validation, hashes, atomic preservation, and reproducibility.")


if __name__ == "__main__":
    main()
