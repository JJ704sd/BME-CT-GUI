from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Run uncached persistent-worker nnUNet performance checks.")
  parser.add_argument("--run-root", type=Path, default=None, help="Directory for isolated work and summary files.")
  parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "nnunetv2_files" / "amos_0117(3).nii.gz")
  parser.add_argument("--runs", type=int, default=2, help="Number of uncached sequential runs. Use 2 for cold/warm.")
  parser.add_argument("--device", default="cuda", choices=["cuda", "cpu", "mps"])
  parser.add_argument("--preprocess-workers", type=int, default=2)
  parser.add_argument("--export-workers", type=int, default=2)
  parser.add_argument("--inference-profile", default="quality", choices=["quality", "fast"])
  parser.add_argument("--tile-step-size", type=float, default=None, help="Override nnUNet sliding-window step size.")
  parser.add_argument("--disable-tta", action="store_true", help="Disable mirroring/TTA for faster but less accurate inference.")
  parser.add_argument("--not-on-device", action="store_true", help="Disable perform_everything_on_device to reduce VRAM pressure.")
  parser.add_argument("--timeout-seconds", type=int, default=1800)
  parser.add_argument("--dry-run", action="store_true", help="Print resolved settings without running inference.")
  return parser.parse_args()


def run_label(index: int) -> str:
  if index == 0:
    return "cold_persistent_no_cache"
  if index == 1:
    return "warm_persistent_no_cache"
  return f"warm_persistent_no_cache_{index + 1}"


