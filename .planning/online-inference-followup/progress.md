# Online Inference Follow-up Progress

## 2026-05-25

- Created planning tracker for the next online inference follow-up round.
- Confirmed the branch is `codex/update-ct-gui-prototype`.
- Confirmed the latest pushed commit is `ed5cf86 docs: record quality inference comparison`.
- Confirmed the working tree was clean before creating these planning files.
- Captured the product strategy: `quality` is official/default, `fast` is quick preview only and must be marked as needing review.
- Next planned action: implement user-visible inference mode selection and carry the selected profile through job state and result summaries.

## 2026-05-25 Follow-up Implementation

- Implemented Phase 1 product mode selection:
  - Frontend `分割控制` exposes `质量推理` / `快速预览`, defaulting to `quality`.
  - Fast preview shows a visible `需人工复核` warning and fast result metadata cannot be mistaken for official quality output.
  - `createInferenceJob()` sends `inference_profile` with each job.
  - Backend `/api/segment/jobs` resolves request-level `quality` / `fast` into effective `inference_options`.
  - Effective options are carried through create response, job state, SSE complete events, `job_summary.json`, and cache key input.
- Updated `README.md`, `REVIEW.md`, and `SEGMENTATION_METRICS_SUMMARY.md` to document the productized mode selection without changing benchmark conclusions.
- Verification completed:
  - `node tests/imagingLogic.test.ts`
  - `python tests/backendState.test.py` with isolated `SEGMENTATION_TEST_TMP`
  - `npm --prefix 'D:\BME2026\BME_CT_Seg\segmentation-gui-prototype' test`
  - `npm --prefix 'D:\BME2026\BME_CT_Seg\segmentation-gui-prototype' run build`
- Remaining planned action: review git diff, then commit and push the follow-up work.

## 2026-05-25 Main Baseline Closure

- Confirmed the active branch is `main` tracking `origin/main`.
- Confirmed selectable inference profile work has been merged and pushed at commit `838e77e merge selectable inference profiles`.
- Updated the follow-up plan so the remaining work starts from benchmark discipline, postprocess experiment gating, and broader reference-case validation rather than repeating Phase 1.
- Verification to run for this baseline:
  - `npm test`
  - `npm run build`
- Verification completed:
  - `npm --prefix 'D:\BME2026\BME_CT_Seg\segmentation-gui-prototype' test` exited 0.
  - `npm --prefix 'D:\BME2026\BME_CT_Seg\segmentation-gui-prototype' run build` exited 0; Vite built `1595` modules in `5.04s`.
- `git status --short` shows only planning-file edits under `.planning/online-inference-followup/`.
