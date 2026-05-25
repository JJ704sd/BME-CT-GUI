# Online Inference Follow-up Findings

## Established Evidence

- Latest pushed main commit: `838e77e merge selectable inference profiles`.
- Selectable inference profile work has been merged from `codex/update-ct-gui-prototype` into `main`; the old branch is no longer the active planning baseline.
- Fast no-cache run:
  - Run directory: `.test-output\perf-fast-profile-20260525-1305`
  - Job id: `6802e01f1a73`
  - Duration: `384.345s`
  - Main phase: `persistent_worker=381.448s`
  - Validation: `review`
  - Mean Dice: `0.777243`
  - Min Dice: `0.0`
  - Mean IoU: `0.713592`
  - Mean Hausdorff: `10.282058 mm`
  - Label 14/15 prediction voxels: `664 / 670`
- Quality no-cache run:
  - Run directory: `.test-output\perf-quality-profile-20260525-1330`
  - Job id: `b3c528cc9e20`
  - Duration: `1360.398s`
  - Main phase: `persistent_worker=1357.677s`
  - Validation: `passed`
  - Mean Dice: `0.924780`
  - Min Dice: `0.846569`
  - Mean IoU: `0.865088`
  - Mean Hausdorff: `7.716048 mm`
  - Label 14/15 prediction voxels: `0 / 0`

## Decisions

- `quality` is the default and official result path.
- `fast` is allowed only as a quick preview/demo path.
- Fast preview must be visibly marked as requiring review.
- Frontend job submission now sends `inference_profile` per job; backend environment variables remain fallback defaults.
- Effective `inference_options` are persisted through create response, job state, SSE complete event, `job_summary.json`, and cache key input.
- Label 14/15 small-volume false positives are a known fast-profile risk from the current AMOS 0117 comparison.
- Any filtering for label 14/15 must be documented as `postprocess`, not as raw model output.
- Do not claim a speed improvement unless it is tied to a recorded benchmark run with the same input, checkpoint, script, and cache state.

## Constraints

- Real CT/NIfTI/checkpoint/inference outputs stay local and ignored by git.
- `.test-output`, `nnunetv2_files`, and `server/work` must not be committed.
- Cache keys must include checkpoint identity and effective inference options.
- Legacy AMOS cache can be reused only when `job_summary.json` has a matching `cache_key`.

## Open Questions

- What minimum validation set is required before any label 14/15 postprocess filter can be enabled by default?
- Should warm-cache quality/fast timings be added as a separate comparison, or is no-cache still the only decision metric for first-run UX?
- Which non-AMOS local CT cases should be registered next for broader acceptance?
