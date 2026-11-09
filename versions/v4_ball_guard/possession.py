"""V4: V3 with an unvalidated, local-only ball-position jump guard."""

import argparse
from itertools import tee, zip_longest
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from versions.v2_tagged.possession import (
    FRAME_COUNT, PLAY_BLOCKS, observations as tracking_observations, position,
    positive, tagging_evidence, track_teams, write_csv,
)
from versions.v3_temporal.possession import segment as temporal_segment


def guarded_evidence(
    path, teams, expected_rows, pitch, control_radius, team_margin, *,
    tagging=None, max_ball_speed=60.0, fps=25, play_blocks=None,
):
    """Yield tracking/tag pairs, masking both at an implausible ball jump.

    Compare with the last accepted position, allowing elapsed time across gaps.
    Two consecutive plausible raw positions can reacquire a relocated track.
    Missing positions retain V3's tagging fallback; rejected jumps do not.
    """
    if len(pitch) != 2 or any(
        not math.isfinite(value) or value <= 0
        for value in (*pitch, max_ball_speed, fps)
    ):
        raise ValueError("Pitch dimensions, speed ceiling, and frame rate must be positive and finite.")
    tracking = tracking_observations(
        path, teams, expected_rows, pitch, control_radius, team_margin,
    )
    if tagging is None:
        tagging = ("X" for _ in range(expected_rows))
    anchor = previous = previous_block = None
    max_step = max_ball_speed / fps
    # reread only ball fields alongside frozen V2 validation;
    # a shared record parser is worth extracting only if input I/O becomes costly.
    with Path(path).open(encoding="utf-8-sig") as handle:
        for frame, (line, tracked, tagged) in enumerate(zip_longest(handle, tracking, tagging)):
            if line is None or tracked not in {"H", "A", "D", "X"} or tagged not in {"H", "A", "X"}:
                raise ValueError("Evidence labels or timeline lengths are invalid.")
            block = 0 if play_blocks is None else next(
                (i for i, (start, end) in enumerate(play_blocks) if start <= frame <= end),
                None,
            )
            if block != previous_block or block is None:
                anchor = previous = None
            previous_block = block
            # V2 has already validated this same record, including every player.
            ball = position(line.strip().split(":")[2])
            if ball is None or block is None:
                previous = None
                yield tracked, tagged
                continue
            plausible = anchor is None or any(
                math.hypot(
                    (ball[0] - sample[1][0]) * pitch[0],
                    (ball[1] - sample[1][1]) * pitch[1],
                ) <= max_step * (frame - sample[0])
                for sample in (anchor, previous) if sample is not None
            )
            # a coherent pair can still be a sustained tracking
            # error; validate a stronger reacquisition rule on external data only.
            previous = frame, ball
            if plausible:
                anchor = previous
            yield (tracked, tagged) if plausible else ("X", "X")


def segment(evidence, confirm_frames, play_blocks=None):
    """Reuse V3 timing/dead-state rules without buffering another full timeline."""
    tracking, tagging = tee(evidence)
    return temporal_segment(
        (tracked for tracked, _ in tracking), confirm_frames, play_blocks,
        tagging=(tagged for _, tagged in tagging),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "Tactical")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "v4_ball_guard.csv")
    parser.add_argument("--confirm-seconds", type=positive, default=1.0)
    parser.add_argument("--control-radius", type=positive, default=2.0, help="Metres.")
    parser.add_argument("--team-margin", type=positive, default=0.5, help="Metres.")
    parser.add_argument(
        "--max-ball-speed", type=positive, default=60.0,
        help="Unvalidated m/s ceiling; freeze for this match, tune on external data only.",
    )
    args = parser.parse_args()
    data_dir, output = args.data_dir.resolve(), args.out.resolve()
    if output.is_relative_to(data_dir):
        parser.error("Write outputs outside the input data directory.")
    try:
        teams = track_teams(data_dir / "BAR-ATH_tactical_atd.xml")
        evidence = guarded_evidence(
            data_dir / "BAR-ATH_tactical_atd.txt", teams, FRAME_COUNT,
            (105.3, 68.0), args.control_radius, args.team_margin,
            tagging=tagging_evidence(data_dir / "BAR-ATH_tactical_smart_tagging.xml", FRAME_COUNT),
            max_ball_speed=args.max_ball_speed, play_blocks=PLAY_BLOCKS,
        )
        labels = segment(evidence, max(1, math.ceil(args.confirm_seconds * 25)), PLAY_BLOCKS)
        write_csv(output, labels, FRAME_COUNT)
    except (OSError, ValueError, ET.ParseError):
        parser.exit(1, "Local processing failed. Inspect inputs locally; no contents disclosed.\n")
    print("PASS: V4 local processing and CSV format. Accuracy not assessed.")


if __name__ == "__main__":
    main()
