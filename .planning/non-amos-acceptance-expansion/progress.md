# Non-AMOS Acceptance Expansion Progress

## 2026-05-25 Planning

- Created a dedicated planning session for expanding acceptance beyond AMOS 0117.
- Kept this separate from `.planning/online-inference-followup/`, which is mainly about inference profile behavior, benchmark discipline, and postprocess experiment gating.
- Reviewed the existing registry and docs constraints:
  - `reference_cases.example.json` is only a public example.
  - `ACCEPTANCE.md` already warns that current evidence is mainly AMOS 0117.
  - `SEGMENTATION_METRICS_SUMMARY.md` states that cases without standard labels cannot get Dice, IoU, or Hausdorff metrics.
- Checked local `nnunetv2_files/`; it currently contains AMOS 0117 assets and the checkpoint, not a confirmed non-AMOS case.
- Next action: inventory local non-AMOS `.nii` / `.nii.gz` candidates and choose which ones can be registered privately.

## 2026-05-26 Candidate Data Inventory

- Ran the planned `D:\BME2026` NIfTI inventory and found credible non-AMOS candidates under `D:\BME2026\BME_CT_Seg\nnUNet_raw\Dataset001_FLARE`.
- Ignored package test fixtures under `nnunetv2\tests` / `nnunet_env\Lib\site-packages\nibabel\tests`, plus existing app `.test-output` and `server\work` files, because they are not new acceptance cases.
- Confirmed the active checkpoint reports `Dataset001_AMOS22`, `3d_fullres`, with AMOS-style labels `1..15`.
- Confirmed local `Dataset001_FLARE` labels use a different label ID taxonomy from the active AMOS22 checkpoint. Even when a FLARE label file exists, it must be treated as `manual-only` for this checkpoint.

| case_id | dataset | original_path | label_path | has_label | expected_validation | notes |
|---|---|---|---|---|---|---|
| `flare_case_00002` | FLARE | `D:\BME2026\BME_CT_Seg\nnUNet_raw\Dataset001_FLARE\imagesTr\Case_00002_0000.nii.gz` | `D:\BME2026\BME_CT_Seg\nnUNet_preprocessed\Dataset001_FLARE\gt_segmentations\Case_00002.nii.gz` | `true` | `manual-only` | Image and label shapes both `(512, 512, 64)` with spacing `(0.976562, 0.976562, 4.0)`. Label values are `0..13`, but their FLARE meanings do not match the active AMOS22 checkpoint labels, so this label must not be registered for automatic validation. |
| `flare_ts_0000` | FLARE | `D:\BME2026\BME_CT_Seg\nnUNet_raw\Dataset001_FLARE\imagesTs\FLARE_0000_0000.nii.gz` | `none` | `false` | `manual-only` | Image shape `(512, 512, 102)` with spacing `(0.820312, 0.820312, 5.0)`. Selected as an additional non-AMOS browser/inference workflow case without metrics. |

- Selected the two cases above for the next private registry step.
- Next action: create `nnunetv2_files/reference_cases.local.json` with both selected cases and no `label` fields, then validate `/api/samples` reports `validation_available=false` for both.

## 2026-05-26 Private Registry and `/api/samples` Validation

- Created ignored private registry: `nnunetv2_files/reference_cases.local.json`.
- Registry entries:
  - `flare_case_00002`: original configured, no label configured because the available FLARE label taxonomy is incompatible with the active AMOS22 checkpoint.
  - `flare_ts_0000`: original configured, no label available.
- Confirmed `git check-ignore -v nnunetv2_files/reference_cases.local.json` is covered by `.gitignore:10:nnunetv2_files/`.
- First direct backend attempt used `D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\python.exe`; that environment does not have FastAPI installed, so do not use it to launch `server.main`.
- Re-ran backend validation with default `python`, private registry env, and a temporary uvicorn process on `127.0.0.1:8000`.
- `/api/samples` returned both selected cases with:
  - `has_original=true`
  - `has_label=false`
  - `validation_available=false`
- Stopped the temporary uvicorn process after validation.
- Next action: Phase 3 GUI acceptance for `flare_case_00002` and `flare_ts_0000`, including browser metadata, three-view readability, and `quality` inference only if the long GPU run is acceptable.

## 2026-05-26 FLARE22 Tr 0009 Online Inference

