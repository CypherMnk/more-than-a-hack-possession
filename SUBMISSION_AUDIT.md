# Submission audit - November 9, 2026

## Scope

Current V6 delivery, local inference, CSV handling, source provenance,
packaging, synthetic tests and repository privacy. No supplied-match label,
video, score or outcome-based parameter selection was used.
The older algorithms remain development snapshots, not the delivery entry.

## Fixed

| Issue | Resolution |
|---|---|
| V6 could replace a Python/source file via `--out` | Require a CSV extension; reject input, Git-metadata and dependency directories before reading data. |
| Packaging validated a path, then read it again | Validate and archive the same immutable byte snapshot. |
| A valid CSV filename did not prove which code produced it | Fresh inference from the exact source snapshot included in the delivery archive. |
| Only a custom CSV contract checker had been run | Add the pinned official format validator, with source-hash verification and no ground truth. |
| An interrupted/invalid preparation could replace a delivery | Stage privately; replace the final ZIP only after all checks succeed. |
| Third-party notices were absent from convenience bundles | Include the existing third-party licence and source provenance. |
| Redundant development-tool comment labels | Remove labels while retaining explanations, limitations and legal notices. No authorship claim is made. |

No distance, speed, timing, block or restart parameter was changed.
Comment cleanup does change source-file hashes; original saved archives retain
their original contents. A new delivery records its exact current source.

## Automated checks

- V1-V6 synthetic suites, including V6's missing-player motion veto and unsafe
  output rejection.
- Bundle allowlist, exact-byte validation, malformed/duplicate/blank rows,
  extracted-source tests, hashes, determinism and failure preservation.
- Full-length invented release input, pinned-validator integrity, fresh source
  provenance and preservation after invalid input/validator failures.
- External importer/scorer synthetic checks and separation of references from
  inference. These synthetic scores are not real football accuracy.
- Local delivery checks: CSV contract, pinned format validation, unchanged
  numerical V6 result, unchanged match inputs and preserved previous artifacts.
- Source-only Git allowlist and ignored assets, credentials and environments.

The reproducible commands are:

```powershell
python test_versions.py
& '.\.venv\Scripts\python.exe' test_external.py
& '.\.venv\Scripts\python.exe' test_submission.py
& '.\.venv\Scripts\python.exe' prepare_submission.py
```

Only the last command reads authorised local match inputs. It does not use
video, ground truth, external services or a trained model.
Delivery: `packages/v6_submission_candidate.zip`, including `possession.csv`.
Do not commit or share the ZIP/CSV with AI services.

## Remaining model risks

- In-pitch whistles and stoppages remain undetected.
- Co-motion/proximity are not proof of control. Missing opposition can make
  the distance-margin heuristic overconfident.
- 2D tracks omit ball height; jitter, missing slots and coherent wrong tracks
  can pass the guards.
- Weak phases can imply an incorrect team. The missing-player fast-motion
  veto can also suppress useful phase evidence.
- The placement/restart guard can delay a real kicked restart or mistake a
  moved placement for resumed play.
- Offline backdating uses future confirmation; it is not a live model.
- There is no real external score and no proof that V6 beats earlier versions.

These are disclosed limitations, not problems solved by format validation.
Further model changes require licensed external development/evaluation data,
not checking or tuning against the supplied match.

## Human readiness gates

The public repository was unreachable during this audit. Current delivery
requirements, deadline, team fields, ZIP acceptance and any assistance
disclosure cannot be confirmed from the live organiser documents.
Supply the public SUBMISSION.md and RULES.md, not restricted match assets,
to complete that review. The user's email clarification overrides older rules.

No AI-detector outcome is guaranteed. Readable code and removal of irrelevant
tool labels are not evidence of unassisted authorship. Do not make a false
authorship claim or omit a required disclosure. Preserve third-party credits.

Technical preparation does not constitute acceptance or an automatic submission.
No Git commit, remote, push or organiser upload is performed by these commands.
