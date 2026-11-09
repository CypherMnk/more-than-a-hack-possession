# External accuracy evaluation

**Status:** the importer and evaluation harness have synthetic checks. A real
external accuracy score has not been produced: this network's security filter
blocked the large tracking download. Do not mistake test scores for real accuracy.
**User decision:** do not retry downloads or circumvent blocks on this corporate
laptop. External accuracy testing is deferred to another approved environment.

## Licensed dataset

IDSSE: *An integrated dataset of spatiotemporal and event data in elite soccer*,
Bassek, Manuel; Rein, Robert; Weber, Hendrik; Memmert, Daniel (2025),
Scientific Data 12, 195. DOI: https://doi.org/10.1038/s41597-025-04505-y.

Data owner: **Deutsche Fußball Liga (DFL)**.
License: **CC-BY 4.0**, https://creativecommons.org/licenses/by/4.0/.
Credit DFL, cite the publication, link the license, and state any transformations.
The paper and authors' repository explicitly confirm the dataset license.

- Original source: https://doi.org/10.6084/m9.figshare.28196177
- Authors' repository: https://github.com/spoho-datascience/idsse-data
- PySport mirror: https://huggingface.co/datasets/pysport/idsse-data/tree/a715a38dfbaf5f58e431727c2b78d174101a703c

The chosen external match is **Fortuna Düsseldorf vs SSV Jahn Regensburg**,
August 26, 2022, match ID **J03WOH**. This is not the competition match.

## Files needed

Use the authorised download page in a normal browser. If a corporate security
filter blocks it, request access through the appropriate IT process; this tool
does not circumvent that filter.

Save under `C:\More than a hack\external_data\J03WOH`:

- `C:\More than a hack\external_data\J03WOH\DFL_04_03_positions_raw_observed_DFL-COM-000002_DFL-MAT-J03WOH.xml`
  — approximately 349 MB; **still missing**.
- `C:\More than a hack\external_data\J03WOH\DFL_02_01_matchinformation_DFL-COM-000002_DFL-MAT-J03WOH.xml`
  — approximately 12 KB; downloaded already.

The importer verifies their pinned SHA-256 hashes. No event file or video is
needed for V1. `external_data` is excluded from Git.

## How to run

```powershell
Set-Location 'C:\More than a hack'
& 'C:\More than a hack\.venv\Scripts\python.exe' -m pip install -r 'C:\More than a hack\requirements-evaluation.txt'
& 'C:\More than a hack\.venv\Scripts\python.exe' 'C:\More than a hack\test_external.py'
& 'C:\More than a hack\.venv\Scripts\python.exe' 'C:\More than a hack\prepare_external.py'
& 'C:\More than a hack\.venv\Scripts\python.exe' 'C:\More than a hack\evaluate_external.py'
# Optional: also measure a fixed synthetic-fault condition on EXTERNAL data.
& 'C:\More than a hack\.venv\Scripts\python.exe' 'C:\More than a hack\evaluate_external.py' --stress
```

The virtual environment is already set up on this machine. On a new machine,
create it first with `python -m venv 'C:\More than a hack\.venv'`.
The original algorithms still use only the standard library.

## Data flow and outputs

The converter changes centred metre coordinates to normalized pitch coordinates.
It keeps each source half separate, with one explicitly unknown separator row,
and records source frame IDs in `frame_map.csv`. It does not copy the competition
frame count, grading blocks, or club names onto this different match.

Provider `BallStatus` and `BallPossession` are exported **only as reference labels**:
dead -> D; live and home -> H; live and away -> A; missing/unknown -> X.
They never enter inference inputs. No Smart Tagging is synthesized from them.
Speed is set to NaN because the frozen algorithms do not use speed.

Prepared files are written in a new
`C:\More than a hack\external_data\J03WOH\prepared` directory.
Re-running preparation refuses to overwrite it.
Outputs include `v1_tracking.csv`, `v2_tracking_only.csv`, `v3_tracking_only.csv`,
`v4_tracking_only.csv`, `v5_tracking_only.csv`, and the four V5 feature-removal
outputs, all under `C:\More than a hack\external_data\J03WOH\prepared`.
The harness also produces `v6_tracking_only.csv` with unchanged V5 thresholds
and the missing-player flight-veto fix.
The score report is
`C:\More than a hack\external_data\J03WOH\prepared\report.json`.
Competition algorithms and outputs are not modified.

## What the report can and cannot establish

- Uses the official, MIT-licensed possession metric library, pinned to commit
  `f8f2629ff1e0985f81d7e59d8413678514ee1530`. Attribution/license are in
  `C:\More than a hack\evaluation_tools\LICENSE` and source provenance in
  `C:\More than a hack\evaluation_tools\SOURCE.json`.
- Reports spellF1, macroF1, frame accuracy, per-class F1, input/source/dependency/
  output hashes, feature flags and parameters. No parameter sweep or automatic
  version selection is run.
- Full tag-enabled V2-V6 modes are **not evaluated**: this source has no compatible
  automatic Smart Tagging. Explicitly named tracking-only modes are compared.
  Passing reference labels as fake tags would leak answers and invalidate the test.
- V5 feature-removal tests disable motion, adaptive confirmation, the ball jump
  guard or the placement/restart guard ONE at a time. All are tracking-only; they
  do not measure the benefit or harm of the tag feature.
- `--stress` adds fixed, independently generated ball dropout (10%), player-slot
  dropout (5%) and occasional normalized (2,2) ball spikes (1% conditional on no
  ball dropout), with seed 101. These are not measurements of this match or rates
  tuned to it. External reference labels stay unchanged and outside inference.
  Faulted inputs are temporary; their hash, fixed recipe and `_faults.csv` outputs
  are recorded. Clean and stress results must be reproducible.
- Reference possession is defined by the provider as control; loose-ball and
  transition conventions may differ from Metrica's. This is an external benchmark,
  not an estimate guaranteed to match the private competition score.
- The external tracking is post-processed and differs from the competition's
  noisy automatic tracking. One match cannot establish robust generalization.
- If later tuning on this external match, report that as development performance
  and reserve other external matches for an honest held-out comparison.

## External-development settings for V5

On the approved external machine only, `--v5-params` can read a JSON object with
named settings from `DEFAULTS` in
`C:\More than a hack\versions\v5_control\possession.py`. For example, a development
file may override `relative_control_speed`; the report records the merged values.
Do NOT use this option to optimize on the supplied match/video/ground truth.
This does not modify frozen algorithm sources or competition CSVs.
This option applies only to V5 runs. V6 tracking-only uses its frozen defaults;
V5 overrides are not silently transferred to V6.

The tests exercise this interface on invented data, not on the missing real
dataset. No real external accuracy result has been produced on this laptop.

No competition video, public/private ground truth, or result CSV is used here.
