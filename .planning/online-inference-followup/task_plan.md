# Online Inference Follow-up Plan

**Scope:** Track the next round of online inference product work after the 2026-05-25 fast vs quality comparison.

**Current branch:** `codex/update-ct-gui-prototype`

**Current baseline:** commit `ed5cf86 docs: record quality inference comparison`

**Primary rule:** `quality` remains the default and official report path. `fast` is only a quick preview path and must be visibly marked as needing review.

## Status

- [x] Record fast vs quality no-cache baseline in `REVIEW.md`.
- [x] Record benchmark metrics in `SEGMENTATION_METRICS_SUMMARY.md`.
- [x] Push baseline documentation to `origin/codex/update-ct-gui-prototype`.
- [ ] Add user-visible inference mode selection.
- [ ] Carry selected inference profile through the API/job state/result summary.
- [ ] Show a clear "needs review" warning for fast preview results.
- [ ] Re-run focused verification after UI/backend profile plumbing.
- [ ] Update `README.md`, `REVIEW.md`, and `SEGMENTATION_METRICS_SUMMARY.md` after implementation.
- [ ] Commit and push the follow-up work.

## Phase 1: Product Mode Selection

Goal: make the quality/fast distinction explicit in the product instead of relying only on process environment variables.

Tasks:

- [ ] Inspect current job creation UI and backend request schema.
- [ ] Add a mode control with two choices: `quality` and `fast`.
- [ ] Default to `quality`.
- [ ] Label `fast` as quick preview only and requiring review.
- [ ] Persist selected profile in job state and `job_summary.json`.
- [ ] Ensure cache key still includes the effective inference options.

Acceptance checks:

- [ ] A default submission uses `quality`.
- [ ] A fast preview submission uses `fast`, `tile_step_size=1.0`, and TTA disabled unless explicitly overridden by backend config.
- [ ] Fast results cannot be mistaken for official quality results in the UI or job summary.

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

## Phase 4: Final Verification and Handoff

Tasks:

- [ ] Run `npm --prefix 'D:\BME2026\BME_CT_Seg\segmentation-gui-prototype' test`.
- [ ] Run `npm --prefix 'D:\BME2026\BME_CT_Seg\segmentation-gui-prototype' run build`.
- [ ] If inference behavior changes, run at least a dry-run benchmark command and document the exact output expectation.
- [ ] Check `git status --short`.
- [ ] Commit with a focused message.
- [ ] Push to `origin/codex/update-ct-gui-prototype`.
