# Non-AMOS Acceptance Expansion Plan

**Goal:** Expand the GUI acceptance evidence beyond AMOS 0117 using local non-AMOS CT cases without committing private imaging data.

**Current baseline:** `main` at `838e77e merge selectable inference profiles`.

**Primary rule:** `quality` remains the official acceptance profile. `fast` may be recorded only as a preview or comparison path and must stay marked as requiring review.

## Status

- [x] Confirm main baseline is already verified by `npm test` and `npm run build`.
- [x] Confirm current tracked example registry only contains AMOS plus a placeholder external example.
- [x] Confirm local `nnunetv2_files/` currently contains AMOS 0117 assets and the active checkpoint, but no confirmed non-AMOS acceptance case.
- [x] Identify candidate non-AMOS `.nii` / `.nii.gz` files.
- [x] Create a private local reference-case registry.
- [x] Validate `/api/samples` metadata for registered cases.
- [ ] Run manual GUI acceptance for each selected case.
- [ ] Run segmentation metrics only for cases with compatible real labels.
- [x] Update acceptance and metrics documentation with evidence.
- [x] Fix three-view interaction lag mitigation and split-mode visibility for real NIfTI views.
- [x] Add module-level code walkthrough document: `CODE_MODULE_GUIDE.md`.

## Rules and Constraints

- Do not commit real CT, NIfTI, checkpoint, prediction, or private patient paths.
- Keep true local case registration in an ignored location, preferably `nnunetv2_files/reference_cases.local.json`, then point the backend at it with `SEGMENTATION_REFERENCE_CASES_JSON`.
- Keep `reference_cases.example.json` as a public schema/example file only. Do not put private real case paths there.
- Do not calculate or claim Dice, IoU, or Hausdorff metrics unless the case has a real label file whose label IDs match the checkpoint label definition.
- If a case has no label, record browsing, inference, result download, GUI refill, and human review only.
- Keep benchmark and inference outputs under `.test-output/`.
- Separate raw model metrics from any later postprocess experiment.

## Phase 1: Candidate Data Inventory

Goal: pick credible non-AMOS local cases before changing app behavior or documentation.

Tasks:

- [x] Search for candidate NIfTI files outside the current AMOS-only inputs:

```powershell
Get-ChildItem -Path 'D:\BME2026' -Recurse -File -Include *.nii,*.nii.gz |
  Where-Object { $_.FullName -notmatch 'segmentation-gui-prototype\\nnunetv2_files\\amos_0117' } |
  Select-Object FullName, Length, LastWriteTime
```

- [x] For each candidate, record this table in `progress.md`:

| Field | Required value |
|---|---|
| case_id | Stable local ID, for example `flare_0001` or `local_abdomen_001` |
| dataset | Source name, for example `FLARE`, `Local`, or `External` |
| original_path | Local CT image path, not committed |
| label_path | Local label path, or `none` |
| has_label | `true` / `false` |
| expected_validation | `metrics` when label taxonomy matches, otherwise `manual-only` |
| notes | Anything about anatomy coverage, spacing, privacy, or uncertainty |

- [x] Select at least two cases if available:
  - One labeled case for metrics, if a compatible label exists.
  - One additional non-AMOS case for browser and inference workflow coverage.

Acceptance checks:

- [x] Selected cases are not just copies of AMOS 0117.
- [x] Label availability is explicitly recorded.
- [x] Any taxonomy mismatch is treated as `manual-only`, not as failed model quality.

## Phase 2: Private Reference Registry

Goal: make selected cases available through `/api/samples` without exposing private data in tracked files.

Tasks:

- [x] Create `nnunetv2_files/reference_cases.local.json` with this structure:

```json
{
  "samples": [
    {
      "id": "non_amos_case_001",
      "name": "Non-AMOS Case 001",
      "dataset": "External",
      "modality": "CT",
      "role": "external-reference",
      "description": "Local non-AMOS CT case for GUI acceptance. Validation is manual-only unless a compatible label is configured.",
      "original": "external_cases/non_amos_case_001_image.nii.gz",
      "original_filename": "non_amos_case_001_image.nii.gz"
    }
  ]
}
```

- [ ] If a compatible label exists, add:

```json
{
  "label": "external_cases/non_amos_case_001_label.nii.gz",
  "label_filename": "non_amos_case_001_label.nii.gz"
}
```

- [x] Start the backend with the private registry:

```powershell
$env:SEGMENTATION_REFERENCE_CASES_JSON = "D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\nnunetv2_files\reference_cases.local.json"
$env:SEGMENTATION_DEVICE = "cuda"
$env:SEGMENTATION_INFERENCE_PROFILE = "quality"
$env:SEGMENTATION_PREPROCESS_WORKERS = "2"
$env:SEGMENTATION_EXPORT_WORKERS = "2"
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

- [x] Confirm `/api/samples` exposes the case and correct `validation_available`:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/samples' | ConvertTo-Json -Depth 6
```

Acceptance checks:

- [ ] Cases with both original and compatible label show `validation_available=true` (not applicable until a compatible labeled case is found).
- [x] Cases without labels or without compatible labels show `validation_available=false`.
- [x] No private registry or true NIfTI path is staged for Git.

## Phase 3: GUI Acceptance Run

Goal: record whether each non-AMOS case works through the product workflow.

Tasks for each selected case:

- [ ] Start the frontend:

```powershell
npm run dev -- --port 5173
```

