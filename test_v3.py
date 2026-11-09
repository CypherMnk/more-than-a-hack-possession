"""Synthetic V3 checks only; no competition data, accuracy scoring, or network access."""

from itertools import product
from pathlib import Path
import tempfile

from versions.v2_tagged import possession as v2
from versions.v3_temporal import possession as v3


def main():
    # Confirm the same evidence, but remove the forced one-frame delay in this toy case.
    assert list(v2.segment("HHAA", 2)) == list("XHHA")
    assert v3.segment("HHAA", 2) == list("HHAA")
    assert v3.segment("HHAXHH", 2) == list("HHHHHH")  # transient touch
    assert v3.segment("HHXX", 2) == list("HHHH")  # missing ball is not dead ball
    assert v3.segment("HAXAA", 2) == list("XXXAA")  # no backfill across unknown gap
    assert v3.segment("HHDDXXAA", 2) == list("HHDDDDAA")
    assert v3.segment("HHA", 2) == list("HHH")  # unfinished change at end
    assert v3.segment("A", 2) == ["X"]  # no unconfirmed initial guess
    assert v3.segment("", 2) == []
    assert v3.segment("DDXXX", 2, tagging="HHHHH") == list("DDDDD")
    assert v3.segment("DDHXHH", 2, tagging="HHHHHH") == list("DDDDHH")
    assert v3.segment("HHDD", 2, tagging="AAAA") == list("HHDD")  # tracking wins
    assert v3.segment("XXXXX", 2, tagging="HHHHH") == list("HHHHH")
    assert v3.segment(
        "XXXXX", 2, ((0, 1), (3, 4)), tagging="HHHHH"
    ) == list("HHXHH")  # tagging/backdating never crosses a half boundary
    assert v3.segment("HHAAXAA", 2, ((0, 2), (5, 6))) == list("HHHXXAA")

    for duration in (0, -1, 1.5, True):
        try:
            v3.segment("HH", duration)
            raise AssertionError("Invalid confirmation duration was accepted.")
        except ValueError:
            pass
    for tracked, tagged in (("HH", "H"), ("H", "HH"), ("HH", "HD"), ("HZ", "HH")):
        try:
            v3.segment(tracked, 2, tagging=tagged)
            raise AssertionError("Invalid/misaligned evidence was accepted.")
        except ValueError:
            pass
    # At one-frame confirmation, tracking-only states equal V2 for all short sequences.
    for sequence in product("HADX", repeat=4):
        assert v3.segment(sequence, 1) == list(v2.segment(sequence, 1))

    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        meta = directory / "invented_meta.xml"
        meta.write_text(
            '<root><Team id="home"/><Team id="away"/>'
            '<Player teamId="home"/><Player teamId="away"/></root>',
            encoding="utf-8",
        )
        raw = directory / "invented_tracking.txt"
        balls = (
            ["0.1,0.5,0"] * 25 + ["NaN,NaN,NaN"] * 25
            + ["1.1,0.5,0"] * 25 + ["NaN,NaN,NaN"] * 25
            + ["0.1,0.5,0"] * 25
        )
        raw.write_text(
            "".join(
                f"{i}:0.1,0.5,0;0.9,0.5,0:{ball}\n"
                for i, ball in enumerate(balls, 1)
            ), encoding="utf-8",
        )
        tags = directory / "invented_tags.xml"
        tags.write_text(
            "<root><instance><start>0</start><end>5</end><code>BUILD UP</code>"
            "<label><group>Team</group><text>Barcelona</text></label>"
            "</instance></root>", encoding="utf-8",
        )
        teams = v3.track_teams(meta)
        expected = list("H" * 50 + "D" * 50 + "H" * 25)
        output = directory / "invented_output.csv"
        for run in range(2):
            evidence = v3.observations(raw, teams, 125, (105.3, 68), 2, 0.5)
            labels = v3.segment(
                evidence, 25, ((0, 124),), tagging=v3.tagging_evidence(tags, 125)
            )
            assert labels == expected
            v3.write_csv(output, labels, 125)
            v2.validate_csv(output, 125)
            if run == 0:
                saved = output.read_bytes()
            else:
                assert output.read_bytes() == saved
        try:
            v3.write_csv(output, ["H"], 125)
            raise AssertionError("Short output was accepted.")
        except ValueError:
            assert output.read_bytes() == saved
    print("PASS: V3 synthetic timing, dead-state guard, gaps, half reset, CSV, and determinism.")


if __name__ == "__main__":
    main()
