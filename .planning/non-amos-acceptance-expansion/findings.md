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