- [ ] Load the case from the reference-case UI.
- [ ] Record CT browser metadata:

| Field | Record |
|---|---|
| case_id | Selected case ID |
| dimensions | columns / rows / slices |
| spacing | x / y / z |
| Axial | readable / distorted / overflow / notes |
| Sagittal | readable / distorted / overflow / notes |
| Coronal | readable / distorted / overflow / notes |
| interaction | click, drag, wheel, crosshair stability |
| mobile | vertical scroll ok, no horizontal overflow |

- [ ] Run `quality` inference once with cache avoided or clearly recorded as cache miss.
- [ ] Record inference details:

| Field | Record |
|---|---|
| case_id | Selected case ID |
| profile | `quality` |
| job_id | Backend job ID |
| mode | `real-nnunetv2` / `cached-real-nnunetv2` / `unavailable` |
| cached_result | `true` / `false` |
| duration_seconds | Job duration |
| phase_timings | prepare / nnUNet or persistent worker / validation / collect result |
| result_size_bytes | Output bytes |
| resource_latest | device, GPU, disk free |
| result_refill | overlay / split / side / difference usable |
| review_note | Human review outcome |

- [ ] Run a second same-input submission only if cache behavior needs to be documented separately.

Acceptance checks:

- [ ] Three orthogonal views remain readable.
- [ ] Result download and GUI refill work.
- [ ] No unlabeled case is documented as automatically validated.
- [ ] Any fast preview run is clearly separate from the official `quality` run.

## Phase 4: Metrics for Labeled Cases

Goal: add numeric evidence only when labels are real and compatible.

Tasks:

- [ ] For each labeled case, run:

```powershell
python tools\segmentation_metrics_summary.py `
  --prediction <prediction.nii.gz> `
  --reference <reference-label.nii.gz> `
  --checkpoint nnunetv2_files\checkpoint_best.pth `
  --labels-json <validation_summary.json> `
  --sample-id <case-id> `
  --output-dir .test-output\<case-id>-quality-metrics-YYYYMMDD-HHMM `
  --stem <case-id>-quality-segmentation-metrics
```

- [ ] Record aggregate metrics:

| Metric | Record |
|---|---|
| mean Dice | value |
| min Dice | value |
| foreground Dice | value |
| mean IoU | value |
| min IoU | value |
| foreground IoU | value |
| voxel accuracy | value |
| mean Hausdorff Distance | mm |
| max Hausdorff Distance | mm |
| label 14/15 prediction voxels | value / value |

Acceptance checks:

- [ ] Metrics output JSON and Markdown are under `.test-output/`.
- [ ] Raw model metrics are documented separately from any postprocess metrics.
- [ ] Label taxonomy assumptions are stated before interpreting scores.

## Phase 5: Documentation and Verification

Goal: make the new evidence useful without overstating model generalization.

Tasks:

- [x] Update `ACCEPTANCE.md` with non-AMOS manual acceptance records.
- [x] Update `SEGMENTATION_METRICS_SUMMARY.md` only with clearly marked FLARE22 taxonomy-remapped comparison metrics; do not treat them as backend automatic validation.
- [ ] Update `README.md` only if the user-facing workflow changes; do not move the full experiment log into README.
- [ ] Run focused checks:

```powershell
node tests/acceptanceDocs.test.ts
python tests/segmentationMetrics.test.py
```

- [ ] Run full checks before committing:

```powershell
npm test
npm run build
git status --short
```

Acceptance checks:

- [ ] Documentation distinguishes AMOS evidence from non-AMOS evidence.
- [ ] Unlabeled cases are manual-only.
- [ ] No private imaging files, ignored outputs, or local registry files are staged.

## Phase 6: GUI Interaction Performance and Split-mode Follow-up

Goal: reduce visible cursor-move lag and make the `分屏` control observable in the real three-view NIfTI workflow.

Tasks:

- [x] Confirm root cause: high-frequency pointer movement can trigger synchronous NIfTI slice rasterization and preview thumbnail refresh.
- [x] Coalesce three-view image rerendering with `requestAnimationFrame` while keeping crosshair feedback immediate.
- [x] Coalesce selected axial slice preview updates per animation frame.
- [x] Reuse the shared cached slice renderer for axial side/footer previews.
- [x] Fix split mode in `OrthogonalViewer`: clip `.ortho-mask` by `--compare-position` when `maskVolume` exists.
- [x] Avoid showing a fake split divider when only the original CT is loaded.
- [x] Document the split-mode meaning: it is original-vs-mask sliding comparison, not Axial/Sagittal/Coronal layout switching.
- [x] Add `CODE_MODULE_GUIDE.md` for code walkthroughs.

Verification:

- [x] `node tests/imagingLogic.test.ts`
- [x] `node tests/acceptanceDocs.test.ts`
- [x] `npm test`
- [x] `npm run build`

Acceptance checks:

- [x] Split slider affects orthogonal mask clipping when a mask exists.
- [x] No split divider appears when no mask exists.
- [x] Crosshair uses immediate coordinates; heavy image rendering is frame-coalesced.
- [x] Documentation records that metrics/inference results are unchanged by this GUI-only fix.

## Stop Conditions

- Stop before metrics if labels are missing or label taxonomy is incompatible.
- Stop before long inference if GPU memory or runtime constraints make the run impractical; record the blocker in `progress.md`.
- Stop before documentation claims if the evidence only proves UI workflow, not model quality.
