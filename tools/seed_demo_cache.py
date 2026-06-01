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
    print()

    print("Both caches ready. Re-uploading the same CT files will hit cached-real-nnunetv2.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
