"""Convert a licensed IDSSE match into separate inference inputs and reference labels."""

import argparse
from array import array
import csv
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from possession import write_csv


ROOT = Path(__file__).resolve().parent
MATCH = "J03WOH"
POSITIONS = f"DFL_04_03_positions_raw_observed_DFL-COM-000002_DFL-MAT-{MATCH}.xml"
METADATA = f"DFL_02_01_matchinformation_DFL-COM-000002_DFL-MAT-{MATCH}.xml"
EXPECTED_HASHES = {
    POSITIONS: "ec4dcf30200aad694dea263d5289485fcd0ca42badddaeb7c81f5cd5a4229d4f",
    METADATA: "f23b3ee13b988b1ff9a0bce438c416dac47e71355bbc7ee1dab21aaf3e33c18c",
}
DATASET = {
    "dataset": "IDSSE",
    "match_id": MATCH,
    "license": "CC-BY-4.0",
    "credit": "Deutsche Fußball Liga (DFL); Bassek, Rein, Weber and Memmert (2025)",
    "paper": "https://doi.org/10.1038/s41597-025-04505-y",
    "original": "https://doi.org/10.6084/m9.figshare.28196177",
    "mirror": "https://huggingface.co/datasets/pysport/idsse-data",
    "revision": "a715a38dfbaf5f58e431727c2b78d174101a703c",
}
HALVES = ("firstHalf", "secondHalf")


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reference_label(frame):
    """Provider reference attributes are exported ONLY to the ground-truth file."""
    status = frame.get("BallStatus")
    if status == "0":
        return "D"
    if status == "1":
        return {"1": "H", "2": "A"}.get(frame.get("BallPossession"), "X")
    return "X"


def metadata_info(path):
    root = ET.parse(path).getroot()
    general = root.find(".//MatchInformation/General")
    environment = root.find(".//MatchInformation/Environment")
    if general is None or environment is None:
        raise ValueError("Missing match metadata.")
    team_ids = [general.get("HomeTeamId"), general.get("AwayTeamId") or general.get("GuestTeamId")]
    if None in team_ids or len(set(team_ids)) != 2:
        raise ValueError("Expected distinct home and away teams.")
    pitch = tuple(float(environment.get(key, "")) for key in ("PitchX", "PitchY"))
    if any(not math.isfinite(value) or value <= 0 for value in pitch):
        raise ValueError("Invalid pitch dimensions.")
    people = {}
    for team in root.findall(".//Teams/Team"):
        team_id = team.get("TeamId")
        if team_id in team_ids:
            for player in team.findall("Players/Player"):
                person = player.get("PersonId")
                if person is None or person in people:
                    raise ValueError("Invalid or duplicate player metadata.")
                people[person] = team_id
    if not people or not all(team in people.values() for team in team_ids):
        raise ValueError("Missing player metadata for a team.")
    return team_ids, people, pitch


def load_objects(path, people):
    """Read object-major Sportec XML using compact arrays rather than frame dictionaries."""
    objects = {}
    current = frameset = None
    for event, element in ET.iterparse(path, events=("start", "end")):
        if event == "start" and element.tag == "FrameSet":
            frameset = element
            half = element.get("GameSection")
            person = "BALL" if element.get("TeamId", "").upper() == "BALL" else element.get("PersonId")
            current = None
            if half in HALVES and (person == "BALL" or person in people):
                key = (half, person)
                if key in objects:
                    raise ValueError("Duplicate object/half FrameSet; inspect external export.")
                current = (array("q"), array("d"), array("d"), bytearray())
                objects[key] = current
        elif event == "end" and element.tag == "Frame":
            if current is not None:
                ids, xs, ys, labels = current
                frame_id = int(element.get("N", ""))
                if ids and frame_id <= ids[-1]:
                    raise ValueError("Object frames must be strictly increasing.")
                x, y = (float(element.get(axis, "NaN")) for axis in ("X", "Y"))
                if math.isinf(x) or math.isinf(y):
                    raise ValueError("Infinite position in external tracking.")
                ids.append(frame_id)
                xs.append(x)
                ys.append(y)
                if person == "BALL":
                    labels.append(ord(reference_label(element)))
            element.clear()
            if frameset is not None:
                frameset.remove(element)
        elif event == "end" and element.tag == "FrameSet":
            element.clear()
            current = frameset = None
    return objects


