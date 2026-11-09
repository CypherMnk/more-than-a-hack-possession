"""Create a private, unscored candidate bundle. Never upload or submit it automatically."""

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import zipfile

from versions.v2_tagged.possession import FRAME_COUNT, PLAY_BLOCKS


ROOT = Path(__file__).resolve().parent
SOURCES = {
    "v5_control": (
        "versions/v2_tagged/possession.py",
        "versions/v5_control/possession.py",
        "test_v5.py",
    ),
    "v6_control": (
        "versions/v2_tagged/possession.py",
        "versions/v5_control/possession.py",
        "versions/v6_control/possession.py",
        "test_v5.py",
        "test_v6.py",
    ),
}
COMMON_SOURCES = ("evaluation_tools/LICENSE", "evaluation_tools/SOURCE.json")
README = """# {version} possession candidate

This is a private convenience archive, not an automatically submitted entry or
an accuracy-based best-version selection. Read METHOD.md for limitations.

Python 3.10+; standard library only. Obtain the three Tactical input files
independently, then run from this extracted folder:

    python {test}
    python versions/{version}/possession.py --data-dir /path/to/Tactical --out regenerated.csv

possession.csv is the candidate result. manifest.json hashes the bundled files.
No supplied input assets, external reference labels or credentials are included.
Third-party licence and source provenance are retained under evaluation_tools.
Keep this archive private. Do not upload it or its CSV to AI services.
Extract/upload individual deliverables if the organisers require separate files.
"""


def validated_result(path, expected_rows):
    """Read once and validate the exact bytes that will be archived."""
    if not isinstance(expected_rows, int) or isinstance(expected_rows, bool) or expected_rows < 0:
        raise ValueError("Expected row count must be a nonnegative integer.")
    contents = Path(path).read_bytes()
    reader = csv.reader(io.StringIO(contents.decode("utf-8"), newline=""))
    if next(reader, None) != ["frame", "label"]:
        raise ValueError("CSV header must be frame,label.")
    count = 0
    for frame, row in enumerate(reader):
        if len(row) != 2 or row[0] != str(frame) or row[1] not in {"H", "A", "D", "X"}:
            raise ValueError("Invalid result CSV row.")
        if (
            expected_rows == FRAME_COUNT
            and not any(start <= frame <= end for start, end in PLAY_BLOCKS)
            and row[1] != "X"
        ):
            raise ValueError("Inactive frames must be X.")
        count += 1
    if count != expected_rows:
        raise ValueError("Result CSV row count is incorrect.")
    return contents


def build_bundle(
    result, output, expected_rows=FRAME_COUNT, *, version="v5_control",
    source_root=ROOT, verification=None,
):
    if version not in SOURCES:
        raise ValueError("Unknown candidate version.")
    result_contents = validated_result(result, expected_rows)
    if verification is not None:
        checked = verification.get("official_format_validator", {})
        if (
            checked.get("status") != "passed"
            or checked.get("expected_frames") != expected_rows
            or checked.get("result_sha256") != hashlib.sha256(result_contents).hexdigest()
        ):
            raise ValueError("Result does not match the pinned format check.")
    source_root = Path(source_root)
    # Explicit allowlist: never recurse through the workspace or package data.
    payload = {
        name: (source_root / name).read_bytes()
        for name in SOURCES[version] + COMMON_SOURCES
    }
    method = "MODEL_CARD.md" if version == "v5_control" else "MODEL_CARD_V6.md"
    payload["METHOD.md"] = (source_root / method).read_bytes()
    payload["README.md"] = README.format(version=version, test=SOURCES[version][-1]).encode("utf-8")
    payload["possession.csv"] = result_contents
    payload["manifest.json"] = (json.dumps({
        "candidate": version,
        "accuracy_status": "not_assessed",
        "not_a_submission": True,
        "verification": verification,
        "files_sha256": {
            name: hashlib.sha256(contents).hexdigest() for name, contents in payload.items()
        },
    }, indent=2) + "\n").encode("utf-8")
    output = Path(output)
    if output.suffix.casefold() != ".zip" or output.resolve() == Path(result).resolve():
        raise ValueError("Candidate output must be a separate ZIP file.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(temporary, "w") as archive:
            for name, contents in payload.items():
                # Fixed ZIP metadata makes the same payload reproducible.
                entry = zipfile.ZipInfo(name)
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, contents)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=SOURCES, default="v5_control")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    output = (args.out or ROOT / "packages" / f"{args.version[:2]}_candidate.zip").resolve()
    if not output.is_relative_to(ROOT / "packages"):
        parser.error("Keep private bundles inside this workspace's packages folder.")
    try:
        build_bundle(ROOT / "outputs" / f"{args.version}.csv", output, version=args.version)
    except (OSError, ValueError, zipfile.BadZipFile):
        parser.exit(1, "Candidate packaging failed locally; no match contents disclosed.\n")
    print(f"PASS: private {args.version} candidate bundle created. Unscored; not submitted.")


if __name__ == "__main__":
    main()
