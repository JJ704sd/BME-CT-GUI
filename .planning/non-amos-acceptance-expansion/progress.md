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
