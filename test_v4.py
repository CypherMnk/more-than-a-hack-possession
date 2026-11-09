"""Synthetic V4 checks only: no match inspection, accuracy scoring, or network."""

from pathlib import Path
import tempfile

from versions.v2_tagged import possession as v2
from versions.v4_ball_guard import possession as v4


def main():
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        raw = directory / "invented_tracking.txt"

        def run(balls, tags=None, **kwargs):
            raw.write_text(
                "".join(
                    f"{frame}:0.1,0.5,0;0.9,0.5,0:"
                    + ("NaN,NaN,NaN" if ball is None else f"{ball[0]},{ball[1]},0")
                    + "\n"
                    for frame, ball in enumerate(balls, 1)
                ), encoding="utf-8",
            )
            return list(v4.guarded_evidence(
                raw, ["H", "A"], len(balls), (105.3, 68), 2, 0.5,
                tagging=tags, **kwargs,
            ))

        def at(*xs):
            return [(x, 0.5) if x is not None else None for x in xs]

        assert run(at(0.1, 0.11, 0.115)) == [("H", "X")] * 3
        assert run([(0.1, y) for y in (0.5, 0.51, 0.52)]) == [("H", "X")] * 3
        # An isolated jump cannot supply away-team or boundary evidence.
        for spike in (0.9, 1.1):
            pairs = run(at(0.1, spike, 0.1), tags="AAA")
            assert pairs == [("H", "A"), ("X", "X"), ("H", "A")]
            assert v4.segment(pairs, 1) == list("HHH")
        # A coherent second observation reacquires, rather than rejecting forever.
        pairs = run(at(0.1, 0.1, 0.9, 0.9, 0.9))
        assert [tracked for tracked, _ in pairs] == list("HHXAA")
        assert v4.segment(pairs, 2) == list("HHHAA")
        assert run(at(0.1, None, 0.9, 0.9), tags="AAAA") == [
            ("H", "A"), ("X", "A"), ("X", "X"), ("A", "A"),
        ]
        # Missing frames allow elapsed travel time, but cannot bridge a pending change.
        assert run(at(0.1, None, 0.14), tags="AAA")[-1] == ("X", "A")
        assert run(at(0.1, *([None] * 49), 0.9))[-1] == ("A", "X")
        assert v4.segment(
            run(at(0.1, 0.1, None, 0.9, 0.1), tags="AAAAA"), 2,
        ) == list("HHHHH")
        # Plausible boundary crossings still give D; tags cannot restart D on a spike.
        assert v4.segment(run(at(0.99, 1.01, 1.02)), 2) == list("XDD")
        assert v4.segment(
            run(at(0.99, 1.01, 1.02, 0.1, 1.02), tags="HHHHH"), 2,
        ) == list("XDDDD")
        assert run(at(0.99, 1.0, 1.01))[-1] == ("D", "X")
        # Neither motion anchors nor possession states carry across halves.
        blocks = ((0, 1), (3, 4))
        pairs = run(at(0.1, 0.1, 1.1, 0.9, 0.9), play_blocks=blocks)
        assert v4.segment(pairs, 2, blocks) == list("HHXAA")
        assert run(at(0.1, 0.9), play_blocks=((0, 0), (1, 1)))[-1] == ("A", "X")
        # Speed checks use metres, frame rate and elapsed frames, not normalized distance.
        assert run(at(0.1, 0.11), max_ball_speed=20)[-1] == ("X", "X")
        assert run(at(0.1, 0.11), max_ball_speed=20, fps=10)[-1] == ("H", "X")
        assert run([]) == []

        for parameter in ("max_ball_speed", "fps"):
            for value in (0, -1, float("nan"), float("inf")):
                try:
                    run(at(0.1), **{parameter: value})
                    raise AssertionError("Invalid physical parameter was accepted.")
                except ValueError:
                    pass
        for tags in ("H", "HHH", "HD", "HZ"):
            try:
                run(at(0.1, 0.1), tags=tags)
                raise AssertionError("Invalid/misaligned tags were accepted.")
            except ValueError:
                pass
        # Frozen V2 validation remains active for ball AND player fields/frame IDs.
        for record, expected_rows in (
            ("1:0.1,0.5,0;0.9,0.5,0:0.1,0.5,0\n", 2),
            ("2:0.1,0.5,0;0.9,0.5,0:0.1,0.5,0\n", 1),
            ("1:0.1,0.5,0:0.1,0.5,0\n", 1),
            ("1:bad,0.5,0;0.9,0.5,0:0.1,0.5,0\n", 1),
            ("1:0.1,0.5,0;0.9,0.5,0:inf,0.5,0\n", 1),
        ):
            raw.write_text(record, encoding="utf-8")
            try:
                list(v4.guarded_evidence(raw, ["H", "A"], expected_rows, (105.3, 68), 2, 0.5))
                raise AssertionError("Invalid tracking was accepted.")
            except ValueError:
                pass

        meta = directory / "invented_meta.xml"
        meta.write_text(
            '<root><Team id="home"/><Team id="away"/>'
            '<Player teamId="home"/><Player teamId="away"/></root>', encoding="utf-8",
        )
        tags = directory / "invented_tags.xml"
        tags.write_text(
            "<root><instance><start>0</start><end>1</end><code>BUILD UP</code>"
            "<label><group>Team</group><text>Atletic Club</text></label>"
            "</instance></root>", encoding="utf-8",
        )
        output = directory / "invented_output.csv"
        for iteration in range(2):
            run(at(0.1, 0.1, 1.1, 0.1))
            pairs = v4.guarded_evidence(
                raw, v4.track_teams(meta), 4, (105.3, 68), 2, 0.5,
                tagging=v4.tagging_evidence(tags, 4),
            )
            labels = v4.segment(pairs, 2)
            assert labels == list("HHHH")
            v4.write_csv(output, labels, 4)
            v2.validate_csv(output, 4)
            if iteration == 0:
                saved = output.read_bytes()
            else:
                assert output.read_bytes() == saved
        try:
            v4.write_csv(output, ["H"], 4)
            raise AssertionError("Short output was accepted.")
        except ValueError:
            assert output.read_bytes() == saved
    print("PASS: V4 synthetic jump guard, reacquisition, gaps, tagging, halves, validation, and determinism.")


if __name__ == "__main__":
    main()
