"""Local tracking/tagging prototype. No training, ground-truth access, or network calls."""

import argparse
import csv
from itertools import zip_longest
import math
import os
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET


# Public submission contract, not observed possession answers.
FRAME_COUNT = 199319
PLAY_BLOCKS = ((11185, 90651), (110808, 190197))
ROOT = Path(__file__).resolve().parent
# Publicly documented tag names; these are not labels learned from the match.
ATTACK_CODES = {
    "build up", "progression", "creating chances", "long ball",
    "ball in final third", "ball in the box", "attacking transition",
}
DEFENCE_CODES = {
    "defending in attacking third", "defending in middle third",
    "defending in defensive third",
}
TAG_TEAMS = {"barcelona": "H", "atletic club": "A", "athletic club": "A"}


def track_teams(path):
    """Use the team/slot order specified by the public starter's EPTS loader."""
    root = ET.parse(path).getroot()
    teams = [team.get("id") for team in root.iter("Team")]
    if len(teams) != 2 or None in teams or len(set(teams)) != 2:
        raise ValueError("Metadata must declare two distinct team IDs.")
    mapping = dict(zip(teams, ("H", "A")))
    slots = [player.get("teamId") for player in root.iter("Player")]
    if not slots or any(team not in mapping for team in slots):
        raise ValueError("Tracking slots must belong to a declared team.")
    return [mapping[team] for team in slots]


def position(group):
    values = group.strip().split(",")
    if len(values) != 3:
        raise ValueError("Expected x,y,speed.")
    x, y, speed = map(float, values)
    if math.isinf(x) or math.isinf(y) or math.isinf(speed):
        raise ValueError("Infinite tracking value.")
    return (x, y) if math.isfinite(x) and math.isfinite(y) else None


def observations(path, teams, expected_rows, pitch, control_radius, team_margin):
    """Yield H/A control evidence, D boundary evidence, or X (no evidence).

    Reject malformed records rather than silently shifting the timeline.
    Errors contain only record numbers, never restricted file contents.
    """
    count = 0
    with Path(path).open(encoding="utf-8-sig") as handle:
        for count, line in enumerate(handle, 1):
            try:
                frame, player_text, ball_text = line.strip().split(":")
                if int(frame) != count or count > expected_rows:
                    raise ValueError("Unexpected frame.")
                groups = player_text.split(";")
                if len(groups) != len(teams):
                    raise ValueError("Unexpected slot count.")
                players = [position(group) for group in groups]
                ball = position(ball_text)
            except (ValueError, OverflowError):
                raise ValueError(f"Invalid tracking record {count}; inspect locally.") from None

            if ball is None:
                yield "X"
                continue
            bx, by = ball
            if not (0 <= bx <= 1 and 0 <= by <= 1):
                # boundary-only stoppages; add external-validated
                # restart/whistle evidence before treating this as competition-ready.
                yield "D"
                continue
            distances = {"H": math.inf, "A": math.inf}
            for team, player in zip(teams, players):
                if player is not None:
                    dx = (player[0] - bx) * pitch[0]
                    dy = (player[1] - by) * pitch[1]
                    distances[team] = min(distances[team], math.hypot(dx, dy))
            team = min(distances, key=distances.get)
            other = "A" if team == "H" else "H"
            convincing = (
                distances[team] <= control_radius
                and distances[other] - distances[team] > team_margin
            )
            yield team if convincing else "X"
    if count != expected_rows:
        raise ValueError("Tracking row count does not match the requested timeline.")


def tagging_evidence(path, expected_rows, fps=25):
    """Convert automatic phases to weak H/A evidence on half-open frame intervals.

    Conflicting teams produce X, regardless of the number of overlapping tags.
    Set pieces, goals, player counts, and defensive transitions are deliberately
    excluded: their intervals do not establish the exact live-ball state.
    """
    differences = {team: [0] * (expected_rows + 1) for team in ("H", "A")}
    for event in ET.parse(path).iter("instance"):
        start = float(event.findtext("start", ""))
        end = float(event.findtext("end", ""))
        if not math.isfinite(start) or not math.isfinite(end) or end < start:
            raise ValueError("Invalid automatic tag interval.")
        code = " ".join(event.findtext("code", "").casefold().split())
        teams = {
            " ".join(label.findtext("text", "").casefold().split())
            for label in event.findall("label")
            if label.findtext("group", "").strip().casefold() == "team"
        }
        # Unknown, absent, or multiple distinct Team values are not evidence.
        side = TAG_TEAMS.get(next(iter(teams))) if len(teams) == 1 else None
        if side is None or code not in ATTACK_CODES | DEFENCE_CODES:
            continue
        if code in DEFENCE_CODES:
            side = "A" if side == "H" else "H"
        start_frame = round(max(0, min(start, expected_rows / fps)) * fps)
        end_frame = round(max(0, min(end, expected_rows / fps)) * fps)
        differences[side][start_frame] += 1
        differences[side][end_frame] -= 1
    # difference arrays avoid scanning every event per frame;
    # no learned weights or match-derived duration rules.
    home = away = 0
    for frame in range(expected_rows):
        home += differences["H"][frame]
        away += differences["A"][frame]
        yield "H" if home and not away else "A" if away and not home else "X"


