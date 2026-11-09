# Local tracking + Smart Tagging possession prototype

## Start here: source-only repository and V6 candidate

Python 3.10+; no installation or network is needed for inference or synthetic
algorithm/package tests. From the repository root:

```powershell
python test_versions.py
python versions/v6_control/possession.py
python prepare_candidate.py --version v6_control
```

The second command expects the authorised files under the local `Tactical`
folder and creates `outputs/v6_control.csv`. The third creates the private
`packages/v6_candidate.zip`. On a different machine, obtain the input assets
separately; for another input location, pass `--data-dir 'D:\authorised\Tactical'`.

**V6 is the latest engineering candidate, not a proven accuracy winner.**
Its only algorithm change is preserving the existing motion veto when every
player observation is missing. Thresholds are unchanged; see `MODEL_CARD_V6.md`.
The root `possession.py` remains the older V2 entry point, not V6.

### Prepare the reviewed delivery

Use the existing evaluation environment for the pinned official CSV-format
validator; the inference algorithm itself still has no third-party dependencies:

```powershell
& '.\.venv\Scripts\python.exe' test_submission.py
& '.\.venv\Scripts\python.exe' prepare_submission.py
```

This creates `packages/v6_submission_candidate.zip`. It runs fresh inference
from the exact source snapshot in the bundle, tests that snapshot, validates
CSV format with the pinned official validator (no possession references), and
records those checks in the manifest. Unlike convenience packaging, it does not
trust an earlier CSV merely because its filename says V6.
Failures preserve the previous delivery archive. Existing candidate ZIPs and
outputs are not replaced. The CSV, method note and code are inside the new ZIP;
extract individual deliverables if required by the organisers.

Read `SUBMISSION_AUDIT.md` for the checked scope and unresolved readiness gates.
This is technical preparation, not verified portal acceptance, an accuracy
claim, or an automatic submission.

Only source, synthetic tests, documentation and the licensed public evaluation
tool belong in Git. Match inputs, outputs, candidate archives, external data,
screenshots, secrets and virtual environments stay local and ignored.
Never force-add restricted files. A CSV is generated locally, not stored in
the source repository. This repository is not an automatic submission.
Follow `SUBMISSION_CHECKLIST.md` before publishing code or submitting results.

## External accuracy testing

See `C:\More than a hack\EXTERNAL_EVALUATION.md` for the licensed IDSSE dataset,
required external files, commands, and limitations. **External downloads and
accuracy testing on this corporate laptop are paused at the user's request.
Do not retry or bypass blocked downloads.** Accuracy testing will happen
elsewhere; no real accuracy score exists.

## Saved algorithm versions

Saved versions never import the evolving root algorithm. V1/V2 are standalone;
V3 reuses frozen V2 input/output helpers; V4 also reuses V3's temporal rules.
Keep all version folders.
Keep saved versions unchanged; create a new version for future algorithm changes.

| Version | Method | Default output |
|---|---|---|
| v1_tracking | Tracking only | `C:\More than a hack\outputs\v1_tracking.csv` |
| v2_tagged | Tracking + Smart Tagging fallback | `C:\More than a hack\outputs\v2_tagged.csv` |
| v3_temporal | Tagging + offline transition timing + dead-state guard | `C:\More than a hack\outputs\v3_temporal.csv` |
| v4_ball_guard | V3 + ball-position jump guard | `C:\More than a hack\outputs\v4_ball_guard.csv` |
| v5_control | Motion-aware control + evidence-specific timing + placement/restart guard | `C:\More than a hack\outputs\v5_control.csv` |
| v6_control | V5 + motion veto retained when all player observations are missing | `C:\More than a hack\outputs\v6_control.csv` |

```powershell
python 'C:\More than a hack\test_versions.py'
python 'C:\More than a hack\versions\v1_tracking\possession.py'
python 'C:\More than a hack\versions\v2_tagged\possession.py'
python 'C:\More than a hack\versions\v3_temporal\possession.py'
python 'C:\More than a hack\versions\v4_ball_guard\possession.py'
python 'C:\More than a hack\versions\v5_control\possession.py'
python 'C:\More than a hack\versions\v6_control\possession.py'
```

Each run replaces only its own default output, leaving other versions and earlier
prototype outputs untouched. Keep parameter defaults unchanged for these outputs;
if using external-data parameters, give that run a separate `--out` path.
The v1 snapshot retains unused tagging helpers so the same synthetic suite can
check both snapshots; its execution path is fixed to tracking only.
Versioning does not establish which method is more accurate. Do not select or
tune versions by checking predictions against the competition video/ground truth.

### What is new in V6

- V5 could discard observed ball motion when no players were visible and let a
  weak tag change the established team. V6 checks ball motion before that return.
- Observed fast in-pitch ball motion now vetoes tags even without players.
  Missing/stationary motion still permits the existing weak fallback.
- No threshold changes, new assets, dependencies, training or match tuning.
  The fix and its effect reproduce on invented cases only.
- Shared V5 tests run against V6 too. The external harness includes frozen V6
  tracking-only inference; full tag-enabled V6 accuracy is still untested.
