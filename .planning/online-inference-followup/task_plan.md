# Online Inference Follow-up Plan

**Scope:** Track the next round of online inference product work after the 2026-05-25 fast vs quality comparison.

**Current branch:** `main`

**Current baseline:** commit `838e77e merge selectable inference profiles`

**Primary rule:** `quality` remains the default and official report path. `fast` is only a quick preview path and must be visibly marked as needing review.

## Status

- [x] Record fast vs quality no-cache baseline in `REVIEW.md`.
- [x] Record benchmark metrics in `SEGMENTATION_METRICS_SUMMARY.md`.
- [x] Push baseline documentation to `origin/codex/update-ct-gui-prototype`.
- [x] Add user-visible inference mode selection.
- [x] Carry selected inference profile through the API/job state/result summary.
- [x] Show a clear "needs review" warning for fast preview results.
- [x] Re-run focused verification after UI/backend profile plumbing.
- [x] Update `README.md`, `REVIEW.md`, and `SEGMENTATION_METRICS_SUMMARY.md` after implementation.
- [x] Merge and push the selectable inference profile follow-up to `origin/main`.

## Phase 1: Product Mode Selection

Goal: make the quality/fast distinction explicit in the product instead of relying only on process environment variables.

Tasks:

- [x] Inspect current job creation UI and backend request schema.
- [x] Add a mode control with two choices: `quality` and `fast`.
- [x] Default to `quality`.
- [x] Label `fast` as quick preview only and requiring review.
- [x] Persist selected profile in job state and `job_summary.json`.
- [x] Ensure cache key still includes the effective inference options.

Acceptance checks:

- [x] A default submission uses `quality`.
- [x] A fast preview submission uses `fast`, `tile_step_size=1.0`, and TTA disabled unless explicitly overridden by backend config.
- [x] Fast results cannot be mistaken for official quality results in the UI or job summary.

## Phase 2: Benchmark Discipline

Goal: keep future speed claims tied to reproducible measurements.

Tasks:

- [ ] Keep benchmark runs under `.test-output/`.
- [ ] For every benchmark, record input, checkpoint, profile, tile step, TTA state, cache state, job id, total duration, phase timings, result size, resource snapshot, and validation status.
- [ ] For reference cases with labels, record Dice, IoU, Hausdorff, and label 14/15 prediction voxel counts.
- [ ] Separate raw model metrics from any postprocess metrics.

Acceptance checks:

- [ ] `REVIEW.md` contains the decision-level conclusion.
- [ ] `SEGMENTATION_METRICS_SUMMARY.md` contains the numeric comparison.
- [ ] README only contains current user-facing usage, not the full experiment log.

## Phase 3: Postprocess Experiment Gate

Goal: investigate label 14/15 false positives only as an explicit postprocess experiment.

Tasks:

- [ ] Design a small-volume connected-component filter for absent or tiny labels.
- [ ] Run it against the existing fast output with label 14/15 false positives.
- [ ] Report both raw and postprocess metrics.
- [ ] Do not replace raw model quality metrics with filtered metrics.

Acceptance checks:

- [ ] Postprocess output is labeled separately.
- [ ] Raw fast metrics remain visible in documentation.
- [ ] No product default changes until the filter is validated on more than one case.

## Phase 4: Main Baseline Verification

Tasks:

- [x] Run `npm test` from the project root.
- [x] Run `npm run build` from the project root.
- [x] Check `git status --short`.
- [x] Record the verified `main` baseline in `progress.md`.