def combine_evidence(tracking, tagging):
    """Tracking H/A/D takes precedence; tags fill only absent/ambiguous evidence."""
    for tracked, tagged in zip_longest(tracking, tagging):
        if tracked not in {"H", "A", "D", "X"} or tagged not in {"H", "A", "X"}:
            raise ValueError("Evidence labels or timeline lengths are invalid.")
        yield tagged if tracked == "X" else tracked


def segment(evidence, confirm_frames, play_blocks=None):
    """Keep state through uncertainty; require consecutive evidence for a change.

    This is a causal heuristic, not a trained or calibrated possession model.
    """
    if confirm_frames < 1:
        raise ValueError("Confirmation duration must be positive.")
    state, candidate, count, previous_block = "X", None, 0, None
    for frame, observation in enumerate(evidence):
        if observation not in {"H", "A", "D", "X"}:
            raise ValueError("Invalid evidence label.")
        block = 0 if play_blocks is None else next(
            (i for i, (start, end) in enumerate(play_blocks) if start <= frame <= end),
            None,
        )
        if block is None:
            state, candidate, count, previous_block = "X", None, 0, None
            yield "X"
            continue
        if block != previous_block:
            state, candidate, count = "X", None, 0
        previous_block = block
        if observation == "X" or observation == state:
            candidate, count = None, 0
        else:
            count = count + 1 if observation == candidate else 1
            candidate = observation
            if count >= confirm_frames:
                state, candidate, count = observation, None, 0
        yield state


def validate_csv(path, expected_rows):
    """Ground-truth-free contract check; no output labels or statistics printed."""
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        if next(reader, None) != ["frame", "label"]:
            raise ValueError("CSV header must be frame,label.")
        count = 0
        for frame, row in enumerate(reader):
            if len(row) != 2 or row[0] != str(frame) or row[1] not in {"H", "A", "D", "X"}:
                raise ValueError("CSV contains an invalid row.")
            count += 1
        if count != expected_rows:
            raise ValueError("CSV row count is incorrect.")


def write_csv(path, labels, expected_rows):
    """Validate a temporary file before atomically replacing an existing output."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        try:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(("frame", "label"))
            for frame, label in enumerate(labels):
                writer.writerow((frame, label))
        except BaseException:
            handle.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        validate_csv(temporary, expected_rows)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def positive(value):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("Expected a positive finite number.")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "Tactical")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--tracking-only", action="store_true", help="Run the original method.")
    parser.add_argument("--confirm-seconds", type=positive, default=1.0)
    parser.add_argument("--control-radius", type=positive, default=2.0, help="Metres.")
    parser.add_argument("--team-margin", type=positive, default=0.5, help="Metres.")
    args = parser.parse_args()
    data_dir = args.data_dir.resolve()
    name = "prototype.csv" if args.tracking_only else "prototype_tagged.csv"
    output = (args.out or ROOT / "outputs" / name).resolve()
    if output.is_relative_to(data_dir):
        parser.error("Write outputs outside the input data directory.")
    try:
        teams = track_teams(data_dir / "BAR-ATH_tactical_atd.xml")
        evidence = observations(
            data_dir / "BAR-ATH_tactical_atd.txt", teams, FRAME_COUNT,
            (105.3, 68.0), args.control_radius, args.team_margin,
        )
        if not args.tracking_only:
            evidence = combine_evidence(
                evidence,
                tagging_evidence(data_dir / "BAR-ATH_tactical_smart_tagging.xml", FRAME_COUNT),
            )
        labels = segment(evidence, max(1, math.ceil(args.confirm_seconds * 25)), PLAY_BLOCKS)
        write_csv(output, labels, FRAME_COUNT)
    except (OSError, ValueError, ET.ParseError):
        # Keep source content and parser errors out of hosted logs.
        parser.exit(1, "Local processing failed. Inspect inputs locally; no contents disclosed.\n")
    print("PASS: local processing completed and CSV format validated. Accuracy not assessed.")


if __name__ == "__main__":
    main()