- Separate outputs and candidate archives preserve V5. `--tracking-only`
  defaults to `outputs/v6_tracking_only.csv`.

This is a software consistency fix, not proof that fast motion means a pass
or that V6 is more accurate. It does not solve in-pitch stoppages.

### What is new in V3

- Still requires one second of consecutive evidence, with the same 2 m radius
  and >0.5 m team-distance margin. None were tuned on the provided match.
- After a change is confirmed, the saved labels start at the first frame of the
  confirming streak, not at its last frame. This removes the deliberate confirmation
  delay from the offline CSV; it does **not** prove the true transition time.
- Short unconfirmed opposing touches are still ignored. Missing or conflicting
  evidence resets a pending streak; V3 does not backdate across those gaps.
- Once the state is D, tactical phases alone cannot restart play. A return to H/A
  requires a full streak of tracking control evidence. This reduces one mechanism
  for false restarts, but may extend D when the ball is occluded at a real restart.
- Outside-half frames remain X; neither state nor retrospective labels cross halves.
- This uses offline future confirmation, not a live/real-time prediction model.
- In-pitch stoppages and whistle detection are still missing. Outside-pitch tracking
  errors can still cause false D states. V3 is not proven more accurate than V2.

No new assets, network access, dependencies, or accuracy scoring are needed.
The root `C:\More than a hack\possession.py` remains the V2 development entry;
run the explicit version command above for newer behaviour.

### What is new in V4

- Checks ball displacement in metres against elapsed time at 25 fps, using a
  **60 m/s arbitrary, unvalidated ceiling** (2.4 m per frame). This is a generous
  engineering assumption, not an established physical bound or a measured value.
  Freeze it for this match; `--max-ball-speed` is for external-data tuning only.
- Rejects implausible jumps before they reach V3's state machine. At those frames,
  neither tracking nor Smart Tagging can provide new possession/dead-ball evidence.
  V3 keeps the previous state and resets pending confirmation; rejected coordinates
  are not replaced with invented positions.
- Missing ball observations still allow V3's tagging fallback. Elapsed time since
  the last accepted ball observation is used when checking a return after a gap.
- A second consecutive, mutually plausible ball observation can reacquire a
  relocated track, so a jump does not cause permanent rejection. A sustained wrong
  track can also pass this rule; this is not a full tracking-error correction model.
- Resets motion history between halves. Plausible boundary crossings still supply
  D evidence; timing, dead-state guard, and other V3 defaults remain unchanged.
- Uses the same three input files. No new dependencies, downloads, training, match
  statistics, intermediate match files, video comparisons, or accuracy scoring.
- Can reject a genuine fast movement or delay a real restart/turnover. It does not
  fix in-pitch stoppages or prove V4 is more accurate than V3.

Implementation: `C:\More than a hack\versions\v4_ball_guard\possession.py`.
Synthetic checks: `C:\More than a hack\test_v4.py`, included in the version runner.

### Combined next-step candidate: V5

V5 reuses frozen V2 parsing primitives, team mapping, automatic tag parsing and
atomic CSV writing. It needs neither V3 nor V4 at runtime; those versions remain
unchanged. Its new record parser validates the same layout but makes full player
positions available for motion analysis in one pass.

- **Control versus passing contact:** derive ball/player velocities from consecutive
  positions at 25 fps. A nearby player co-moving with the ball provides stronger
  control evidence; excessive relative speed supplies no control evidence. Missing
  frames, rejected ball jumps and implausible player-slot motion break derivatives.
- **Evidence-specific confirmation:** require 0.2 s of consecutive co-motion,
  1 s of proximity or boundary evidence, or 2 s of weak automatic phases.
  These are **ordinal support categories, not calibrated probabilities**.
  Changing the required duration resets a pending streak, so one strong frame
  cannot retroactively upgrade earlier weak evidence.
- **Conservative tag fusion:** phases can support missing/ambiguous observations,
  but cannot override observed flight, a close contest, or a rejected ball jump.
- **Boundary/restart handling:** outside-pitch observations must exceed a 0.25 m
  margin and persist. Once D is established, phases cannot restart play. On a
  trusted return inside the pitch, save a placement reference and require at
  least 1 m of subsequent observed displacement plus confirmed tracking control.
  A stationary ball placed next to a player is not enough.
- Same offline onset backdating, X outside grading blocks and half resets.
  No interpolation, manually corrected tracklets, provided-video checks or training.

Every new number is an **arbitrary, unvalidated starting assumption**, chosen
without inspecting this match's outcomes. Defaults are frozen for this match.
External tuning uses the evaluator's JSON settings, never supplied-match feedback.
Tracking-only CLI runs default to a separate
`C:\More than a hack\outputs\v5_tracking_only.csv`, not the full V5 result.

Important ceilings: 2D co-motion can confuse a duel with control; derivatives can
amplify tracking jitter. A stationary in-pitch ball is NOT sufficient to declare
D. In-pitch whistles/stoppages are still not detected. The restart guard can delay
real kicked restarts until observable tracking control returns. A moved placement
or sustained wrong track can also pass it. **V5 is not proven better than V1-V4.**

