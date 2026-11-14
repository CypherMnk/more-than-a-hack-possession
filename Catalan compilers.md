# Catalan compilers
## More than a Hack 2027: Initial Challenge technical document

### 1. Approach and motivation

We predict team possession using **V6**, a deterministic, offline algorithm
based on automatic player/ball tracking and automatic phases of play.
The output labels are home possession (`H`), away possession (`A`), dead ball
(`D`) and unknown/outside the evaluated timeline (`X`).

We chose explicit control rules because the provided automatic positions can
be processed directly, the method runs locally without trained weights or
hosted APIs, and every decision can be reproduced from the code. This is a
transparent starting approach, not a claim that fixed rules outperform
learned models.

AI coding assistance supported implementation and documentation. It is not
a runtime component: possession labels are produced by local deterministic
code, not by an LLM or a human annotator.

### 2. Assets used

| Asset | Use |
|---|---|
| `BAR-ATH_tactical_atd.txt` | Available player-slot and ball positions at each frame. |
| `BAR-ATH_tactical_atd.xml` | Team membership of tracking slots and input metadata. |
| `BAR-ATH_tactical_smart_tagging.xml` | Automatic phases, used only as weak supporting evidence. |

Positions are scaled to metres using the documented 105.3 by 68 metre pitch.
Consecutive positions supply movement estimates at 25 frames per second.
The parsed speed fields are not used. A tracking slot is not assumed to be
a permanent player identity.

The video, Broadcast tracking, homography and audio are unused. They were
not alternative inputs evaluated and selected against possession outcomes.
No manual tracking corrections, possession annotations or human-produced
event data from the supplied match enter the algorithm.

### 3. Algorithm and possession rules

1. **Validate the inputs.** Require the expected record layout and timeline.
   Missing observations remain missing; we do not interpolate or invent positions.
2. **Find a control candidate.** Compare each team's nearest observed player
   with the ball. A player must be close and clearly closer than the nearest
   opponent. Player/ball co-motion provides stronger evidence than proximity alone.
3. **Handle loose balls and challenges.** Excessive relative ball/player motion
   does not establish control. Close opposing players produce contested evidence.
   Without a confirmed change, retain the previous label; initially this is `X`.
   A fleeting contact therefore need not create a possession change.
4. **Use tags conservatively.** Automatic phases can support missing or ambiguous
   tracking, but cannot override observed flight, a close contest or a rejected
   position jump. Tags are not possession ground truth.
5. **Confirm changes.** Require consecutive evidence, with shorter confirmation
   for co-motion than for proximity or weak phases. Missing/conflicting evidence
   resets a pending change. Once confirmed, backdate the change to the start of
   its confirming streak. This uses future confirmation and is not a live system.
6. **Handle boundaries and restarts.** Sustained, clearly outside-pitch ball
   observations can establish `D`. To leave `D`, require an observed return
   inside, movement from the restart placement and confirmed tracking control.
   Phases alone cannot restart play.
7. **Reject implausible jumps.** A fixed displacement/time guard filters ball
   jumps. A coherent pair of subsequent observations can reacquire a relocated
   track. Motion history resets after gaps/rejections and between halves.

V6 preserves the fast-ball veto even when all player observations are missing.
This prevents that case from falling through to a weak phase-based change.
It does not prove that a fast ball is uncontrolled.

The CSV uses the documented zero-based timeline, with 199,319 data rows.
Frames outside the documented active blocks are `X`; state and motion do not
cross the half boundary.

### 4. Training data and fixed assumptions

**No model training, fitting or calibration was performed. No labelled dataset
was used to train a model or tune these parameters.** In particular, neither
the supplied video nor possession ground truth was used for that purpose.

Manually specified synthetic examples are invented software tests, not labels
for the supplied game and not training data. The external IDSSE evaluation
harness is separate; no external accuracy result or external-data parameter
selection is claimed for this submission.

| Assumption | Fixed value |
|---|---:|
| Control radius / opposing-team distance margin | 2 m / 0.5 m |
| Ball-jump / player-motion ceilings | 60 m/s / 15 m/s |
| Relative control-speed ceiling | 3 m/s |
| Outside-pitch margin | 0.25 m |
| Co-motion / proximity confirmation | 0.2 s / 1 s |
| Automatic-phase / boundary confirmation | 2 s / 1 s |
| Displacement after restart placement | 1 m |

These are arbitrary, unvalidated engineering assumptions, unchanged from V5.
They are not calibrated probabilities, measured match parameters or physical
guarantees. V6 was not selected as an accuracy winner.

### 5. Checks and limitations

Synthetic tests cover parsing, missing observations, contests, motion guards,
confirmation timing, half resets, restarts, CSV writing and reproducibility.
The release workflow runs the exact source snapshot it packages. CSV-format
checks do not assess whether possession labels are correct.

Important limitations:

- Proximity and 2D co-motion are not proof of controlled possession; ball height
  is unavailable.
- Missing opponents, tracking jitter, slot changes and coherent wrong tracks
  can create incorrect control evidence.
- Retaining the previous team through uncertainty can extend a wrong possession.
- Weak automatic phases can span real turnovers or stoppages.
- In-pitch whistles and stoppages are not detected.
- Restart checks can delay a genuine restart until control becomes observable.
- Backdating a confirmed streak does not establish the true transition time.

With more time, we would evaluate these assumptions on licensed external
development matches and test changes on different held-out matches. We would
not use supplied-match outcomes to tune them.

### 6. Reproduction

Repository: https://github.com/CypherMnk/more-than-a-hack-possession

Inference needs Python 3.10 or newer and **only the standard library**; no
weights, proprietary models or additional pip packages are required.
The submission release is checked with CPython 3.14.3.

Obtain the authorised data separately. From the repository root:

```text
python test_versions.py
python versions/v6_control/possession.py --data-dir "/path/to/Tactical" --out "outputs/Catalan compilers.csv"
```

Replace `/path/to/Tactical` with the folder containing the three named input
files. Keep the version and parameter defaults unchanged. The generated CSV
is the submission file; renaming/copying it must not alter its contents.
Input files are never modified.

The optional release/format-validation environment uses the pinned packages
in `requirements-evaluation.txt`. `prepare_submission.py` tests and runs a
source snapshot and builds a private code/result archive. It does not submit
anything or load possession reference labels.

The official MIT-licensed metric code retains its licence and pinned source
information under `evaluation_tools/`. It is used for technical format checks,
not supplied-match accuracy scoring. Match assets and derived results are
excluded from the public repository.
