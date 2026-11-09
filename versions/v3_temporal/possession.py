"""V3: offline transition timing and tracking-confirmed exits from dead-ball states."""

import argparse
from itertools import zip_longest
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
# Reuse the frozen V2 input/output helpers, never the evolving root algorithm.
from versions.v2_tagged.possession import (
    FRAME_COUNT, PLAY_BLOCKS, observations, positive, tagging_evidence,
    track_teams, write_csv,
)


def segment(evidence, confirm_frames, play_blocks=None, *, tagging=None):
    """Confirm sustained changes, then assign the new state from the evidence onset.

    Tags can support team control, but cannot alone exit an established D state.
    Missing/ambiguous evidence still resets confirmation; gaps are not fabricated.
    """
    if not isinstance(confirm_frames, int) or isinstance(confirm_frames, bool) or confirm_frames < 1:
        raise ValueError("Confirmation duration must be a positive integer.")
    pairs = (
        ((tracked, "X") for tracked in evidence)
        if tagging is None else zip_longest(evidence, tagging)
    )
    labels = []
    state, candidate, count, onset, previous_block = "X", None, 0, None, None
    for frame, (tracked, tagged) in enumerate(pairs):
        if tracked not in {"H", "A", "D", "X"} or tagged not in {"H", "A", "X"}:
            raise ValueError("Evidence labels or timeline lengths are invalid.")
        block = 0 if play_blocks is None else next(
            (i for i, (start, end) in enumerate(play_blocks) if start <= frame <= end),
            None,
        )
        if block is None:
            state, candidate, count, onset, previous_block = "X", None, 0, None, None
            labels.append("X")
            continue
        if block != previous_block:
            state, candidate, count, onset = "X", None, 0, None
        previous_block = block
        observation = tagged if tracked == "X" and state != "D" else tracked
        labels.append(state)
        if observation == "X" or observation == state:
            candidate, count, onset = None, 0, None
        else:
            if observation != candidate:
                candidate, count, onset = observation, 0, frame
            count += 1
            if count >= confirm_frames:
                state = observation
                # O(frames) output buffer; bounded-lookahead
                # streaming if recording size makes memory a problem.
                labels[onset:frame + 1] = [state] * (frame - onset + 1)
                candidate, count, onset = None, 0, None
    return labels


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "Tactical")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "v3_temporal.csv")
    parser.add_argument("--confirm-seconds", type=positive, default=1.0)
    parser.add_argument("--control-radius", type=positive, default=2.0, help="Metres.")
    parser.add_argument("--team-margin", type=positive, default=0.5, help="Metres.")
    args = parser.parse_args()
    data_dir, output = args.data_dir.resolve(), args.out.resolve()
    if output.is_relative_to(data_dir):
        parser.error("Write outputs outside the input data directory.")
    try:
        teams = track_teams(data_dir / "BAR-ATH_tactical_atd.xml")
        evidence = observations(
            data_dir / "BAR-ATH_tactical_atd.txt", teams, FRAME_COUNT,
            (105.3, 68.0), args.control_radius, args.team_margin,
        )
        tags = tagging_evidence(data_dir / "BAR-ATH_tactical_smart_tagging.xml", FRAME_COUNT)
        labels = segment(
            evidence, max(1, math.ceil(args.confirm_seconds * 25)), PLAY_BLOCKS,
            tagging=tags,
        )
        write_csv(output, labels, FRAME_COUNT)
    except (OSError, ValueError, ET.ParseError):
        parser.exit(1, "Local processing failed. Inspect inputs locally; no contents disclosed.\n")
    print("PASS: V3 local processing and CSV format. Accuracy not assessed.")


if __name__ == "__main__":
    main()
