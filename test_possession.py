"""Synthetic checks only: this file never opens the competition assets."""

from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from possession import (
    combine_evidence, observations, segment, tagging_evidence,
    track_teams, validate_csv, write_csv,
)


def main():
    assert list(segment("HHAXHH", 2)) == list("XHHHHH")  # brief touch + missing ball
    assert list(segment("HHAA", 2)) == list("XHHA")  # sustained turnover
    assert list(segment("HHDDXXAA", 2)) == list("XHHDDDDA")  # stoppage + restart
    assert list(segment("HHXX", 2, ((0, 1), (3, 3)))) == list("XHXX")  # half reset
    assert list(segment("HAXAA", 2)) == list("XXXXA")  # gaps reset confirmation
    try:
        list(segment("H", 0))
        raise AssertionError("Invalid confirmation accepted.")
    except ValueError:
        pass

    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        meta = directory / "synthetic.xml"
        meta.write_text(
            '<root><Team id="home"/><Team id="away"/>'
            '<Player teamId="home"/><Player teamId="away"/></root>',
            encoding="utf-8",
        )
        teams = track_teams(meta)
        tags = directory / "synthetic_tags.xml"
        tag_root = ET.Element("root")
        for start, end, code, team in (
            (0, 4, " BUILD UP ", " Barcelona "),
            (1, 2, "PROGRESSION", "Barcelona"),  # duplicate same-team evidence
            (2, 4, "PROGRESSION", "Atletic Club"),  # opposing overlap -> X
            (4, 6, "Defending in middle third", "Barcelona"),  # implies A
            (6, 7, "SET PIECES", "Barcelona"),  # not a live/dead interval
            (6, 7, "BUILD UP", "N/A"),  # no known team
            (6, 7, "DEFENSIVE TRANSITION", "Barcelona"),  # not assumed control
            (7, 8, "PROGRESSION", "Athletic Club"),  # spelling alias
            (8, 9, "UNRECOGNIZED", "Barcelona"),
            (9, 12, "PROGRESSION", "Barcelona"),  # clip to requested timeline
        ):
            event = ET.SubElement(tag_root, "instance")
            for name, value in (("start", start), ("end", end), ("code", code)):
                ET.SubElement(event, name).text = str(value)
            label = ET.SubElement(event, "label")
            ET.SubElement(label, "group").text = "TEAM"
            ET.SubElement(label, "text").text = team
        ET.ElementTree(tag_root).write(tags, encoding="utf-8")
        assert list(tagging_evidence(tags, 10, fps=1)) == list("HHXXAAXAXH")
        tagged_output = directory / "tagged.csv"
        for _ in range(2):
            write_csv(tagged_output, segment(combine_evidence(
                "X" * 10, tagging_evidence(tags, 10, fps=1)
            ), 2), 10)
            if _ == 0:
                tagged_saved = tagged_output.read_bytes()
            else:
                assert tagged_output.read_bytes() == tagged_saved
        combined = list(combine_evidence("HXDAX", "AAHHX"))
        assert combined == list("HADAX")  # tracking H/A/D wins
        assert list(segment(combine_evidence("XXXXX", "HHHHH"), 2)) == list("XHHHH")
        assert list(segment(
            combine_evidence("XXXXX", "HHHHH"), 2, ((0, 1), (3, 4))
        )) == list("XHXXH")  # tags cannot leak state across halves
        for bad_tagging in ("H", "HHHHHH", "HHHDH"):
            try:
                list(combine_evidence("XXXXX", bad_tagging))
                raise AssertionError("Invalid tag evidence accepted.")
            except ValueError:
                pass
        tags.write_text(
            "<root><instance><start>-0.04</start><end>0.08</end>"
            "<code>BUILD UP</code><label><group>Team</group><text>Barcelona</text>"
            "</label></instance></root>", encoding="utf-8",
        )
        assert list(tagging_evidence(tags, 4)) == list("HHXX")  # 25 fps, end-exclusive
        ET.ElementTree(ET.Element("root")).write(tags, encoding="utf-8")
        assert list(tagging_evidence(tags, 4)) == list("XXXX")
        tags.write_text(
            "<root><instance><start>0</start><end>1</end><code>BUILD UP</code>"
            "<label><group>Team</group><text>Barcelona</text></label>"
            "<label><group>Team</group><text>Atletic Club</text></label>"
            "</instance></root>", encoding="utf-8",
        )
        assert list(tagging_evidence(tags, 4)) == list("XXXX")  # ambiguous Team group
        for start, end in (("NaN", "1"), ("2", "1"), ("", "1")):
            tags.write_text(
                f"<root><instance><start>{start}</start><end>{end}</end>"
                "<code>BUILD UP</code></instance></root>", encoding="utf-8",
            )
            try:
                list(tagging_evidence(tags, 10))
                raise AssertionError("Invalid interval accepted.")
            except ValueError:
                pass
        raw = directory / "synthetic.txt"
        records = [
            "0.1,0.5,0;0.9,0.5,0:0.1,0.5,0",
            "0.1,0.5,0;0.9,0.5,0:0.1,0.5,0",
            "0.1,0.5,0;0.9,0.5,0:NaN,NaN,NaN",
            "0.1,0.5,0;0.9,0.5,0:0.9,0.5,0",
            "0.1,0.5,0;0.9,0.5,0:0.9,0.5,0",
            "0.1,0.5,0;0.9,0.5,0:1.1,0.5,0",
            "0.1,0.5,0;0.9,0.5,0:1.1,0.5,0",
        ]
        raw.write_text(
            "\n".join(f"{i}:{record}" for i, record in enumerate(records, 1)) + "\n",
            encoding="utf-8",
        )
        evidence = list(observations(raw, teams, 7, (105.3, 68), 2, 0.5))
        assert evidence == list("HHXAADD")
        output = directory / "synthetic.csv"
        write_csv(output, segment(evidence, 2), 7)
        validate_csv(output, 7)
        saved = output.read_bytes()
        write_csv(output, segment(evidence, 2), 7)
        assert output.read_bytes() == saved
        try:
            write_csv(output, ["H"], 7)
            raise AssertionError("Short output accepted.")
        except ValueError:
            assert output.read_bytes() == saved  # preserve previous valid output
        raw.write_text("2:" + records[0] + "\n", encoding="utf-8")
        try:
            list(observations(raw, teams, 1, (105.3, 68), 2, 0.5))
            raise AssertionError("Misaligned input accepted.")
        except ValueError:
            pass
    print("PASS: synthetic tracking, tagging, conflicts, state, CSV, and determinism checks.")


if __name__ == "__main__":
    main()