def main() -> int:
  args = parse_args()
  stamp = time.strftime("%Y%m%d-%H%M%S")
  run_root = (args.run_root or PROJECT_ROOT / ".test-output" / f"perf-no-cache-persistent-{stamp}").resolve()
  tile_step_size = args.tile_step_size if args.tile_step_size is not None else (1.0 if args.inference_profile == "fast" else 0.5)
  disable_tta = bool(args.disable_tta or args.inference_profile == "fast")

  settings = {
    "project_root": str(PROJECT_ROOT),
    "run_root": str(run_root),
    "input": str(args.input),
    "runs": args.runs,
    "device": args.device,
    "preprocess_workers": args.preprocess_workers,
    "export_workers": args.export_workers,
    "inference_profile": args.inference_profile,
    "tile_step_size": tile_step_size,
    "disable_tta": disable_tta,
    "not_on_device": args.not_on_device,
    "timeout_seconds": args.timeout_seconds,
    "cache_policy": "disabled via patch(server.find_cached_prediction, return_value=None)",
    "worker_policy": "SEGMENTATION_PERSISTENT_WORKER=1",
  }
  if args.dry_run:
    print(json.dumps(settings, ensure_ascii=False, indent=2))
    return 0

  if args.runs < 1:
    raise SystemExit("--runs must be >= 1")
  input_path = args.input.resolve()
  if not input_path.exists():
    raise SystemExit(f"Input NIfTI does not exist: {input_path}")

  os.environ["SEGMENTATION_DEVICE"] = args.device
  os.environ["SEGMENTATION_PREPROCESS_WORKERS"] = str(args.preprocess_workers)
  os.environ["SEGMENTATION_EXPORT_WORKERS"] = str(args.export_workers)
  os.environ["SEGMENTATION_PERSISTENT_WORKER"] = "1"
  os.environ["SEGMENTATION_INFERENCE_PROFILE"] = args.inference_profile
  os.environ["SEGMENTATION_TILE_STEP_SIZE"] = str(tile_step_size)
  os.environ["SEGMENTATION_DISABLE_TTA"] = "1" if disable_tta else "0"
  os.environ["SEGMENTATION_NOT_ON_DEVICE"] = "1" if args.not_on_device else "0"

  from fastapi.testclient import TestClient
  import server.main as server

  run_root.mkdir(parents=True, exist_ok=True)
  progress_path = run_root / "progress.jsonl"
  summary_path = run_root / "perf_no_cache_persistent_summary.json"

  server.WORK_DIR = run_root / "work"
  server.RUNTIME_MODEL_DIR = server.WORK_DIR / "runtime_model" / "nnUNetTrainer__nnUNetPlans__2d"
  server.RUNTIME_CHECKPOINT = server.RUNTIME_MODEL_DIR / "fold_0" / "checkpoint_best.pth"
  server.jobs.clear()
  client = TestClient(server.app)

  def emit(payload: dict[str, Any]) -> None:
    line = json.dumps({"timestamp": round(time.time(), 3), **payload}, ensure_ascii=True)
    print(line, flush=True)
    with progress_path.open("a", encoding="utf-8") as handle:
      handle.write(line + "\n")

  def compact_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
      "job_id": state.get("job_id"),
      "status": state.get("status"),
      "progress": state.get("progress"),
      "stage": state.get("stage"),
      "mode": state.get("mode"),
      "cached_result": state.get("cached_result"),
      "duration_seconds": state.get("duration_seconds"),
      "phase_timings": state.get("phase_timings"),
      "result_ready": state.get("result_ready"),
      "error": state.get("error"),
    }

  def run_once(label: str) -> dict[str, Any]:
    started = time.time()
    with input_path.open("rb") as handle:
      response = client.post(
        "/api/segment/jobs",
        files={"file": (input_path.name, handle, "application/gzip")},
        data={"model_id": "abdomen", "confidence_threshold": "0.65"},
      )
    body = response.json()
    emit({
      "event": "created",
      "label": label,
      "status_code": response.status_code,
      "job_id": body.get("job_id"),
      "cached_result": body.get("cached_result"),
      "mode": body.get("mode"),
    })
    if response.status_code != 200:
      return {"label": label, "status": "create_failed", "body": body}
    if body.get("cached_result"):
      return {"label": label, "status": "unexpected_cache", "body": body}

    job_id = body["job_id"]
    last_marker = None
    while True:
      state = client.get(f"/api/segment/jobs/{job_id}").json()
      marker = (
        state.get("status"),
        state.get("progress"),
        state.get("stage"),
        tuple(sorted((state.get("phase_timings") or {}).items())),
      )
      if marker != last_marker:
        emit({
          "event": "progress",
          "label": label,
          "elapsed_wall_seconds": round(time.time() - started, 1),
          "state": compact_state(state),
        })
        last_marker = marker
      if state.get("status") in {"succeeded", "failed", "cancelled"}:
        break
      if time.time() - started > args.timeout_seconds:
        return {"label": label, "status": "timeout", "state": compact_state(state)}
      time.sleep(10)

    result_status = None
    result_bytes = None
    if state.get("status") == "succeeded":
      result_response = client.get(f"/api/segment/jobs/{job_id}/result")
      result_status = result_response.status_code
      result_bytes = len(result_response.content)
    validation = state.get("validation") or {}
    return {
      "label": label,
      "job_id": job_id,
      "status": state.get("status"),
      "mode": state.get("mode"),
      "cached_result": state.get("cached_result"),
      "checkpoint_sha256": state.get("checkpoint_sha256"),
      "duration_seconds": state.get("duration_seconds"),
      "phase_timings": state.get("phase_timings"),
      "result_status": result_status,
      "result_bytes": result_bytes,
      "validation_status": validation.get("status"),
      "mean_dice": validation.get("mean_dice"),
      "min_dice": validation.get("min_dice"),
      "foreground_dice": validation.get("foreground_dice"),
      "error": state.get("error"),
    }

  summaries: list[dict[str, Any]] = []
  exit_code = 1
  try:
    emit({"event": "start", **settings})
    with patch.object(server, "find_cached_prediction", return_value=None):
      for index in range(args.runs):
        summaries.append(run_once(run_label(index)))
    exit_code = 0 if all(item.get("status") == "succeeded" and item.get("cached_result") is False for item in summaries) else 1
    return exit_code
  finally:
    with server.persistent_worker_lock:
      server.close_persistent_worker_locked()
    result = {"settings": settings, "summaries": summaries, "exit_code": exit_code}
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    emit({"event": "summary", "summary_path": str(summary_path), "result": result})


if __name__ == "__main__":
  raise SystemExit(main())