- User provided a newer FLARE22 supplemental case under `nnunetv2_files/`:
  - `FLARE\`: local FLARE challenge notes/evaluation scripts.
  - `FLARE22_Tr_0009.nii.gz`: FLARE22 label.
  - `FLARE22_Tr_0009_0000.nii.gz`: FLARE22 original image.
- NIfTI inspection:
  - Original shape `(512, 512, 87)`, spacing `(0.806641, 0.806641, 2.5)`, dtype `float32`.
  - Label shape `(512, 512, 87)`, spacing `(0.806641, 0.806641, 2.5)`, values `0..13`.
- Confirmed taxonomy mismatch:
  - FLARE22 label `1=liver`, `3=spleen`, `4=pancreas`, `13=left_kidney`.
  - Active AMOS22 checkpoint label `1=spleen`, `3=left_kidney`, `6=liver`, `10=pancreas`, `14/15=bladder/prostate_or_uterus`.
- Updated ignored private registry `nnunetv2_files/reference_cases.local.json` with `flare22_tr_0009`, original only. The local label is intentionally not registered for automatic validation.
- `/api/samples` confirmed `flare22_tr_0009` has `has_original=true`, `has_label=false`, `validation_available=false`.
- Ran real online `quality` inference:

| Field | Value |
|---|---|
| case_id | `flare22_tr_0009` |
| profile | `quality` |
| job_id | `86b0153d0a73` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| duration_seconds | `237.323` |
| phase_timings | `prepare_runtime_model=0.003`, `persistent_worker=237.119`, `collect_result=0.001` |
| result_size_bytes | `120761` |
| resource_latest | RTX 4060 Laptop GPU, `1804 / 8188 MiB`, `18%`, disk free `105865117696 bytes` |
| prediction | `.test-output\flare22-tr-0009-quality-20260526\86b0153d0a73.nii.gz` |
| backend_validation | `null`, by design because label taxonomy is not native-compatible |

- Created offline remapped reference under `.test-output\flare22-tr-0009-quality-20260526\FLARE22_Tr_0009_label_remapped_to_amos_ids.nii.gz`.
- Remap metadata saved to `.test-output\flare22-tr-0009-quality-20260526\flare_to_amos_label_remap.json`.
- Remapped metrics output:
  - JSON: `.test-output\flare22-tr-0009-quality-20260526\metrics-remapped\flare22-tr-0009-quality-remapped-segmentation-metrics.json`
  - Markdown: `.test-output\flare22-tr-0009-quality-20260526\metrics-remapped\flare22-tr-0009-quality-remapped-segmentation-metrics.md`
- Remapped aggregate metrics:

| Metric | Value |
|---|---:|
| mean Dice | `0.893127` |
| min Dice | `0.673730` |
| foreground Dice | `0.949908` |
| mean IoU | `0.815941` |
| min IoU | `0.507989` |
| foreground IoU | `0.904594` |
| voxel accuracy | `0.991879` |
| mean Hausdorff Distance | `12.595149 mm` |
| max Hausdorff Distance | `38.043429 mm` |

- Documentation updated: `ACCEPTANCE.md`, `SEGMENTATION_METRICS_SUMMARY.md`, and `REVIEW.md`.
- Next action: start frontend and perform GUI refill/three-view manual acceptance for `flare22_tr_0009`.

## 2026-05-26 GUI Interaction Performance and Split-mode Fix

- Investigated the reported lag during fast cursor movement in the three orthogonal CT views.
- Root cause:
  - `voxelCoord` updates can trigger synchronous NIfTI slice rasterization.
  - Right-side axial previews and footer thumbnails were also tied to slice updates.
  - Three-view `split` mode received `compareMode="split"`, but the current `.ortho-mask` layer had no split clipping rule, so the split slider was not visible in the real NIfTI three-view workflow.
- Implemented:
  - `OrthogonalViewer` now coalesces image slice rendering with `requestAnimationFrame` while keeping crosshair feedback immediate.
  - Main-page selected-slice updates are coalesced per animation frame.
  - Axial previews reuse the shared cached NIfTI slice renderer.
  - `.compare-split.has-mask .ortho-mask` now clips the mask layer by `--compare-position`, and a split divider is shown only when a mask volume exists.
  - Added `CODE_MODULE_GUIDE.md` for module-level code walkthroughs.
- Verification completed in this round:
  - `node tests/imagingLogic.test.ts`
  - `node tests/acceptanceDocs.test.ts`
  - Edge/Playwright smoke on `http://127.0.0.1:5173/` found 3 orthogonal panels, non-empty images, and no console errors after fast pointer drag.
- Finalization completed:
  - full `npm test` exited 0;
  - `npm run build` exited 0;
  - Git tracking check confirmed `nnunetv2_files/`, `.test-output/`, `server/work/`, and `nnunetv2_files/reference_cases.local.json` are not tracked.
