"""Rewrite 0aa7323a4c01 validation_summary.json from 2026-05-26 historical metrics.

Option B from local-cache demo: copy the 2026-05-26 quality-profile Dice
metrics into the current cache source's validation_summary.json so that
GUI cache hits for FLARE22 Tr 0009 surface numbers that match the README
(0.893 / 0.674 / 0.950).

Note: the 2026-05-26 prediction and 0aa7323a4c01 prediction differ at the
byte level (different cache_key SHA), so the Dice values are not strictly
the Dice of the 0aa7323a4c01 prediction. The validation_summary.json
carries an explicit "historical" / "source_metrics_path" tag so the GUI
can label it as a historical summary, not a fresh validation.
"""
from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(r"D:\BME2026\BME_CT_Seg\segmentation-gui-prototype")
SOURCE = PROJECT_ROOT / ".test-output" / "flare22-tr-0009-quality-20260526" / "metrics-remapped" / "flare22-tr-0009-quality-remapped-segmentation-metrics.json"
TARGET = PROJECT_ROOT / "server" / "work" / "0aa7323a4c01" / "output" / "validation_summary.json"

raw = json.loads(SOURCE.read_text(encoding="utf-8"))

labels = []
for row in raw.get("labels", []):
    labels.append({
        "label": int(row["label"]),
        "name": row.get("name") or f"Label {row['label']}",
        "dice": row.get("dice"),
        "prediction_voxels": row.get("prediction_voxels", 0),
        "reference_voxels": row.get("reference_voxels", 0),
        "intersection_voxels": row.get("intersection_voxels", 0),
    })

mean_dice = round(float(raw["mean_dice"]), 6)
min_dice = round(float(raw["min_dice"]), 6)
foreground_dice = round(float(raw["foreground_dice"]), 6)

summary = {
    "status": "review",
    "sample_id": "flare22_tr_0009",
    "accepted": mean_dice >= 0.85 and min_dice >= 0.7,
    "mean_dice": mean_dice,
    "min_dice": min_dice,
    "foreground_dice": foreground_dice,
    "message": "（历史离线缓存摘要，未在当前 job 重新验证）",
    "thresholds": {
        "mean_dice": 0.85,
        "min_label_dice": 0.7,
    },
    "remap_applied": True,
    "remap_source": "FLARE22",
    "historical": True,
    "source_job_id": "0aa7323a4c01",
    "source_metrics_path": str(SOURCE).replace("\\", "/"),
    "source_generated_at": raw.get("generated_at"),
    "source_prediction_path": ".test-output/flare22-tr-0009-quality-20260526/86b0153d0a73.nii.gz",
    "labels": labels,
}

TARGET.parent.mkdir(parents=True, exist_ok=True)
TARGET.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(f"wrote {TARGET}")
print(f"  mean_dice={summary['mean_dice']}  min_dice={summary['min_dice']}  fg_dice={summary['foreground_dice']}")
print(f"  labels: {len(labels)}  historical={summary['historical']}  source_job_id={summary['source_job_id']}")
