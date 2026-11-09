# Testing, repository and submission checklist

## 1. Keep the repository source-only

Include code, invented test cases, docs, evaluation dependency requirements,
and the public metric's existing licence/provenance.

Do not include Tactical/Broadcast data, video, screenshots, external dataset
files, possession outputs, result archives, local environment files or secrets.
`.gitignore` includes those folders and common asset formats, including copies
outside their usual folders. It does not protect uploads, force-added files,
previous history, or data pasted into source code.

Before any commit/push, inspect `git status --short` and `git ls-files`.
Only the intended source/documentation allowlist should appear.
Choose code ownership/licensing and repository visibility before publication.
The local repository has no automatic commit, push, remote or submission step.
GitHub publication requires separate approval.
Irrelevant development-tool labels were removed from comments, not licensing
or technical explanations. There is no guarantee about AI-detector results and
no claim of unassisted authorship. Follow any required assistance disclosure.

## 2. Run tests without match data

From the repository root, using Python 3.10+:

```powershell
python test_versions.py
```

This runs V1-V6 synthetic parser/algorithm tests and V5/V6 packaging checks.
It works without Tactical, outputs, archives, an external dataset or a venv.
Inference and these tests use only the Python standard library.

For the external importer/scorer's synthetic tests, use the separately prepared
environment containing numpy/pandas:

```powershell
& '.\.venv\Scripts\python.exe' test_external.py
```

On this corporate laptop the dependencies already exist. Do not retry blocked
downloads or install workaround tools. Set up another approved machine for
real external evaluation; see `EXTERNAL_EVALUATION.md`.

Synthetic pass/fail verifies software behaviour, not football accuracy.

## 3. Generate the reviewed delivery locally

Obtain the authorised match assets separately. Keep the filenames:

- `BAR-ATH_tactical_atd.txt`
- `BAR-ATH_tactical_atd.xml`
- `BAR-ATH_tactical_smart_tagging.xml`

Then run:

```powershell
& '.\.venv\Scripts\python.exe' test_submission.py
& '.\.venv\Scripts\python.exe' prepare_submission.py --data-dir 'D:\authorised\Tactical'
```

Use the actual local input path in place of the example.
Omit `--data-dir` when inputs are in the repository's local Tactical folder.

Private reviewed bundle: `packages/v6_submission_candidate.zip`.
It contains `possession.csv`, required code/tests, the method note, third-party
licence/provenance and a hash/verification manifest. No input assets are bundled.
The workflow tests and runs its exact bundled source using frozen defaults,
then checks format with the pinned official validator. It does not load ground
truth, produce accuracy scores, or upload/submit anything.
Extract individual deliverables if the organiser requires separate files.
Keep the archive and CSV out of Git and AI services.
The older `outputs/v6_control.csv`, `packages/v6_candidate.zip`, V5 commands and
saved archives remain unchanged; earlier ZIPs are convenience snapshots.
Do not relabel an arbitrary CSV as V6 instead of using fresh generation.

## 4. Accuracy gate: external only

- No prediction/video checking, manual labels or tuning on the supplied match.
- Do not send supplied inputs or derived results to AI services.
- Tune only on licensed external development data; evaluate on different
  untouched external matches before making generalisation claims.
- The external harness includes V6 tracking-only. It cannot evaluate full
  Smart Tagging support without compatible automatic external tags.
- Existing `--v5-params` affects V5 only. V6 runs frozen defaults.
- No real score is currently available; do not call V6 "more accurate."

## 5. Human submission review

- Confirm the organisers' current delivery format, required files, deadline and
  team details. This checklist does not assert that ZIP submission is accepted.
- Use the organiser-designated channel, not a public code repository or AI chat,
  for the result CSV and any permitted private artifacts.
- The documented CSV contract is header `frame,label`, consecutive frames
  0-199318, H/A/D/X labels and X outside active blocks. The delivery builder checks
  this contract and runs the pinned official format validator. This is not a
  claim that the latest online validator or submission portal was accessed.
- Include honest method/status notes: deterministic offline heuristic, frozen
  assumptions, no external accuracy result, and remaining in-pitch stoppage and
  restart limitations.
- Retain the exact code, result and private bundle used for submission locally.
  Packaging hashes record that bundle's contents; do not post them to AI services.
- Submit only after explicit human review. No code here contacts the organisers.
- The public repository was unreachable during the November 9, 2026 audit.
  Confirm the current public SUBMISSION.md and RULES.md, including any assistance
  disclosure requirement. The supplied clarification remains authoritative over
  older/conflicting statements.
