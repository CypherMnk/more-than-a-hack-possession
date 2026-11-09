"""Synthetic importer/scorer checks. Never reads Tactical or competition outputs."""

import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

import numpy as np

from evaluate_external import RUNS, benchmark, corrupt_tracking
from evaluation_tools import possession_metrics as pm
from prepare_external import convert, normalized_group, reference_label


def main():
    labels = pm.label_codes(list("HHHDDDAAAXHHHDDDAAA"))
    perfect = pm.evaluate(labels, labels)
    assert perfect["macro_f1"] == perfect["spell_f1_mean"] == 1.0
    assert pm.evaluate(labels, np.full(len(labels), pm.X))["spell_f1_mean"] == 0
    masked = pm.label_codes(list("HHHXXXAAADDD"))
    predicted = pm.label_codes(list("HHHDDDAAADDD"))
    assert pm.evaluate(masked, predicted)["macro_f1"] == 1.0
    filled = pm.fill_abstentions(
        pm.label_codes(list("XHHXXAX")), [(0, 4), (5, 7)],
    )
    assert list(filled) == [pm.H, pm.H, pm.H, pm.H, pm.X, pm.A, pm.A]
    fragmented = pm.label_codes(list("HAHAHDDDAAAXHHHDDDAAA"))
    truth = pm.label_codes(list("HHHHHDDDAAAXHHHDDDAAA"))
    assert pm.evaluate(truth, fragmented)["spell_f1_mean"] < 1.0
    assert reference_label({"BallStatus": "0", "BallPossession": "1"}) == "D"
    assert reference_label({"BallStatus": "1", "BallPossession": "2"}) == "A"
    assert reference_label({"BallStatus": "1", "BallPossession": "0"}) == "X"
    assert normalized_group(0, 0, (100, 60)) == "0.5,0.5,NaN"

    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        metadata = directory / "source_meta.xml"
        metadata.write_text(
            '<root><MatchInformation><General HomeTeamId="home" GuestTeamId="away"/>'
            '<Environment PitchX="100" PitchY="60"/><Teams>'
            '<Team TeamId="away"><Players><Player PersonId="a"/></Players></Team>'
            '<Team TeamId="home"><Players><Player PersonId="h"/></Players></Team>'
            '</Teams></MatchInformation></root>', encoding="utf-8",
        )
        # Source order differs from team order; N IDs restart in half 2.
        tree = ET.Element("PositionData")
        for half, start in (("firstHalf", 100), ("secondHalf", 500)):
            for person, team, x in (("a", "away", 20), ("h", "home", -20), ("BALL", "BALL", -20)):
                frameset = ET.SubElement(tree, "FrameSet", GameSection=half, TeamId=team, PersonId=person)
                for i in range(30):
                    if person == "a" and i == 1:
                        continue  # absent observation, not shifted to the next frame
                    attributes = {"N": str(start + i), "X": str(x), "Y": "0"}
                    if person == "BALL":
                        attributes.update(BallStatus="1", BallPossession="1")
                    ET.SubElement(frameset, "Frame", **attributes)
        positions = directory / "source_positions.xml"
        ET.ElementTree(tree).write(positions, encoding="utf-8")
        output = directory / "prepared"
        manifest = convert(
            metadata, positions, output,
            {"dataset": "SYNTHETIC", "match_id": "invented", "license": "synthetic-test"},
        )
        assert manifest["n_frames"] == 61
        assert manifest["play_blocks"] == [(0, 29), (31, 60)]
        lines = (output / "tracking.txt").read_text().splitlines()
        assert lines[1].startswith("2:NaN,NaN,NaN;")  # missing AWAY slot
        assert ":0.3,0.5,NaN" in lines[0]  # centred coordinates normalized
        assert "BallStatus" not in "".join(lines) and "BallPossession" not in "".join(lines)
        assert (output / "ground_truth.csv").read_text().splitlines()[31] == "30,X"
        report = benchmark(output)
        assert report["dataset"] == "SYNTHETIC"
        assert report["versions"]["v1_tracking"]["n_graded"] == 60
        assert report["versions"]["v2_tagged"]["status"] == "not_evaluated"
        for name in RUNS:
            assert report["versions"][name]["status"] == "evaluated"
            assert report["versions"][name]["n_graded"] == 60
            assert report["versions"][name]["features"]["automatic_tags"] is False
        for name in ("v3_temporal", "v4_ball_guard", "v5_control", "v6_control"):
            assert report["versions"][name]["status"] == "not_evaluated"
        assert report["versions"]["v5_no_motion"]["features"]["use_motion"] is False
        assert report["versions"]["v5_fixed_confirmation"]["features"]["adaptive"] is False
        assert report["versions"]["v5_no_jump_guard"]["features"]["use_guard"] is False
        assert report["versions"]["v5_no_restart_guard"]["features"]["restart_guard"] is False
        assert report["versions"]["v6_tracking_only"]["features"]["missing_player_flight_veto"] is True
        assert report["versions"]["v5_tracking_only"]["features"]["missing_player_flight_veto"] is False
        assert report["versions"]["v1_tracking"]["output_sha256"] == report["versions"]["v2_tracking_only"]["output_sha256"]
        first_report = (output / "report.json").read_bytes()
        benchmark(output)
        assert (output / "report.json").read_bytes() == first_report
        stressed = benchmark(output, stress=True)
        assert set(stressed["synthetic_fault_test"]["versions"]) == set(RUNS)
        stress_report = (output / "report.json").read_bytes()
        benchmark(output, stress=True)
        assert (output / "report.json").read_bytes() == stress_report
        faulted_a, faulted_b = directory / "faults_a.txt", directory / "faults_b.txt"
        corrupt_tracking(output / "tracking.txt", faulted_a, manifest["n_frames"])
        corrupt_tracking(output / "tracking.txt", faulted_b, manifest["n_frames"])
        assert faulted_a.read_bytes() == faulted_b.read_bytes()
        assert faulted_a.read_bytes() != (output / "tracking.txt").read_bytes()
        tuned = benchmark(output, v5_params={"relative_control_speed": 4.0})
        assert tuned["versions"]["v5_tracking_only"]["parameters"]["relative_control_speed"] == 4.0
        assert tuned["versions"]["v6_tracking_only"]["parameters"]["relative_control_speed"] == 3.0
        changed_positions = directory / "changed_reference.xml"
        for frameset in tree.findall("FrameSet"):
            if frameset.get("TeamId") == "BALL":
                for frame in frameset.findall("Frame"):
                    frame.set("BallStatus", "0")
                    frame.set("BallPossession", "2")
        ET.ElementTree(tree).write(changed_positions, encoding="utf-8")
        changed_output = directory / "changed_reference"
        convert(
            metadata, changed_positions, changed_output,
            {"dataset": "SYNTHETIC", "match_id": "invented", "license": "synthetic-test"},
        )
        assert (changed_output / "tracking.txt").read_bytes() == (output / "tracking.txt").read_bytes()
        assert (changed_output / "ground_truth.csv").read_bytes() != (output / "ground_truth.csv").read_bytes()
        benchmark(changed_output)
        benchmark(output)  # restore frozen defaults after the external-only parameter check
        for name in RUNS:
            assert (changed_output / f"{name}.csv").read_bytes() == (output / f"{name}.csv").read_bytes()
        ball_frameset = next(frame for frame in tree if frame.get("TeamId") == "BALL")
        ball_frameset.remove(ball_frameset.findall("Frame")[5])
        ET.ElementTree(tree).write(changed_positions, encoding="utf-8")
        try:
            convert(metadata, changed_positions, directory / "bad_timeline", {})
            raise AssertionError("A gap in the ball timeline was accepted.")
        except ValueError:
            assert not (directory / "bad_timeline").exists()
        try:
            convert(metadata, positions, output, {})
            raise AssertionError("Existing dataset was overwritten.")
        except ValueError:
            pass
        (output / "tracking.txt").write_text("tampered", encoding="utf-8")
        try:
            benchmark(output)
            raise AssertionError("Changed inference inputs accepted.")
        except ValueError:
            pass
    print("PASS: synthetic import, coordinate/frame alignment, label isolation, official metrics, and reproducibility.")


if __name__ == "__main__":
    main()
