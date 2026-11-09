# More than a Hack 2027 - Ball Possession

## About the hackathon

This is our project for Metrica Sports' **More than a Hack 2027**.

For the **Initial Challenge**, the task is to predict ball possession at each
frame of a football match: the home team, the away team, dead ball, or unknown.

We use automatic match data to generate those predictions. The current
algorithm does **not** use the video.

Official challenge: [Metrica Sports' repository](https://github.com/metrica-sports/more-than-a-hack-2027).
The organisers' email clarification takes priority over conflicting older rules.

## What data do we use?

The current version uses three files from the **Tactical** folder:

| File | What it contains |
|---|---|
| `BAR-ATH_tactical_atd.txt` | The ball's position and available players' positions at each frame. |
| `BAR-ATH_tactical_atd.xml` | Match information, including which player-tracking slots belong to each team. |
| `BAR-ATH_tactical_smart_tagging.xml` | Automatically detected phases of play, used as supporting information, not possession answers. |

A **frame** is one moment in the match. A **slot** is a player-tracking entry.
One frame can contain many player slots and one ball position. A slot is not
guaranteed to identify the same player throughout the match.

Video, Broadcast data and homography files are not used by this version.
The supplied match files are **not included in this repository**.

## What does the algorithm do?

**V6 is our current development version.** It uses fixed rules, not a trained
AI model:

In plain English, it asks: **"Who seems to control the ball, and has that
evidence lasted long enough to trust?"** Being the nearest player alone is
not enough.

1. Read the ball/player positions and match each player slot to a team.
2. Look for a player close to the ball, clearly closer than the opposing team's
   nearest player. Moving with the ball provides stronger evidence.
3. Check ball movement so a fast passing ball is not automatically treated as control.
4. Use automatic phases as weak support when tracking is unclear, but not when
   the observed movement or a close contest contradicts them.
5. Confirm changes over several frames instead of switching on every observation.
6. Filter implausible ball-position jumps and apply basic dead-ball/restart checks.

### Simple example

This example is invented, not taken from the supplied match:

- A home player is 1 metre from the ball; the nearest away player is 4 metres away.
  The home player and ball move together. After enough consecutive evidence,
  the algorithm labels this **home possession (`H`)**.
- The ball then passes quickly near an away player. That alone does not confirm
  a takeover, so the previous possession label is kept.
- The away player then stays close to the ball and moves with it. Once that
  evidence is confirmed, the label changes to **away possession (`A`)**.

When there is no usable evidence of a change, the algorithm keeps the last
confirmed label rather than immediately picking another team.
Before anything is confirmed, the label remains `X`.

A ball that stays clearly outside the pitch can produce `D`. After that, the
ball must return inside, move from its restart position and show confirmed
player control before the algorithm returns to `H` or `A`. This does not
detect every stoppage inside the pitch.

It works **offline**: later frames can confirm when a possession change started.
It is not a live prediction system, and V6 is **not proven more accurate** than
the earlier versions.

## What output do we get?

The algorithm creates `outputs/v6_control.csv` locally.

The CSV has two columns, `frame,label`, with one row per frame. Frame numbering
starts at zero.

| Label | Meaning |
|---|---|
| `H` | Home-team possession |
| `A` | Away-team possession |
| `D` | Dead ball / play stopped |
| `X` | Unknown, or outside the parts of the match being evaluated |

Predictions and submission archives stay local; they are not stored in Git.

## How to run it

You need **Python 3.10 or newer**. Inference and the version tests need no
additional packages. Run the commands below from the repository's root folder.

### 1. Add the input files

Download the authorised files separately and keep this folder layout:

```text
Tactical/
  BAR-ATH_tactical_atd.txt
  BAR-ATH_tactical_atd.xml
  BAR-ATH_tactical_smart_tagging.xml
```

### 2. Check the code

```powershell
python test_versions.py
```

These tests use invented data, so they work without the match files.
They check software behaviour, not football accuracy.

### 3. Generate V6 predictions

```powershell
python versions/v6_control/possession.py
```

This creates `outputs/v6_control.csv`. Input files are not modified.
Running it again replaces that version's output, not other versions' outputs.

If your input files are elsewhere:

```powershell
python versions/v6_control/possession.py --data-dir 'D:\authorised\Tactical'
```

**Use the V6 command above.** The root `possession.py` is the older V2 entry point.
Earlier versions are kept under `versions/` for comparison.

## Prepare a submission candidate

The packaging workflow also needs the packages listed in
`requirements-evaluation.txt` for the official CSV-format checker.
Use an approved environment; do not bypass blocked downloads.

In this workspace, the prepared environment is `.venv`:

```powershell
& '.\.venv\Scripts\python.exe' test_submission.py
& '.\.venv\Scripts\python.exe' prepare_submission.py
```

This creates the private archive `packages/v6_submission_candidate.zip`, containing:

- The generated possession CSV.
- The exact code and tests used to produce it.
- A method note, third-party notices and a verification manifest.

The workflow tests and runs the code it packages, then checks the CSV format.
**It does not measure accuracy or submit anything.** Confirm the organisers'
current required files and submission format; do not assume they accept a ZIP.

## Rules and limitations

- You may inspect the supplied data/video to understand possession, but must not
  check predictions against the video or tune the algorithm using it.
- Do not create manual labels or corrections for the supplied match.
- Do not upload supplied match data or derived results to AI services.
- Train or tune only on external data you have the right to use, not on the
  supplied match, its video or possession ground truth.
- Keep match inputs, predictions, archives, screenshots and secrets out of Git.
- Use local automatic checks for technical correctness.

There is **no real accuracy score yet**. Being near the ball does not always
mean control, missing or incorrect tracking can cause mistakes, and stoppages
inside the pitch may be missed. Parameters remain fixed and unvalidated.

## Further details

- [V6 method and limitations](MODEL_CARD_V6.md)
- [External accuracy testing](EXTERNAL_EVALUATION.md)
- [Submission checklist](SUBMISSION_CHECKLIST.md)
- [Technical audit](SUBMISSION_AUDIT.md)
- Third-party evaluation code retains its licence and source information in `evaluation_tools/`.
