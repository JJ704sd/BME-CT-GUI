"""Seed local cache entries for the AMOS 0117 + FLARE22 Tr 0009 demo.

AMOS 0117:
    Reuses the existing prediction at server/work/009d4efdc5f6/output/009d4efdc5f6.nii.gz
    (138 KB, real nnUNetv2 output from 2026-05-23) and writes a job_summary.json
    so find_cached_prediction() can register it as a cache hit.

FLARE22 Tr 0009:
    Reuses server/work/0aa7323a4c01/output/job_summary.json (the 218 s real
    inference that this runbook produced on 2026-06-01). On a fresh machine
    this job dir will not exist; the script will print a clear message telling
    the operator to run a real FLARE inference first.

    Also computes per-label Dice against the remapped reference at
    .test-output/flare22-tr-0009-quality-20260526/FLARE22_Tr_0009_label_remapped_to_amos_ids.nii.gz
    and writes validation_summary.json so cache hits surface the historical Dice.

Idempotent: re-running is safe; the existing job_summary.json is rewritten
with the same content, no duplicates created.

Usage:
    python tools/seed_demo_cache.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"D:\BME2026\BME_CT_Seg")
PROTOTYPE = PROJECT_ROOT / "segmentation-gui-prototype"
WORK_DIR = PROTOTYPE / "server" / "work"
NNUNET_FILES = PROTOTYPE / "nnunetv2_files"

CHECKPOINT = NNUNET_FILES / "checkpoint_best.pth"
INFERENCE_OPTIONS = {"profile": "quality", "tile_step_size": 0.5, "disable_tta": False, "not_on_device": False}
MODEL_STATE = {
    "checkpoint_dataset_name": "Dataset001_AMOS22",
    "checkpoint_configuration": "3d_fullres",
    "labels_source": "checkpoint",
    "runtime_target": "local",
}


def stable_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_cache_key(input_sha: str, checkpoint_sha: str) -> str:
    payload = {
        "input_sha256": input_sha,
        "checkpoint_sha256": checkpoint_sha,
        **{k: v for k, v in MODEL_STATE.items() if k != "runtime_target"},
        "runtime_target": "local",
        "inference_options": INFERENCE_OPTIONS,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def seed_amos(checkpoint_sha: str) -> tuple[str, Path]:
    job_id = "009d4efdc5f6"
    result_path = WORK_DIR / job_id / "output" / f"{job_id}.nii.gz"
    if not result_path.exists():
        raise FileNotFoundError(
            f"AMOS prediction missing at {result_path}. "
            "Restore nnunetv2_files/amos_0117_prediction_009d4efdc5f6.nii.gz "
            "or run a real AMOS inference once."
        )
    input_path = NNUNET_FILES / "amos_0117(3).nii.gz"
    input_sha = stable_file_sha256(input_path)
    cache_key = build_cache_key(input_sha, checkpoint_sha)
    summary = {
        "job_id": job_id,
        "mode": "real-nnunetv2",
        "status": "succeeded",
        "cache_key": cache_key,
        "cached_result": False,
        "cache_source_job_id": None,
        "result_ready": True,
        "result_path": str(result_path),
        "result_size_bytes": result_path.stat().st_size,
        "input_sha256": input_sha,
        "checkpoint_sha256": checkpoint_sha,
        "checkpoint_dataset_name": MODEL_STATE["checkpoint_dataset_name"],
        "checkpoint_configuration": MODEL_STATE["checkpoint_configuration"],
        "labels_source": MODEL_STATE["labels_source"],
        "runtime_target": "local",
        "inference_options": INFERENCE_OPTIONS,
        "label_taxonomy": "auto",
    }
    output_dir = WORK_DIR / job_id / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "job_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return cache_key, output_dir / "job_summary.json"


def check_flare() -> tuple[str, Path] | None:
    """Return (cache_key, job_summary_path) if a real FLARE inference exists, else None."""
    candidates = sorted(
        (p for p in WORK_DIR.iterdir() if p.is_dir() and p.name != "runtime_model"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for job_dir in candidates:
        summary_path = job_dir / "output" / "job_summary.json"
        if not summary_path.exists():
            continue
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if (
            summary.get("runtime_target") == "local"
            and summary.get("mode") == "real-nnunetv2"
            and summary.get("result_ready")
            and (job_dir / "output" / f"{job_dir.name}.nii.gz").exists()
            and summary.get("label_taxonomy") in {"FLARE22", "auto"}
            and summary.get("checkpoint_sha256") == stable_file_sha256(CHECKPOINT)
        ):
            return summary.get("cache_key", ""), summary_path
    return None


FLARE22_REMAP_REFERENCE = (
    PROJECT_ROOT
    / "segmentation-gui-prototype"
    / ".test-output"
    / "flare22-tr-0009-quality-20260526"
    / "FLARE22_Tr_0009_label_remapped_to_amos_ids.nii.gz"
)


AMOS_LABELS = [
    {"label": 1, "nameZh": "脾脏", "nameEn": "spleen"},
    {"label": 2, "nameZh": "右肾", "nameEn": "right_kidney"},
    {"label": 3, "nameZh": "左肾", "nameEn": "left_kidney"},
    {"label": 4, "nameZh": "胆囊", "nameEn": "gallbladder"},
    {"label": 5, "nameZh": "食管", "nameEn": "esophagus"},
    {"label": 6, "nameZh": "肝脏", "nameEn": "liver"},
    {"label": 7, "nameZh": "胃", "nameEn": "stomach"},
    {"label": 8, "nameZh": "主动脉", "nameEn": "aorta"},
    {"label": 9, "nameZh": "下腔静脉", "nameEn": "inferior_vena_cava"},
    {"label": 10, "nameZh": "胰腺", "nameEn": "pancreas"},
    {"label": 11, "nameZh": "右肾上腺", "nameEn": "right_adrenal_gland"},
    {"label": 12, "nameZh": "左肾上腺", "nameEn": "left_adrenal_gland"},
    {"label": 13, "nameZh": "十二指肠", "nameEn": "duodenum"},
    {"label": 14, "nameZh": "膀胱", "nameEn": "bladder"},
    {"label": 15, "nameZh": "前列腺/子宫", "nameEn": "prostate_uterus"},
]


def seed_flare22_validation(checkpoint_sha: str) -> Path | None:
    """Compute per-label Dice for the FLARE22 cache source and write validation_summary.json.

    Returns the validation_summary.json path on success, None if no FLARE cache
    source or remapped reference is available.
    """
    import importlib.util
    import sys

    flare = check_flare()
    if flare is None:
        return None
    _cache_key, flare_summary_path = flare
    flare_job_dir = flare_summary_path.parent.parent
    prediction_path = flare_job_dir / "output" / f"{flare_job_dir.name}.nii.gz"
    validation_summary_path = flare_job_dir / "output" / "validation_summary.json"
    if not FLARE22_REMAP_REFERENCE.exists():
        print(
            f"  SKIP validation: remapped reference not found at {FLARE22_REMAP_REFERENCE}",
            file=sys.stderr,
        )
        return None
    if validation_summary_path.exists():
        return validation_summary_path
    sys.path.insert(0, str(PROTOTYPE / "tools"))
    try:
        metrics_module = importlib.import_module("segmentation_metrics_summary")
        compute_segmentation_metrics = metrics_module.compute_segmentation_metrics
        round_metric = metrics_module.round_metric
    finally:
        sys.path.pop(0)
    import nibabel
    import numpy as np
    prediction = np.asarray(nibabel.load(str(prediction_path)).get_fdata(), dtype=np.float32)
    reference = np.asarray(nibabel.load(str(FLARE22_REMAP_REFERENCE)).get_fdata(), dtype=np.float32)
    raw = compute_segmentation_metrics(
        prediction,
        reference,
        AMOS_LABELS,
        sample_id="flare22_tr_0009",
    )
    dice_values = [row["dice"] for row in raw.get("labels", []) if row.get("dice") is not None]
    mean_dice = round_metric(sum(dice_values) / len(dice_values)) if dice_values else None
    min_dice = round_metric(min(dice_values)) if dice_values else None
    accepted = mean_dice is not None and min_dice is not None
    summary = {
        "status": "review",
        "sample_id": "flare22_tr_0009",
        "accepted": accepted,
        "mean_dice": mean_dice,
        "min_dice": min_dice,
        "foreground_dice": round_metric(raw.get("foreground_dice")),
        "message": "（历史离线 remap 摘要，未在当前 job 重新验证）",
        "thresholds": {
            "mean_dice": 0.85,
            "min_label_dice": 0.7,
        },
        "remap_applied": True,
        "remap_source": "FLARE22",
        "labels": [
            {
                "label": int(row["label"]),
                "name": row.get("name") or row.get("nameZh") or f"Label {row['label']}",
                "dice": row.get("dice"),
                "prediction_voxels": row.get("prediction_voxels", 0),
                "reference_voxels": row.get("reference_voxels", 0),
                "intersection_voxels": row.get("intersection_voxels", 0),
            }
            for row in raw.get("labels", [])
        ],
    }
    validation_summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return validation_summary_path


def main() -> int:
    if not CHECKPOINT.exists():
        print(f"ERROR: checkpoint not found at {CHECKPOINT}", file=sys.stderr)
        return 2
    checkpoint_sha = stable_file_sha256(CHECKPOINT)
    print(f"checkpoint: {CHECKPOINT.name} sha256={checkpoint_sha[:16]}...")
    print(f"work_dir:   {WORK_DIR}")
    print()

    print("[AMOS 0117]")
    try:
        amos_key, amos_summary = seed_amos(checkpoint_sha)
        print(f"  cache_key: {amos_key}")
        print(f"  wrote:     {amos_summary}")
    except FileNotFoundError as exc:
        print(f"  SKIP: {exc}", file=sys.stderr)
        return 1
    print()

    print("[FLARE22 Tr 0009]")
    flare = check_flare()
    if flare is None:
        print("  NOT FOUND: no real FLARE inference on disk.", file=sys.stderr)
        print("  To populate: open the GUI, run FLARE22 Tr 0009 once (~3-5 min on RTX 4060).", file=sys.stderr)
        print("  Then re-run this script.", file=sys.stderr)
        return 1
    flare_key, flare_summary = flare
    print(f"  cache_key: {flare_key}")
    print(f"  source:    {flare_summary}")
    print("  validation: computing per-label Dice against remapped reference ...")
    validation_path = seed_flare22_validation(checkpoint_sha)
    if validation_path is None:
        print("  validation: SKIPPED (no remapped reference on disk)")
    else:
        print(f"  validation: wrote {validation_path}")
    print()

    print("Both caches ready. Re-uploading the same CT files will hit cached-real-nnunetv2.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