def normalized_group(x, y, pitch):
    # Sportec/DFL coordinates are metres with the origin at the pitch centre.
    # Speed is unused by V1/V2, so it remains NaN rather than being fabricated.
    return f"{x / pitch[0] + 0.5:.12g},{y / pitch[1] + 0.5:.12g},NaN"


def convert(metadata, positions, output, provenance):
    """Transpose object observations; never expose reference status to inference."""
    output = Path(output)
    if output.exists():
        raise ValueError("Prepared directory exists; use a fresh directory to preserve results.")
    team_ids, people, pitch = metadata_info(metadata)
    objects = load_objects(positions, people)
    periods = []
    for half in HALVES:
        ball = objects.get((half, "BALL"))
        if ball is None or not ball[0]:
            raise ValueError("Both halves require ball records.")
        ids = ball[0]
        if ids[-1] - ids[0] + 1 != len(ids):
            raise ValueError("Ball timeline is not contiguous; do not invent alignment.")
        periods.append((half, ball))
    output.mkdir(parents=True)
    metadata_root = ET.Element("root")
    for team in team_ids:
        ET.SubElement(metadata_root, "Team", id=team)
    for person, team in people.items():
        ET.SubElement(metadata_root, "Player", id=person, teamId=team)
    ET.ElementTree(metadata_root).write(output / "metadata.xml", encoding="utf-8")

    reference = []
    play_blocks = []
    with (output / "tracking.txt").open("w", encoding="utf-8", newline="\n") as handle:
        with (output / "frame_map.csv").open("w", encoding="utf-8", newline="") as map_handle:
            frame_map = csv.writer(map_handle)
            frame_map.writerow(("frame", "half", "source_frame"))
            for half_index, (half, ball) in enumerate(periods):
                if half_index:
                    # one explicit unknown separator keeps the
                    # two source halves distinct without fabricating a halftime duration.
                    slots = ";".join(["NaN,NaN,NaN"] * len(people))
                    frame_map.writerow((len(reference), "separator", ""))
                    handle.write(f"{len(reference) + 1}:{slots}:NaN,NaN,NaN\n")
                    reference.append("X")
                start = len(reference)
                tracks = [objects.get((half, person)) for person in people]
                indexes = [0] * len(tracks)
                for i, frame_id in enumerate(ball[0]):
                    groups = []
                    for slot, track in enumerate(tracks):
                        group = "NaN,NaN,NaN"
                        if track is not None:
                            ids, xs, ys, _ = track
                            index = indexes[slot]
                            while index < len(ids) and ids[index] < frame_id:
                                index += 1
                            if index < len(ids) and ids[index] == frame_id:
                                group = normalized_group(xs[index], ys[index], pitch)
                            indexes[slot] = index
                        groups.append(group)
                    ball_group = normalized_group(ball[1][i], ball[2][i], pitch)
                    frame_map.writerow((len(reference), half, frame_id))
                    handle.write(f"{len(reference) + 1}:{';'.join(groups)}:{ball_group}\n")
                    reference.append(chr(ball[3][i]))
                play_blocks.append((start, len(reference) - 1))
    write_csv(output / "ground_truth.csv", reference, len(reference))
    files = ("metadata.xml", "tracking.txt", "ground_truth.csv", "frame_map.csv")
    manifest = {
        **provenance, "n_frames": len(reference), "fps": 25,
        "pitch": pitch, "play_blocks": play_blocks,
        "reference": "D if BallStatus=0; H/A if live with BallPossession=1/2; otherwise X",
        "changes": "Centred metres to normalized coordinates; speed omitted; half separator inserted.",
        "compatible_automatic_tags": False,
        "prepared_sha256": {name: file_hash(output / name) for name in files},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "external_data" / MATCH)
    args = parser.parse_args()
    raw = args.raw_dir.resolve()
    if not raw.is_relative_to(ROOT / "external_data"):
        parser.error("Use the dedicated external_data directory, never Tactical or outputs.")
    for name, digest in EXPECTED_HASHES.items():
        path = raw / name
        if not path.is_file():
            parser.exit(1, f"Missing licensed external file:\n{path}\nSee EXTERNAL_EVALUATION.md.\n")
        if file_hash(path) != digest:
            parser.exit(1, "External source checksum mismatch. Do not substitute competition files.\n")
    manifest = convert(
        raw / METADATA, raw / POSITIONS, raw / "prepared",
        {**DATASET, "source_sha256": EXPECTED_HASHES},
    )
    print(f"Prepared external match {MATCH}: {manifest['n_frames']} rows; no algorithm tuning.")


if __name__ == "__main__":
    main()
