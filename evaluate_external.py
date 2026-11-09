"""Evaluate frozen versions only on an explicitly prepared external dataset."""

import argparse
import importlib.util
import json
import math
from pathlib import Path
import random
import tempfile

from evaluation_tools import possession_metrics as pm
from prepare_external import DATASET, EXPECTED_HASHES, MATCH, ROOT, file_hash


# Missing automatic tags are NOT synthesized from possession reference labels.
RUNS = {
    "v1_tracking": ("v1_tracking", {}),
    "v2_tracking_only": ("v2_tagged", {}),
    "v3_tracking_only": ("v3_temporal", {}),
    "v4_tracking_only": ("v4_ball_guard", {}),
    "v5_tracking_only": ("v5_control", {}),
    "v5_no_motion": ("v5_control", {"use_motion": False}),
    "v5_fixed_confirmation": ("v5_control", {"adaptive": False}),
    "v5_no_jump_guard": ("v5_control", {"use_guard": False}),
    "v5_no_restart_guard": ("v5_control", {"restart_guard": False}),
    "v6_tracking_only": ("v6_control", {}),
}
FAULTS = {"seed": 101, "ball_missing": 0.10, "player_missing": 0.05, "ball_spike": 0.01}


def load_version(version):
    path = ROOT / "versions" / version / "possession.py"
    spec = importlib.util.spec_from_file_location(version, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path


def infer(version, tracking, metadata, manifest, flags=None, v5_params=None):
    """Inference gets tracking/metadata only; no reference table or reference file."""
    flags = flags or {}
    algorithm, source = load_version(version)
    teams = algorithm.track_teams(metadata)
    n, fps, blocks = manifest["n_frames"], manifest["fps"], manifest["play_blocks"]
    arguments = tracking, teams, n, manifest["pitch"], 2.0, 0.5
    parameters = {"control_radius_m": 2.0, "team_margin_m": 0.5, "confirm_seconds": 1.0}
    features = {"automatic_tags": False}
    if version == "v4_ball_guard":
        evidence = algorithm.guarded_evidence(*arguments, fps=fps, play_blocks=blocks)
        labels = algorithm.segment(evidence, math.ceil(fps), blocks)
        parameters["max_ball_speed_m_s"] = 60.0
    elif version in {"v5_control", "v6_control"}:
        # Preserve the existing V5-only tuning interface; V6 uses frozen defaults.
        parameters = algorithm.settings(v5_params if version == "v5_control" else None)
        features |= {
            "use_motion": True, "use_guard": True, "adaptive": True, "restart_guard": True,
            "missing_player_flight_veto": version == "v6_control",
        } | flags
        evidence = algorithm.observations(
            *arguments, fps=fps, play_blocks=blocks, params=parameters, use_tags=False,
            use_motion=features["use_motion"], use_guard=features["use_guard"],
        )
        labels = algorithm.segment(
            evidence, play_blocks=blocks, fps=fps, params=parameters,
            adaptive=features["adaptive"], restart_guard=features["restart_guard"],
        )
    else:
        evidence = algorithm.observations(*arguments)
        labels = algorithm.segment(evidence, math.ceil(fps), blocks)
    return algorithm, source, labels, parameters, features


def corrupt_tracking(source, output, n):
    """Deterministic synthetic faults on EXTERNAL tracking, never match-calibrated."""
    rng = random.Random(FAULTS["seed"])
    count = 0
    with Path(source).open(encoding="utf-8-sig") as reader, Path(output).open("w", encoding="utf-8") as writer:
        for count, line in enumerate(reader, 1):
            frame, player_text, ball = line.strip().split(":")
            if int(frame) != count or count > n:
                raise ValueError("Invalid external fault-test timeline.")
            players = [
                "NaN,NaN,NaN" if rng.random() < FAULTS["player_missing"] else group
                for group in player_text.split(";")
            ]
            if rng.random() < FAULTS["ball_missing"]:
                ball = "NaN,NaN,NaN"
            elif rng.random() < FAULTS["ball_spike"]:
                ball = "2,2,NaN"
            writer.write(f"{frame}:{';'.join(players)}:{ball}\n")
    if count != n:
        raise ValueError("External fault-test row count changed.")


def score_runs(folder, tracking, manifest, gt, *, suffix="", v5_params=None):
    results = {}
    for name, (version, flags) in RUNS.items():
        algorithm, source, labels, parameters, features = infer(
            version, tracking, folder / "metadata.xml", manifest, flags, v5_params,
        )
        output = folder / f"{name}{suffix}.csv"
        algorithm.write_csv(output, labels, manifest["n_frames"])
        metrics = pm.evaluate(gt, pm.label_codes(pm.read_label_csv(output)))
        dependencies = {"v2_tagged"}
        if version == "v4_ball_guard":
            dependencies.add("v3_temporal")
        if version == "v1_tracking":
            dependencies.clear()
        results[name] = {
            "status": "evaluated",
            "mode": (
                "full tracking-only algorithm" if version == "v1_tracking"
                else "tracking-only ablation; full automatic-tag feature not tested"
            ),
            "source_sha256": file_hash(source),
            "dependency_sha256": {
                dependency: file_hash(ROOT / "versions" / dependency / "possession.py")
                for dependency in sorted(dependencies) if dependency != version
            },
            "output_sha256": file_hash(output),
            "parameters": parameters,
            "features": features,
            "spellF1": metrics["spell_f1_mean"],
            "macroF1": metrics["macro_f1"],
            "frame_accuracy": metrics["accuracy"],
            "per_class": metrics["per_class"],
            "n_graded": metrics["n_graded"],
            "n_gt_spells": metrics["n_gt_spells"],
            "n_pred_spells": metrics["n_pred_spells"],
        }
    return results


def benchmark(folder, *, stress=False, v5_params=None):
    """Never pass provider possession/dead-ball reference attributes to inference."""
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    n = manifest["n_frames"]
    if not isinstance(n, int) or isinstance(n, bool) or n < 1 or manifest["fps"] != 25:
        raise ValueError("This harness supports the documented 25 fps external export.")
    for name in ("metadata.xml", "tracking.txt", "ground_truth.csv", "frame_map.csv"):
        if file_hash(folder / name) != manifest["prepared_sha256"][name]:
            raise ValueError("Prepared file changed; regenerate from the licensed source.")
    table = pm.read_label_csv(folder / "ground_truth.csv")
    reason = pm.validate_submission(table, n)
    if reason:
        raise ValueError(reason)
    gt = pm.label_codes(table)
    if not pm.valid_runs(gt):
        raise ValueError("No labelled external frames are available.")

    report = {
        "dataset": manifest["dataset"], "match_id": manifest["match_id"],
        "license": manifest["license"], "n_frames": n,
        "purpose": "External development benchmark; not competition-match accuracy.",
        "metrics_source": json.loads((ROOT / "evaluation_tools" / "SOURCE.json").read_text()),
        "input_sha256": manifest["prepared_sha256"],
        "versions": {},
    }
    for version in ("v2_tagged", "v3_temporal", "v4_ball_guard", "v5_control", "v6_control"):
        report["versions"][version] = {
            "status": "not_evaluated",
            "reason": "No compatible external automatic Smart Tagging supplied; see tracking-only modes.",
        }
    report["versions"].update(score_runs(
        folder, folder / "tracking.txt", manifest, gt, v5_params=v5_params,
    ))
    if stress:
        # one frozen fault preset, not a noise-parameter
        # search; expand only when additional external conditions are justified.
        with tempfile.TemporaryDirectory(dir=folder) as directory:
            tracking = Path(directory) / "faulted_external_tracking.txt"
            corrupt_tracking(folder / "tracking.txt", tracking, n)
            report["synthetic_fault_test"] = {
                "parameters": FAULTS,
                "tracking_sha256": file_hash(tracking),
                "reference_labels": "unchanged external labels; never passed to inference",
                "versions": score_runs(
                    folder, tracking, manifest, gt, suffix="_faults", v5_params=v5_params,
                ),
            }
    (folder / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "external_data" / MATCH / "prepared")
    parser.add_argument("--stress", action="store_true", help="Also run a fixed synthetic-fault test on external tracking.")
    parser.add_argument("--v5-params", type=Path, help="External-development JSON settings only; never match/video-tuned.")
    args = parser.parse_args()
    folder = args.data_dir.resolve()
    if not folder.is_relative_to(ROOT / "external_data"):
        parser.error("Only external_data is accepted; competition files must not be scored here.")
    if not (folder / "manifest.json").is_file():
        parser.exit(1, "Run prepare_external.py after downloading the external source files.\n")
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if any(manifest.get(key) != DATASET[key] for key in ("dataset", "match_id", "license")):
        parser.error("Expected the licensed external IDSSE match, not competition or synthetic data.")
    if manifest.get("source_sha256") != EXPECTED_HASHES:
        parser.error("Missing verified external source provenance.")
    params = None if args.v5_params is None else json.loads(args.v5_params.read_text(encoding="utf-8"))
    report = benchmark(folder, stress=args.stress, v5_params=params)
    for version, result in report["versions"].items():
        if result["status"] == "evaluated":
            print(f"{version}: external spellF1={result['spellF1']:.4f}, macroF1={result['macroF1']:.4f}")
        else:
            print(f"{version}: NOT EVALUATED — {result['reason']}")
    print(f"Report: {folder / 'report.json'}")
    if args.stress:
        print("External synthetic-fault results are included in the report.")
    print("External benchmark only; no competition score or best-version claim.")


if __name__ == "__main__":
    main()