The external evaluator now compares tracking-only modes of V1-V5, four V5
feature-removal tests, and optional fixed synthetic faults on EXTERNAL tracking.
It does not pretend missing external Smart Tagging is available or use possession
reference labels as tags. See `C:\More than a hack\EXTERNAL_EVALUATION.md`.

Method note: `C:\More than a hack\MODEL_CARD.md`.
After generating V5, prepare a private local convenience bundle:

```powershell
python 'C:\More than a hack\prepare_candidate.py'
```

This creates `C:\More than a hack\packages\v5_candidate.zip`, with the result CSV,
required source files, synthetic V5 checks, method note and hash manifest.
It contains no provided input files, external reference labels or credentials.
**It is an unscored candidate, not a best-version selection or an automatic
submission.** Keep it private; extract/upload deliverables separately if the
organisers require that rather than accepting an archive.

Python 3.10+; standard library only. No installation, model training, video,
network access, or ground-truth scoring is needed by the implementation.

## Run in PowerShell

```powershell
Set-Location 'C:\More than a hack'
python 'C:\More than a hack\test_possession.py'
python 'C:\More than a hack\possession.py'
```

Inputs are `C:\More than a hack\Tactical\BAR-ATH_tactical_atd.xml` and
`C:\More than a hack\Tactical\BAR-ATH_tactical_atd.txt`, plus
`C:\More than a hack\Tactical\BAR-ATH_tactical_smart_tagging.xml`.
Output is `C:\More than a hack\outputs\prototype_tagged.csv`.
The earlier `C:\More than a hack\outputs\prototype.csv` is preserved.
To regenerate the tracking-only version, use:

```powershell
python 'C:\More than a hack\possession.py' --tracking-only
```

Input files are never modified. Only a completion/format status is printed;
tracking rows, predicted labels, and match statistics are not printed.

## What the root/V2 version does

- Validates tracking IDs are consecutive, one-based, and cover the full timeline.
- Reads team membership using the public starter's metadata/slot convention.
- Scales normalized positions by the public pitch dimensions before measuring distance.
- Considers a team a control candidate when its nearest player is within 2 m of
  the ball and more than 0.5 m closer than the opposing team's nearest player.
- Reads automatic tactical tag intervals with the public seconds-to-frames
  conversion, rounding at 25 fps and treating the end as exclusive.
- Offensive phases support their named team; defensive-third phases support
  the opposing team. Public tag spellings map Barcelona to H and
  Atletic Club/Athletic Club to A; this mapping is specific to this match.
- Conflicting tag evidence is X, not a majority vote. Unknown teams, set pieces,
  goals, player-count tags, and defensive transitions provide no evidence.
- Uses tags only when tracking evidence is X. Tracking H/A/D takes precedence.
- Requires 1 second of consecutive candidate evidence to change state.
- Keeps the previous state if neither tracking nor tags provides evidence.
- Uses sustained out-of-pitch ball coordinates as a crude dead-ball candidate.
- Resets state between the public grading blocks and outputs X outside them.
- Writes a full CSV atomically after validating its format.

The parameters above are **arbitrary, unvalidated starting defaults**, not
parameters selected from this match, ground truth, or video. Freeze them for
this match; tune them only on permitted external data. CLI parameters exist
for future external-data development, not competition-match optimization.

## Important limitations

This is an engineering prototype, **not a competition-ready or accuracy-tested
solution**. Proximity is not proof of controlled possession. Missing observations
break the confirmation streak. V1/V2 delay changes by their confirmation window;
V3-V6 backdate confirmed streaks, without proving the true transition times.
Boundary projection errors can create false D labels. In-pitch stoppages,
whistles, and exact restarts are not detected. Automatic phases may straddle a
stoppage or turnover: a tag may create a false possession or restart when tracking
is missing. This fallback is unvalidated, not an established accuracy improvement.
Tag intervals are used offline and are not a real-time causal input.
Homography remains unused. No intermediate tracking is exported.

Synthetic checks verify intended code behavior, not real football accuracy.
The format check implements the strict documented CSV contract; it is not a
claim that the official scorer was executed.

## Privacy and competition rules

Keep Tactical, data, and outputs private. `.gitignore` helps prevent accidental
commits but does not protect uploads or already tracked files. Never share match
files, derived tracking, screenshots, or prediction/video comparisons with AI
services. Do not train, calibrate, or tune on this match, its video, or its
ground truth. Follow the organisers' clarification over older repository rules.

## Public references used to implement the format

- https://github.com/metrica-sports/more-than-a-hack-2027/blob/main/starter/baseline.py
- https://github.com/metrica-sports/more-than-a-hack-2027/blob/main/starter/load_atd.py
- https://github.com/metrica-sports/more-than-a-hack-2027/blob/main/starter/load_smart_tagging.py
- https://github.com/metrica-sports/more-than-a-hack-2027/blob/main/DATA.md

The inference implementation uses these public input contracts. The separate
external evaluator reuses the official MIT-licensed metrics, with original
license and pinned-source provenance in `C:\More than a hack\evaluation_tools`.
