# V5 possession candidate — method note

## Status

Deterministic offline heuristic. No learned model or calibrated probabilities.
Synthetic software checks and CSV checks are separate from real accuracy:
**no real external score or competition accuracy result is available**.
V5 has not been selected as the most accurate version.

## Inputs and output

- Tactical automatic tracking TXT: one-based consecutive records with player-slot
  and ball normalized x/y positions, plus speed fields.
- Tactical metadata XML: player-slot/team mapping.
- Tactical automatic Smart Tagging XML: optional weak phase evidence.
- Pitch dimensions 105.3 by 68 m; tactical timeline 25 fps.
- Output: 199,319 zero-based `frame,label` rows; labels H/A/D/X.
- Public inclusive grading blocks: 11185–90651 and 110808–190197.
  Output X outside blocks; neither motion nor possession state crosses halves.
- Broadcast, homography, video, audio and reference possession labels are unused.

## Method

1. Validate every player/ball record and convert finite positions to metres.
   Missing observations remain missing. Report errors without source contents.
2. Reject ball jumps inconsistent with a fixed speed ceiling. Elapsed time is
   respected across gaps; a coherent raw pair can reacquire a relocated track.
3. Find convincing nearest-team evidence using distance and an opposing-team
   distance margin. When consecutive motion is usable, compare player and ball
   velocities. Excessive relative speed provides no control evidence, rather than
   transferring possession merely because an opponent is nearest.
4. Use weaker automatic phase evidence only when tracking is missing/ambiguous,
   never to override an observed contest, flight, or rejected jump.
5. Confirm co-motion, proximity, phases and boundary evidence for different
   fixed durations. Confirmed labels start at the streak onset. Unknown evidence
   or a duration change resets the pending streak; no backdating across gaps.
6. Sustained clearly outside-pitch positions can establish D. To exit D, phases
   alone are insufficient: require confirmed tracking control and movement from
   an observed in-pitch placement. Do not infer D merely from a stationary ball.
7. Validate a temporary result CSV before atomic replacement of the output.

## Frozen assumptions

| Parameter | Default |
|---|---:|
| Control radius / team margin | 2 m / 0.5 m |
| Ball jump ceiling / player derivative ceiling | 60 m/s / 15 m/s |
| Relative control speed ceiling | 3 m/s |
| Outside-pitch margin | 0.25 m |
| Co-motion / proximity confirmation | 0.2 s / 1 s |
| Phase / boundary confirmation | 2 s / 1 s |
| Observed displacement after in-pitch placement | 1 m |

All are arbitrary, unvalidated engineering assumptions, not physical guarantees,
learned probabilities or parameters fitted to the supplied match.

## Reproduce

Python 3.10+; standard library only. From the extracted source root:

```text
python test_v5.py
python versions/v5_control/possession.py --data-dir /path/to/Tactical --out regenerated.csv
```

Required runtime code: `versions/v5_control/possession.py` and frozen
`versions/v2_tagged/possession.py`. Input assets must be obtained independently;
they are not included in the private candidate archive.

## Evaluation plan and remaining work

The separate external harness can compare tracking-only V1-V5 modes, remove each
V5 feature in turn, and add one reproducible synthetic-fault condition. It uses
the official metric implementation with licence/provenance retained in the
workspace. Compatible automatic tags are absent from the prepared IDSSE source;
therefore full tag-enabled V2-V5 accuracy is explicitly untested.

Real external testing is deferred to an approved environment. Tune only on
external development matches; keep different external matches untouched for
evaluation. Provider possession definitions and tracking quality may differ.
Fill in measured external results before claiming an accuracy improvement.

## Limitations and compliance

Co-motion is not proof of control; 2D tracks do not describe ball height.
Jitter and slot changes can corrupt derivatives. Sustained tracking errors may
pass reacquisition. Automatic phases can still imply an incorrect team.
The restart guard may prolong D through a genuine kicked restart; moved
placements can imitate a restart. In-pitch whistles/stoppages remain undetected.
Offline onset assignment uses future confirmation; this is not a live model.

The supplied match was not used for training, fitting, calibration, parameter
selection, hand labels or video/output comparison. Only local inference and
automatic technical checks are performed. Match inputs and derived outputs must
not be uploaded to AI services. No blocked corporate download is retried.
