# Non-AMOS Acceptance Expansion Findings

## Current Evidence

- Active project baseline is `main` at `838e77e merge selectable inference profiles`.
- The online inference follow-up plan records fresh baseline verification:
  - `npm --prefix 'D:\BME2026\BME_CT_Seg\segmentation-gui-prototype' test` exited 0.
  - `npm --prefix 'D:\BME2026\BME_CT_Seg\segmentation-gui-prototype' run build` exited 0.
- The tracked `reference_cases.example.json` contains AMOS 0117 plus a placeholder `flare_demo`.
- Local `nnunetv2_files/` currently shows AMOS 0117 image/label/prediction files and `checkpoint_best.pth`; no confirmed non-AMOS acceptance case has been found in that directory.
- `.gitignore` excludes `nnunetv2_files/`, `.test-output/`, `server/work/`, `*.nii`, `*.nii.gz`, `*.pth`, and `*.pt`.

## Decisions

- Use a private local registry such as `nnunetv2_files/reference_cases.local.json` or an external path referenced by `SEGMENTATION_REFERENCE_CASES_JSON`.
- Keep `reference_cases.example.json` public and schematic.
- Treat unlabeled external cases as manual acceptance only.
- Use `quality` as the official acceptance path.
- Keep fast-profile or postprocess experiments out of this acceptance expansion unless explicitly recorded as separate comparisons.

## Risks

- A non-AMOS label file may use a different label taxonomy from the current checkpoint. If so, automatic Dice/IoU/Hausdorff interpretation is invalid.
- Long first-run inference can take many minutes per case. Cache hits must be recorded separately from uncached runs.
- Single non-AMOS cases improve evidence breadth but still do not prove broad generalization.
- Private data paths can leak into docs if copied directly from local commands; documentation should use case IDs and dataset names instead.

## Open Questions

- Which local non-AMOS cases are available and allowed for this project?
- Do any non-AMOS cases include compatible ground-truth labels?
- How many cases are enough for the next acceptance milestone: one labeled plus one unlabeled, or a larger set?
- Should screenshots be kept local only, or should sanitized screenshots be added deliberately later?

## 2026-05-26 Candidate Inventory Findings

- Credible non-AMOS candidates are available in local FLARE data under `D:\BME2026\BME_CT_Seg\nnUNet_raw\Dataset001_FLARE`.
- Selected `flare_case_00002` from `imagesTr` and `flare_ts_0000` from `imagesTs` for private registry validation.
- `flare_case_00002` has a matching local label file in `nnUNet_preprocessed\Dataset001_FLARE\gt_segmentations`, but it is not compatible with the active checkpoint taxonomy.
- The active `nnunetv2_files\checkpoint_best.pth` reports `Dataset001_AMOS22`, configuration `3d_fullres`, and AMOS-style labels where label `1` is spleen, label `6` is liver, and labels `14/15` are bladder and prostate/uterus.
- The local FLARE dataset labels define label `1` as liver, label `3` as spleen, and only foreground labels `1..13`. This mismatch makes automatic Dice/IoU/Hausdorff invalid for FLARE labels under the current checkpoint.
- The private registry should omit `label` fields for the selected FLARE cases so `/api/samples` correctly reports `validation_available=false`.
- `nnunet_env` is the inference environment and currently lacks FastAPI. Use the default `python` environment to run or test `server.main`; keep `nnunet_env` for nnUNet execution through the backend.
- The private registry validation path is working: temporary uvicorn on `127.0.0.1:8000` returned both FLARE cases with `has_original=true`, `has_label=false`, and `validation_available=false`.

## 2026-05-26 FLARE22 Tr 0009 Findings

- `FLARE22_Tr_0009_0000.nii.gz` is a usable non-AMOS CT original for online inference.
- `FLARE22_Tr_0009.nii.gz` is a real label with matching shape/spacing, but its label IDs follow FLARE22 rather than the active AMOS22 checkpoint.
- Because of the label mismatch, the correct product behavior is `validation_available=false` in `/api/samples`; automatic backend validation would be misleading.
- The quality online inference completed successfully without cache:
  - job `86b0153d0a73`
  - `duration_seconds=237.323`
  - `result_size_bytes=120761`
  - completion GPU snapshot `1804 / 8188 MiB`, `18%`
- Offline taxonomy remap by organ name gives a useful comparison signal: `mean_dice=0.893127`, `foreground_dice=0.949908`, `min_dice=0.673730`.
- Weakest remapped label is `duodenum` (`Dice=0.673730`, Hausdorff `38.043429 mm`); `pancreas` and `esophagus` are around `0.81` Dice and should be manually reviewed.
- Labels `14/15` are absent in FLARE22 and the `quality` prediction had `0 / 0` predicted voxels for them in this case.

## 2026-05-26 GUI Interaction Findings

- The reported cursor lag is tied to synchronous front-end rendering, not to nnUNetv2 inference or backend data loading.
- `requestAnimationFrame` coalescing is appropriate here because pointer events can arrive faster than useful slice image repaint cadence.
- Crosshair movement should remain bound to the immediate coordinate state; only heavy slice image generation should be deferred/coalesced.
- The `分屏` control means original-vs-mask sliding comparison, not Axial/Sagittal/Coronal layout switching.
- A bug existed in the current three-view workflow: split-mode CSS clipping was implemented for the old `.result-layer` comparison stage but not for `.ortho-mask`.
- The fix is to clip `.compare-split.has-mask .ortho-mask` by `--compare-position` and show the divider only when `maskVolume` exists.
- If only the original CT is loaded, split mode has no visible comparison target and should not display a fake divider.
