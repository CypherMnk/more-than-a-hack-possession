# V6 possession candidate - method note

## Status and change from V5

Deterministic offline heuristic, not a learned or calibrated model.
**No real external accuracy result or competition accuracy result is available.**
V6 fixes one demonstrated software inconsistency; it is not selected as the most
accurate version. V1-V5 source snapshots and previously generated results remain.

V5 returned "ambiguous" before checking ball motion when all players were missing.
A weak automatic phase could then switch the established team. V6 checks trusted,
consecutive ball motion first: if its speed exceeds the existing relative-control
threshold, the observation vetoes weak tag fallback even without player positions.
This is a conservative veto, not proof of a pass or of absence of control.
Slow/stationary or unavailable motion still permits the existing weak fallback.
Gaps, rejected ball jumps and half changes still reset derivatives.
**No new threshold and no match-specific tuning were introduced.**

## Input and output

- Automatic tactical tracking TXT: one-based consecutive frame IDs, player-slot
  and ball normalized x/y positions, plus parsed but unused speed fields.
- Metadata XML: maps slots to home/away teams. Slots are not permanent identities.
- Automatic tactical Smart Tagging XML: optional weak phase evidence.
- Fixed pitch: 105.3 x 68 m; frame rate: 25 fps.
- Output CSV: `frame,label`; 199,319 zero-based frames with H/A/D/X labels.
- Inclusive active blocks: 11185-90651 and 110808-190197. X outside the blocks;
  state and motion reset between halves.
- Video, broadcast, homography, audio and possession reference labels are unused.

## Unchanged V5 method and assumptions

1. Strict record validation; finite coordinates scaled to metres; no interpolation.
2. Fixed ball-jump guard; elapsed-time allowance and coherent-pair reacquisition.
3. Convincing nearest-team proximity and usable player/ball co-motion supply
   control evidence. Flight, contests and rejected jumps veto phase fallback.
4. Confirm each evidence category for its fixed duration; backdate a confirmed
   transition to the start of that streak, never across gaps or half boundaries.
5. Sustained clearly outside-pitch evidence may establish D. To restart, require
   observed in-pitch placement, subsequent displacement and confirmed tracking
   control. Phases alone cannot exit D.
6. Validate the result CSV before atomic output replacement.

| Parameter | Frozen value |
|---|---:|
| Control radius / opposing-team margin | 2 m / 0.5 m |
| Ball jump / player derivative ceilings | 60 m/s / 15 m/s |
| Relative-control speed ceiling | 3 m/s |
| Outside-pitch margin | 0.25 m |
| Co-motion / proximity confirmation | 0.2 s / 1 s |
| Phase / boundary confirmation | 2 s / 1 s |
| Displacement after in-pitch placement | 1 m |

All values are arbitrary, unvalidated engineering assumptions, identical to V5.
They are not probabilities, fitted values or physical guarantees.

## Reproduce

Python 3.10+; inference and synthetic algorithm checks use only the standard library.
From the extracted source root:

```text
python test_v6.py
python versions/v6_control/possession.py --data-dir /path/to/Tactical --out regenerated.csv
```

Runtime requires the frozen V6 and V2 source files. The candidate archive also
includes V5 and its synthetic suite for shared regression checks.
Obtain authorised input assets separately; they are not bundled.
V6's output CLI rejects non-CSV destinations, input-directory destinations,
repository metadata and dependency folders. These are I/O safeguards, not
changes to the numerical algorithm or its thresholds.

For a fresh reviewed delivery, run `prepare_submission.py` in the separate
evaluation environment. It runs the bundled source snapshot, tests it, applies
the pinned official CSV-format validator without possession references, and
records verification in the private manifest. The exact bytes validated by
the bundle builder are archived; an earlier filename is not source provenance.
Third-party licensing/source notices remain included.

## Checks versus accuracy

Synthetic cases cover the missing-player veto, old-behaviour reproduction,
stationary fallback, disabled motion, gaps, boundaries, rejected jumps and halves.
The shared V5 suite also runs against V6, including restart, parsing, temporal,
CSV and determinism checks. Candidate packaging is separately checked using an
invented CSV, with an exact allowlist, hashes and atomic replacement.

The external harness includes frozen V6 tracking-only inference. Full tag-enabled
V6 is explicitly not evaluated: the external source has no compatible automatic
tags. External downloads/testing remain deferred to an approved environment.
The existing `--v5-params` option affects V5 only, not frozen V6.
No synthetic score should be presented as real football accuracy.
Format validation is not accuracy evaluation or confirmation of submission
portal acceptance. Current organiser delivery/disclosure requirements must be
confirmed independently.

## Limitations and compliance

Co-motion and fast ball motion do not prove possession or non-possession.
2D tracks omit ball height. Jitter, missing players, slot changes and coherent
wrong tracks can defeat the heuristics. The new veto may ignore useful tags
during fast motion when the controlling player is unobserved.
In-pitch whistles/stoppages remain undetected. Restart checks can prolong D
through a genuine kicked restart; moved placements can imitate a restart.
Onset backdating uses future confirmation, so this is not a live algorithm.

No supplied-match training, fitting, calibration, parameter selection, manual
labels, ground-truth scoring or video/output checking. Local inference and
automatic technical checks only. Keep match assets and derived results out of
Git and AI services. No blocked corporate download is retried or circumvented.
