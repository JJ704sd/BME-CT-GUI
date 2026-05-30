from __future__ import annotations

import gzip
import json
import os
import hashlib
import queue
import shutil
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

try:
  from server.server_inference import (
    build_server_ensemble_command,
    build_server_evaluate_command,
    build_server_fold_commands,
    get_server_inference_config,
  )
except ModuleNotFoundError:
  sys.path.insert(0, str(Path(__file__).resolve().parent))
  from server_inference import (
    build_server_ensemble_command,
    build_server_evaluate_command,
    build_server_fold_commands,
    get_server_inference_config,
  )

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
NNUNET_FILES = ROOT / "nnunetv2_files"
NNUNET_RESULTS = PROJECT_ROOT / "nnUNet_results"
NNUNET_RAW = PROJECT_ROOT / "nnUNet_raw"
NNUNET_PREPROCESSED = PROJECT_ROOT / "nnUNet_preprocessed"
WORK_DIR = ROOT / "server" / "work"

DEBUG_LABEL = NNUNET_FILES / "amos_0117(2).nii.gz"
DEBUG_ORIGINAL = NNUNET_FILES / "amos_0117(3).nii.gz"
FALLBACK_LABEL = NNUNET_FILES / "amos_0117_label.nii" / "amos_0117(2).nii"
PROJECT_CHECKPOINT = NNUNET_FILES / "checkpoint_best.pth"
REFERENCE_CASES_JSON = Path(os.environ.get("SEGMENTATION_REFERENCE_CASES_JSON", ROOT / "reference_cases.json"))

FLARE_MODEL_DIR = NNUNET_RESULTS / "Dataset001_FLARE" / "nnUNetTrainer__nnUNetPlans__2d"
FLARE_DATASET_JSON = FLARE_MODEL_DIR / "dataset.json"
FLARE_PLANS_JSON = FLARE_MODEL_DIR / "plans.json"
FLARE_CHECKPOINT = FLARE_MODEL_DIR / "fold_0" / "checkpoint_best.pth"
RUNTIME_MODEL_DIR = WORK_DIR / "runtime_model" / "nnUNetTrainer__nnUNetPlans__2d"
RUNTIME_CHECKPOINT = RUNTIME_MODEL_DIR / "fold_0" / "checkpoint_best.pth"
NNUNET_PREDICT_COMMAND = PROJECT_ROOT / "nnunet_env" / "Scripts" / "nnUNetv2_predict_from_modelfolder.exe"
NNUNET_PYTHON_COMMAND = PROJECT_ROOT / "nnunet_env" / "Scripts" / "python.exe"
PERSISTENT_WORKER_SCRIPT = ROOT / "server" / "persistent_nnunet_worker.py"
NNUNET_PREDICT_ENTRYPOINT = (
  "import sys; "
  "from nnunetv2.inference.predict_from_raw_data import predict_entry_point_modelfolder; "
  "sys.argv=['nnUNetv2_predict_from_modelfolder'] + sys.argv[1:]; "
  "predict_entry_point_modelfolder()"
)
VALIDATION_MEAN_DICE_THRESHOLD = 0.85
VALIDATION_MIN_DICE_THRESHOLD = 0.70


def resolve_reference_path(value: Any, base_dir: Path) -> Path | None:
  if not isinstance(value, str) or not value.strip():
    return None
  path = Path(value)
  return path if path.is_absolute() else base_dir / path


def default_reference_case_specs() -> list[dict[str, Any]]:
  source_label = DEBUG_LABEL if DEBUG_LABEL.exists() else FALLBACK_LABEL
  return [
    {
      "id": "amos_0117",
      "name": "AMOS 0117",
      "dataset": "AMOS22",
      "modality": "CT",
      "role": "built-in-reference",
      "description": "内置参考病例，用于演示、回归和标准答案 Dice 验证。",
      "original": str(DEBUG_ORIGINAL),
      "label": str(source_label),
      "original_filename": "amos_0117_original.nii.gz",
      "label_filename": "amos_0117_label.nii.gz",
    }
  ]


def load_reference_case_specs() -> tuple[list[dict[str, Any]], Path]:
  if REFERENCE_CASES_JSON.exists():
    data = json.loads(REFERENCE_CASES_JSON.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("samples"), list):
      return data["samples"], REFERENCE_CASES_JSON.parent
    if isinstance(data, list):
      return data, REFERENCE_CASES_JSON.parent
  return default_reference_case_specs(), ROOT


def reference_case_records() -> list[dict[str, Any]]:
  specs, base_dir = load_reference_case_specs()
  records: list[dict[str, Any]] = []
  for spec in specs:
    if not isinstance(spec, dict):
      continue
    sample_id = spec.get("id")
    if not isinstance(sample_id, str) or not sample_id.strip():
      continue
    original_path = resolve_reference_path(spec.get("original"), base_dir)
    label_path = resolve_reference_path(spec.get("label"), base_dir)
    has_original = bool(original_path and original_path.exists())
    has_label = bool(label_path and label_path.exists())
    records.append({
      "id": sample_id,
      "name": spec.get("name") if isinstance(spec.get("name"), str) else sample_id,
      "dataset": spec.get("dataset") if isinstance(spec.get("dataset"), str) else "unknown",
      "modality": spec.get("modality") if isinstance(spec.get("modality"), str) else "CT",
      "role": spec.get("role") if isinstance(spec.get("role"), str) else "built-in-reference",
      "description": spec.get("description") if isinstance(spec.get("description"), str) else "",
      "original": str(original_path) if original_path else "",
      "label": str(label_path) if label_path else "",
      "original_url": f"/api/samples/{sample_id}/original",
      "label_url": f"/api/samples/{sample_id}/label",
      "original_filename": spec.get("original_filename") if isinstance(spec.get("original_filename"), str) else f"{sample_id}_original.nii.gz",
      "label_filename": spec.get("label_filename") if isinstance(spec.get("label_filename"), str) else f"{sample_id}_label.nii.gz",
      "validation_reference": str(label_path) if label_path else "",
      "validation_available": has_original and has_label,
      "has_original": has_original,
      "has_label": has_label,
      "_original_path": original_path,
      "_label_path": label_path,
    })
  return records


def find_reference_case(sample_id: str) -> dict[str, Any] | None:
  for record in reference_case_records():
    if record["id"] == sample_id:
      return record
  return None


def public_reference_case(record: dict[str, Any]) -> dict[str, Any]:
  return {key: value for key, value in record.items() if not key.startswith("_")}


@dataclass
class Job:
  id: str
  status: str = "pending"
  progress: int = 0
  stage: str = "等待执行"
  mode: str = "real-nnunetv2"
  error: str | None = None
  result_path: Path | None = None
  validation: dict[str, Any] | None = None
  started_at: float | None = None
  completed_at: float | None = None
  input_sha256: str | None = None
  checkpoint_sha256: str | None = None
  cache_key: str | None = None
  cached_result: bool = False
  cache_source_job_id: str | None = None
  inference_options: dict[str, Any] = field(default_factory=dict)
  phase_started_at: dict[str, float] = field(default_factory=dict, repr=False)
  phase_timings: dict[str, float] = field(default_factory=dict)
  log_tail: str | None = None
  process_log_path: Path | None = None
  resource_snapshots: list[dict[str, Any]] = field(default_factory=list)
  resource_log_path: Path | None = None
  label_path: Path | None = None
  runtime_target: str = "local"
  cancel_requested: bool = False
  process: subprocess.Popen[str] | None = field(default=None, repr=False, compare=False)
  child_processes: list[subprocess.Popen[str]] = field(default_factory=list, repr=False, compare=False)
  events: list[dict[str, Any]] = field(default_factory=list)


jobs: dict[str, Job] = {}
jobs_lock = threading.Lock()
persistent_worker_lock = threading.Lock()
persistent_worker_process: subprocess.Popen[str] | None = None
persistent_worker_key: tuple[str, str, str, int, int, float, bool, bool] | None = None
persistent_worker_log_handle: Any | None = None
persistent_worker_event_queue: queue.Queue[str | None] | None = None
persistent_worker_stdout_thread: threading.Thread | None = None
persistent_worker_reader_process: Any | None = None

HEARTBEAT_INTERVAL = 10


def push_heartbeat(job: Job, phase: str) -> None:
  try:
    elapsed = get_job_duration_seconds(job)
    event: dict[str, Any] = {
      "type": "progress",
      "progress": job.progress,
      "stage": job.stage,
      "heartbeat": True,
      "elapsed_seconds": elapsed,
    }
    try:
      snapshot = record_job_resource_snapshot(job, f"heartbeat_{phase}")
      event["resource_latest"] = snapshot
    except Exception:
      pass
    push_event(job, event)
  except Exception:
    pass


class JobCancelled(RuntimeError):
  def __init__(self, process: subprocess.CompletedProcess[str]):
    super().__init__("推理任务已取消。")
    self.process = process

def get_allowed_origins() -> list[str] | None:
  raw = os.environ.get("SEGMENTATION_ALLOWED_ORIGINS", "").strip()
  if not raw:
    return None
  origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
  return origins or None


allowed_origins = get_allowed_origins()
app = FastAPI(title="Segmentation GUI nnUNetv2 Bridge")
app.add_middleware(
  CORSMiddleware,
  allow_origins=allowed_origins or [],
  allow_origin_regex=None if allowed_origins else r"http://(127\.0\.0\.1|localhost):\d+",
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)


def read_labels() -> list[dict[str, Any]]:
  checkpoint_args = load_checkpoint_init_args()
  checkpoint_dataset_json = checkpoint_args.get("dataset_json") if checkpoint_args else None
  if isinstance(checkpoint_dataset_json, dict):
    data = checkpoint_dataset_json
  elif FLARE_DATASET_JSON.exists():
    data = json.loads(FLARE_DATASET_JSON.read_text(encoding="utf-8"))
  else:
    return [
      {"label": 1, "id": "liver", "nameZh": "肝脏", "color": "#4fd1a5"},
      {"label": 2, "id": "right-kidney", "nameZh": "右肾", "color": "#7cc7ff"},
      {"label": 3, "id": "spleen", "nameZh": "脾脏", "color": "#ef8aa8"},
      {"label": 4, "id": "pancreas", "nameZh": "胰腺", "color": "#f4b95f"},
      {"label": 5, "id": "aorta", "nameZh": "主动脉", "color": "#ff6b6b"},
      {"label": 6, "id": "ivc", "nameZh": "下腔静脉", "color": "#8ec5ff"},
      {"label": 7, "id": "right-adrenal-gland", "nameZh": "右肾上腺", "color": "#f28c28"},
      {"label": 8, "id": "left-adrenal-gland", "nameZh": "左肾上腺", "color": "#d47cff"},
      {"label": 9, "id": "gallbladder", "nameZh": "胆囊", "color": "#a5e567"},
      {"label": 10, "id": "esophagus", "nameZh": "食管", "color": "#ffd166"},
      {"label": 11, "id": "stomach", "nameZh": "胃", "color": "#b8a2ff"},
      {"label": 12, "id": "duodenum", "nameZh": "十二指肠", "color": "#ffb86b"},
      {"label": 13, "id": "left-kidney", "nameZh": "左肾", "color": "#65d6ad"},
    ]
  colors = ["#4fd1a5", "#7cc7ff", "#ef8aa8", "#f4b95f", "#ff6b6b", "#8ec5ff", "#a5e567", "#b8a2ff", "#ffb86b", "#65d6ad", "#d47cff", "#f28c28", "#70d6ff", "#c8e77d", "#ffa8d1"]
  zh_names = {
    "liver": "肝脏",
    "right_kidney": "右肾",
    "right kidney": "右肾",
    "left_kidney": "左肾",
    "left kidney": "左肾",
    "spleen": "脾脏",
    "pancreas": "胰腺",
    "aorta": "主动脉",
    "postcava": "下腔静脉",
    "inferior vena cava": "下腔静脉",
    "right_adrenal_gland": "右肾上腺",
    "right adrenal gland": "右肾上腺",
    "left_adrenal_gland": "左肾上腺",
    "left adrenal gland": "左肾上腺",
    "gall_bladder": "胆囊",
    "gallbladder": "胆囊",
    "esophagus": "食管",
    "stomach": "胃",
    "duodenum": "十二指肠",
    "bladder": "膀胱",
    "prostate_or_uterus": "前列腺/子宫",
  }
  canonical_ids = {
    "right_kidney": "right-kidney",
    "left_kidney": "left-kidney",
    "gall_bladder": "gallbladder",
    "postcava": "ivc",
    "inferior vena cava": "ivc",
    "right_adrenal_gland": "right-adrenal-gland",
    "left_adrenal_gland": "left-adrenal-gland",
    "prostate_or_uterus": "prostate-or-uterus",
  }
  labels = []
  for index, (name, label) in enumerate(data.get("labels", {}).items()):
    if int(label) == 0:
      continue
    organ_id = canonical_ids.get(str(name), str(name).replace(" ", "-").replace("_", "-"))
    labels.append({
      "label": int(label),
      "id": organ_id,
      "nameZh": zh_names.get(str(name), str(name)),
      "nameEn": str(name),
      "color": colors[index % len(colors)],
    })
  return labels


def round_metric(value: float | None) -> float | None:
  if value is None:
    return None
  return round(float(value), 6)


def dice_from_counts(intersection: int, prediction_count: int, reference_count: int) -> float | None:
  denominator = prediction_count + reference_count
  if denominator == 0:
    return None
  return 2 * intersection / denominator


def compute_label_metrics(
  prediction: Any,
  reference: Any,
  labels: list[dict[str, Any]],
  sample_id: str = "amos_0117",
) -> dict[str, Any]:
  import numpy as np

  prediction_array = np.asarray(prediction)
  reference_array = np.asarray(reference)
  if prediction_array.shape != reference_array.shape:
    return {
      "status": "unavailable",
      "sample_id": sample_id,
      "accepted": False,
      "mean_dice": None,
      "min_dice": None,
      "foreground_dice": None,
      "message": f"预测结果尺寸 {prediction_array.shape} 与标准答案尺寸 {reference_array.shape} 不一致，无法计算 Dice。",
      "thresholds": {
        "mean_dice": VALIDATION_MEAN_DICE_THRESHOLD,
        "min_label_dice": VALIDATION_MIN_DICE_THRESHOLD,
      },
      "labels": [],
    }

  label_metrics = []
  dice_values: list[float] = []
  for item in labels:
    label_value = int(item["label"])
    prediction_mask = prediction_array == label_value
    reference_mask = reference_array == label_value
    prediction_count = int(prediction_mask.sum())
    reference_count = int(reference_mask.sum())
    intersection = int((prediction_mask & reference_mask).sum())
    dice = dice_from_counts(intersection, prediction_count, reference_count)
    if dice is not None:
      dice_values.append(dice)
    label_metrics.append({
      "label": label_value,
      "name": item.get("nameZh") or item.get("nameEn") or f"Label {label_value}",
      "dice": round_metric(dice),
      "prediction_voxels": prediction_count,
      "reference_voxels": reference_count,
      "intersection_voxels": intersection,
    })

  foreground_prediction = prediction_array > 0
  foreground_reference = reference_array > 0
  foreground_dice = dice_from_counts(
    int((foreground_prediction & foreground_reference).sum()),
    int(foreground_prediction.sum()),
    int(foreground_reference.sum()),
  )
  mean_dice = sum(dice_values) / len(dice_values) if dice_values else None
  min_dice = min(dice_values) if dice_values else None
  accepted = (
    mean_dice is not None and
    min_dice is not None and
    mean_dice >= VALIDATION_MEAN_DICE_THRESHOLD and
    min_dice >= VALIDATION_MIN_DICE_THRESHOLD
  )
  return {
    "status": "passed" if accepted else "review",
    "sample_id": sample_id,
    "accepted": accepted,
    "mean_dice": round_metric(mean_dice),
    "min_dice": round_metric(min_dice),
    "foreground_dice": round_metric(foreground_dice),
    "message": "标准答案验证通过。" if accepted else "标准答案验证未达阈值，建议人工复核。",
    "thresholds": {
      "mean_dice": VALIDATION_MEAN_DICE_THRESHOLD,
      "min_label_dice": VALIDATION_MIN_DICE_THRESHOLD,
    },
    "labels": label_metrics,
  }


def unavailable_validation(message: str) -> dict[str, Any]:
  return {
    "status": "unavailable",
    "sample_id": "amos_0117",
    "accepted": False,
    "mean_dice": None,
    "min_dice": None,
    "foreground_dice": None,
    "message": message,
    "thresholds": {
      "mean_dice": VALIDATION_MEAN_DICE_THRESHOLD,
      "min_label_dice": VALIDATION_MIN_DICE_THRESHOLD,
    },
    "labels": [],
  }


def write_validation_summary(output_dir: Path, validation: dict[str, Any]) -> Path:
  output_dir.mkdir(parents=True, exist_ok=True)
  summary_path = output_dir / "validation_summary.json"
  summary_path.write_text(
    json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
  )
  return summary_path


def get_current_process_memory_bytes() -> int | None:
  try:
    if os.name == "nt":
      import ctypes

      class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
          ("cb", ctypes.c_ulong),
          ("PageFaultCount", ctypes.c_ulong),
          ("PeakWorkingSetSize", ctypes.c_size_t),
          ("WorkingSetSize", ctypes.c_size_t),
          ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
          ("QuotaPagedPoolUsage", ctypes.c_size_t),
          ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
          ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
          ("PagefileUsage", ctypes.c_size_t),
          ("PeakPagefileUsage", ctypes.c_size_t),
        ]

      counters = PROCESS_MEMORY_COUNTERS()
      counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
      handle = ctypes.windll.kernel32.GetCurrentProcess()
      ok = ctypes.windll.psapi.GetProcessMemoryInfo(
        handle,
        ctypes.byref(counters),
        ctypes.sizeof(counters),
      )
      return int(counters.WorkingSetSize) if ok else None

    import resource

    # Linux reports KiB, macOS reports bytes. The app is developed on Windows,
    # but this keeps summaries useful when the backend is run elsewhere.
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(usage if sys.platform == "darwin" else usage * 1024)
  except Exception:
    return None


def read_gpu_snapshot() -> dict[str, Any] | None:
  command = os.environ.get("SEGMENTATION_NVIDIA_SMI", "nvidia-smi")
  try:
    result = subprocess.run(
      [
        command,
        "--query-gpu=name,memory.used,memory.total,utilization.gpu",
        "--format=csv,noheader,nounits",
      ],
      capture_output=True,
      text=True,
      encoding="utf-8",
      errors="replace",
      timeout=2,
    )
  except Exception:
    return None
  if result.returncode != 0 or not result.stdout.strip():
    return None
  parts = [part.strip() for part in result.stdout.strip().splitlines()[0].split(",")]
  if len(parts) < 4:
    return None
  gpu: dict[str, Any] = {"name": parts[0]}
  if parts[1].replace(".", "", 1).isdigit():
    gpu["memory_used_mib"] = int(float(parts[1]))
  if parts[2].replace(".", "", 1).isdigit():
    gpu["memory_total_mib"] = int(float(parts[2]))
  if parts[3].replace(".", "", 1).isdigit():
    gpu["utilization_gpu_percent"] = int(float(parts[3]))
  return gpu


def collect_runtime_resource_snapshot(phase: str, process_pid: int | None = None) -> dict[str, Any]:
  snapshot: dict[str, Any] = {
    "phase": phase,
    "timestamp": round(time.time(), 3),
    "device": os.environ.get("SEGMENTATION_DEVICE", "cpu"),
    "server_pid": os.getpid(),
  }
  if process_pid is not None:
    snapshot["process_pid"] = process_pid
  try:
    usage = shutil.disk_usage(WORK_DIR)
    snapshot["disk_total_bytes"] = usage.total
    snapshot["disk_used_bytes"] = usage.used
    snapshot["disk_free_bytes"] = usage.free
  except Exception:
    pass
  memory_bytes = get_current_process_memory_bytes()
  if memory_bytes is not None:
    snapshot["server_process_memory_bytes"] = memory_bytes
  gpu = read_gpu_snapshot()
  if gpu:
    snapshot["gpu"] = gpu
  return snapshot


def record_job_resource_snapshot(job: Job, phase: str) -> dict[str, Any]:
  process_pid = job.process.pid if job.process is not None else None
  snapshot = collect_runtime_resource_snapshot(phase, process_pid)
  with jobs_lock:
    job.resource_snapshots.append(snapshot)
  return snapshot


def write_resource_snapshots(output_dir: Path, snapshots: list[dict[str, Any]]) -> Path | None:
  if not snapshots:
    return None
  output_dir.mkdir(parents=True, exist_ok=True)
  resource_path = output_dir / "resource_snapshots.json"
  resource_path.write_text(
    json.dumps(snapshots, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
  )
  return resource_path


def get_job_duration_seconds(job: Job) -> float | None:
  if job.started_at is None:
    return None
  end_time = job.completed_at if job.completed_at is not None else time.time()
  return round(max(0.0, end_time - job.started_at), 3)


def get_result_size_bytes(job: Job) -> int | None:
  if job.result_path is None or not job.result_path.exists():
    return None
  return job.result_path.stat().st_size


def start_job_phase(job: Job, phase: str) -> None:
  job.phase_started_at[phase] = time.perf_counter()


def finish_job_phase(job: Job, phase: str) -> None:
  started_at = job.phase_started_at.pop(phase, None)
  if started_at is None:
    return
  job.phase_timings[phase] = round(max(0.0, time.perf_counter() - started_at), 3)


def build_job_summary(job: Job) -> dict[str, Any]:
  resource_latest = job.resource_snapshots[-1] if job.resource_snapshots else None
  return {
    "job_id": job.id,
    "status": job.status,
    "progress": job.progress,
    "stage": job.stage,
    "mode": job.mode,
    "runtime_target": job.runtime_target,
    "error": job.error,
    "started_at": job.started_at,
    "completed_at": job.completed_at,
    "duration_seconds": get_job_duration_seconds(job),
    "input_sha256": job.input_sha256,
    "checkpoint_sha256": job.checkpoint_sha256,
    "cache_key": job.cache_key,
    "cached_result": job.cached_result,
    "cache_source_job_id": job.cache_source_job_id,
    "inference_profile": job.inference_options.get("profile") if isinstance(job.inference_options, dict) else None,
    "inference_options": job.inference_options,
    "phase_timings": job.phase_timings,
    "result_ready": job.status == "succeeded" and job.result_path is not None and job.result_path.exists(),
    "result_path": str(job.result_path) if job.result_path else None,
    "result_size_bytes": get_result_size_bytes(job),
    "log_tail": job.log_tail,
    "process_log_path": str(job.process_log_path) if job.process_log_path else None,
    "resource_snapshots": job.resource_snapshots,
    "resource_latest": resource_latest,
    "resource_log_path": str(job.resource_log_path) if job.resource_log_path else None,
    "cancel_requested": job.cancel_requested,
    "label_path": str(job.label_path) if job.label_path else None,
    "validation": job.validation,
  }


def write_job_summary(output_dir: Path, job: Job) -> Path:
  output_dir.mkdir(parents=True, exist_ok=True)
  resource_log_path = write_resource_snapshots(output_dir, job.resource_snapshots)
  if resource_log_path is not None:
    job.resource_log_path = resource_log_path
  summary_path = output_dir / "job_summary.json"
  summary_path.write_text(
    json.dumps(build_job_summary(job), ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
  )
  return summary_path


def run_process_with_cancel(job: Job, command: list[str]) -> subprocess.CompletedProcess[str]:
  process = subprocess.Popen(
    command,
    cwd=str(PROJECT_ROOT),
    env=get_predict_environment(),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    errors="replace",
  )
  return wait_for_process_with_cancel(job, process, command, "nnunet_process")


def run_command_with_cancel(
  job: Job,
  command: list[str],
  *,
  env: dict[str, str] | None = None,
  cwd: Path | None = None,
  heartbeat_phase: str = "nnunet_process",
) -> subprocess.CompletedProcess[str]:
  process = subprocess.Popen(
    command,
    cwd=str(cwd or PROJECT_ROOT),
    env=env or get_predict_environment(),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    errors="replace",
  )
  return wait_for_process_with_cancel(job, process, command, heartbeat_phase)


def run_parallel_processes_with_cancel(
  job: Job,
  commands: list[tuple[str, list[str], dict[str, str]]],
  *,
  heartbeat_phase: str,
) -> list[subprocess.CompletedProcess[str]]:
  processes: list[tuple[str, list[str], subprocess.Popen[str]]] = []
  for label, command, env in commands:
    process = subprocess.Popen(
      command,
      cwd=str(PROJECT_ROOT),
      env=env,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
      encoding="utf-8",
      errors="replace",
    )
    processes.append((label, command, process))
  with jobs_lock:
    job.child_processes = [process for _label, _command, process in processes]
  record_job_resource_snapshot(job, f"{heartbeat_phase}_started")
  last_heartbeat = time.monotonic()
  completed: dict[str, subprocess.CompletedProcess[str]] = {}
  try:
    while len(completed) < len(processes):
      for label, command, process in processes:
        if label in completed:
          continue
        return_code = process.poll()
        if return_code is None:
          continue
        stdout, stderr = process.communicate()
        result = subprocess.CompletedProcess(command, return_code, stdout, stderr)
        completed[label] = result
        if result.returncode != 0:
          for _label, _command, running_process in processes:
            if running_process is not process and running_process.poll() is None:
              running_process.terminate()
          for remaining_label, remaining_command, remaining_process in processes:
            if remaining_label in completed:
              continue
            try:
              remaining_stdout, remaining_stderr = remaining_process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
              remaining_process.kill()
              remaining_stdout, remaining_stderr = remaining_process.communicate()
            completed[remaining_label] = subprocess.CompletedProcess(
              remaining_command,
              remaining_process.returncode if remaining_process.returncode is not None else -1,
              remaining_stdout,
              remaining_stderr,
            )
          return [completed[item_label] for item_label, _item_command, _item_process in processes if item_label in completed]
      if len(completed) == len(processes):
        break
      now = time.monotonic()
      if now - last_heartbeat >= HEARTBEAT_INTERVAL:
        last_heartbeat = now
        push_heartbeat(job, heartbeat_phase)
      if job.cancel_requested:
        for _label, _command, process in processes:
          if process.poll() is None:
            process.terminate()
        results: list[subprocess.CompletedProcess[str]] = []
        for _label, command, process in processes:
          try:
            stdout, stderr = process.communicate(timeout=5)
          except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
          results.append(subprocess.CompletedProcess(
            command,
            process.returncode if process.returncode is not None else -1,
            stdout,
            stderr,
          ))
        raise JobCancelled(subprocess.CompletedProcess(
          args=["server-multi-fold-predict"],
          returncode=-1,
          stdout="",
          stderr="推理任务已取消",
        ))
      time.sleep(0.5)
    return [completed[label] for label, _command, _process in processes]
  finally:
    with jobs_lock:
      job.child_processes = []


def write_process_log(output_dir: Path, process: subprocess.CompletedProcess[str]) -> tuple[Path, str]:
  return write_multi_process_log(output_dir, [("process", process)])


def write_multi_process_log(
  output_dir: Path,
  sections: list[tuple[str, subprocess.CompletedProcess[str]]],
) -> tuple[Path, str]:
  output_dir.mkdir(parents=True, exist_ok=True)
  log_path = output_dir / "nnunetv2_process.log"
  chunks: list[str] = []
  for label, process in sections:
    chunks.extend([
      f"=== {label} ===",
      f"COMMAND: {' '.join(str(part) for part in process.args)}",
      f"RETURN_CODE: {process.returncode}",
      "",
      "STDOUT:",
      process.stdout or "",
      "",
      "STDERR:",
      process.stderr or "",
      "",
    ])
  log_path.write_text("\n".join(chunks).rstrip() + "\n", encoding="utf-8")
  tail_source = sections[-1][1] if sections else subprocess.CompletedProcess([], 0, "", "")
  return log_path, get_process_tail(tail_source)



def wait_for_process_with_cancel(job: Job, process: subprocess.Popen[str], command: list[str], heartbeat_phase: str) -> subprocess.CompletedProcess[str]:
  with jobs_lock:
    job.process = process
  record_job_resource_snapshot(job, "process_started")
  last_heartbeat = time.monotonic()
  try:
    while True:
      try:
        stdout, stderr = process.communicate(timeout=0.5)
        completed = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        if job.cancel_requested:
          raise JobCancelled(completed)
        return completed
      except subprocess.TimeoutExpired:
        now = time.monotonic()
        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
          last_heartbeat = now
          push_heartbeat(job, heartbeat_phase)
        if job.cancel_requested:
          if process.poll() is None:
            process.terminate()
          try:
            stdout, stderr = process.communicate(timeout=5)
          except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
          raise JobCancelled(subprocess.CompletedProcess(
            command,
            process.returncode if process.returncode is not None else -1,
            stdout,
            stderr,
          ))
  finally:
    with jobs_lock:
      if job.process is process:
        job.process = None


def request_job_cancel(job_id: str) -> Job | None:
  with jobs_lock:
    job = jobs.get(job_id)
    if not job:
      return None
    if job.status in {"succeeded", "failed", "cancelled"}:
      return job
    job.cancel_requested = True
    job.status = "cancelling"
    job.stage = "正在取消推理任务"
    process = job.process
    child_processes = list(job.child_processes)
  for child in child_processes:
    if child.poll() is None:
      child.terminate()
  if process and process.poll() is None:
    process.terminate()
  push_event(job, {"type": "progress", "progress": job.progress, "stage": "正在取消本地 nnUNetv2 任务" if job.runtime_target == "local" else "正在取消服务器 5-fold 推理任务"})
  return job


def get_persisted_job_output_dir(job_id: str) -> Path | None:
  if not job_id or Path(job_id).name != job_id or "/" in job_id or "\\" in job_id:
    return None
  output_dir = WORK_DIR / job_id / "output"
  try:
    output_dir.resolve().relative_to(WORK_DIR.resolve())
  except ValueError:
    return None
  return output_dir


def read_persisted_job_summary(job_id: str) -> dict[str, Any] | None:
  output_dir = get_persisted_job_output_dir(job_id)
  if output_dir is None:
    return None
  summary_path = output_dir / "job_summary.json"
  if not summary_path.exists():
    candidates = sorted(output_dir.glob(f"{job_id}*.nii*"))
    if not candidates:
      return None
    result_path = candidates[0]
    process_log_path = output_dir / "nnunetv2_process.log"
    log_tail = None
    if process_log_path.exists():
      log_lines = [line for line in process_log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
      log_tail = "\n".join(log_lines[-8:]) if log_lines else None
    validation = None
    validation_path = output_dir / "validation_summary.json"
    if validation_path.exists():
      validation = json.loads(validation_path.read_text(encoding="utf-8"))
    resource_log_path = output_dir / "resource_snapshots.json"
    resource_snapshots = []
    if resource_log_path.exists():
      parsed_snapshots = json.loads(resource_log_path.read_text(encoding="utf-8"))
      if isinstance(parsed_snapshots, list):
        resource_snapshots = parsed_snapshots
    input_candidates = sorted((WORK_DIR / job_id / "input").glob(f"{job_id}_0000.nii*"))
    started_at = input_candidates[0].stat().st_mtime if input_candidates else None
    completed_at = result_path.stat().st_mtime
    duration_seconds = round(max(0.0, completed_at - started_at), 3) if started_at is not None else None
    return {
      "job_id": job_id,
      "status": "succeeded",
      "progress": 100,
      "stage": "历史推理结果已生成",
      "mode": "real-nnunetv2",
      "error": None,
      "started_at": started_at,
      "completed_at": completed_at,
      "duration_seconds": duration_seconds,
      "duration_source": "file_timestamps" if duration_seconds is not None else "unavailable",
      "input_sha256": None,
      "checkpoint_sha256": None,
      "cache_key": None,
      "cached_result": False,
      "cache_source_job_id": None,
      "result_ready": True,
      "result_path": str(result_path),
      "result_size_bytes": result_path.stat().st_size,
      "log_tail": log_tail,
      "process_log_path": str(process_log_path) if process_log_path.exists() else None,
      "resource_snapshots": resource_snapshots,
      "resource_latest": resource_snapshots[-1] if resource_snapshots else None,
      "resource_log_path": str(resource_log_path) if resource_log_path.exists() else None,
      "validation": validation,
    }
  summary = json.loads(summary_path.read_text(encoding="utf-8"))
  if not isinstance(summary, dict):
    return None
  if summary.get("inference_profile") is None and isinstance(summary.get("inference_options"), dict):
    summary["inference_profile"] = summary["inference_options"].get("profile")

  result_path = Path(str(summary.get("result_path"))) if summary.get("result_path") else None
  result_ready = bool(summary.get("status") == "succeeded" and result_path and result_path.exists())
  summary["result_ready"] = result_ready
  summary["result_size_bytes"] = result_path.stat().st_size if result_ready and result_path else None

  if summary.get("validation") is None:
    validation_path = output_dir / "validation_summary.json"
    if validation_path.exists():
      summary["validation"] = json.loads(validation_path.read_text(encoding="utf-8"))

  resource_log_path = output_dir / "resource_snapshots.json"
  if summary.get("resource_snapshots") is None and resource_log_path.exists():
    parsed_snapshots = json.loads(resource_log_path.read_text(encoding="utf-8"))
    if isinstance(parsed_snapshots, list):
      summary["resource_snapshots"] = parsed_snapshots
  if summary.get("resource_latest") is None and isinstance(summary.get("resource_snapshots"), list) and summary["resource_snapshots"]:
    summary["resource_latest"] = summary["resource_snapshots"][-1]
  if summary.get("resource_log_path") is None and resource_log_path.exists():
    summary["resource_log_path"] = str(resource_log_path)

  return summary


def get_persisted_result_path(job_id: str) -> Path | None:
  summary = read_persisted_job_summary(job_id)
  if not summary or not summary.get("result_ready"):
    return None
  result_path = Path(str(summary.get("result_path")))
  return result_path if result_path.exists() else None


def file_sha256(path: Path) -> str:
  digest = hashlib.sha256()
  with path.open("rb") as source:
    for chunk in iter(lambda: source.read(1024 * 1024), b""):
      digest.update(chunk)
  return digest.hexdigest()


def same_file_content(left: Path, right: Path) -> bool:
  if not left.exists() or not right.exists():
    return False
  try:
    if os.path.samefile(left, right):
      return True
  except OSError:
    pass
  if left.stat().st_size != right.stat().st_size:
    return False
  left_stat = left.stat()
  right_stat = right.stat()
  if left_stat.st_mtime_ns == right_stat.st_mtime_ns:
    return True
  return stable_file_sha256(left) == stable_file_sha256(right)


def get_checkpoint_source() -> Path:
  return PROJECT_CHECKPOINT if PROJECT_CHECKPOINT.exists() else FLARE_CHECKPOINT


@lru_cache(maxsize=16)
def file_sha256_cached(path: str, size: int, mtime_ns: int) -> str:
  return file_sha256(Path(path))


def stable_file_sha256(path: Path) -> str:
  stat = path.stat()
  return file_sha256_cached(str(path), stat.st_size, stat.st_mtime_ns)


@lru_cache(maxsize=4)
def load_checkpoint_init_args_cached(checkpoint_path: str, size: int, mtime_ns: int) -> dict[str, Any]:
  import torch

  checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
  init_args = checkpoint.get("init_args", {})
  return init_args if isinstance(init_args, dict) else {}


def load_checkpoint_init_args() -> dict[str, Any] | None:
  checkpoint_source = get_checkpoint_source()
  if not checkpoint_source.exists():
    return None
  stat = checkpoint_source.stat()
  return load_checkpoint_init_args_cached(str(checkpoint_source), stat.st_size, stat.st_mtime_ns)


def get_model_file_ending(checkpoint_args: dict[str, Any] | None = None) -> str:
  dataset_json = checkpoint_args.get("dataset_json") if checkpoint_args else None
  if isinstance(dataset_json, dict):
    ending = dataset_json.get("file_ending")
    if isinstance(ending, str) and ending.lower() in {".nii", ".nii.gz"}:
      return ending.lower()
  if FLARE_DATASET_JSON.exists():
    try:
      ending = json.loads(FLARE_DATASET_JSON.read_text(encoding="utf-8")).get("file_ending")
      if isinstance(ending, str) and ending.lower() in {".nii", ".nii.gz"}:
        return ending.lower()
    except (OSError, json.JSONDecodeError):
      pass
  return ".nii.gz"


def copy_upload_to_nnunet_input(upload: UploadFile, target_path: Path, target_file_ending: str) -> None:
  source_name = (upload.filename or "").lower()
  if target_file_ending == ".nii.gz" and not source_name.endswith(".nii.gz"):
    with target_path.open("wb") as raw_target:
      with gzip.GzipFile(fileobj=raw_target, mode="wb", mtime=0) as gz_target:
        shutil.copyfileobj(upload.file, gz_target)
    return
  with target_path.open("wb") as target:
    shutil.copyfileobj(upload.file, target)


def prepare_runtime_model_dir() -> Path:
  checkpoint_source = get_checkpoint_source()
  if checkpoint_source == FLARE_CHECKPOINT:
    return FLARE_MODEL_DIR
  RUNTIME_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
  init_args = load_checkpoint_init_args() or {}
  checkpoint_dataset_json = init_args.get("dataset_json")
  checkpoint_plans = init_args.get("plans")
  if isinstance(checkpoint_dataset_json, dict) and isinstance(checkpoint_plans, dict):
    (RUNTIME_MODEL_DIR / "dataset.json").write_text(json.dumps(checkpoint_dataset_json, ensure_ascii=False, indent=2), encoding="utf-8")
    (RUNTIME_MODEL_DIR / "plans.json").write_text(json.dumps(checkpoint_plans, ensure_ascii=False, indent=2), encoding="utf-8")
  else:
    shutil.copy2(FLARE_DATASET_JSON, RUNTIME_MODEL_DIR / "dataset.json")
    shutil.copy2(FLARE_PLANS_JSON, RUNTIME_MODEL_DIR / "plans.json")
  if not same_file_content(checkpoint_source, RUNTIME_CHECKPOINT):
    if RUNTIME_CHECKPOINT.exists():
      RUNTIME_CHECKPOINT.unlink()
    try:
      os.link(checkpoint_source, RUNTIME_CHECKPOINT)
    except OSError:
      shutil.copy2(checkpoint_source, RUNTIME_CHECKPOINT)
  return RUNTIME_MODEL_DIR


def is_debug_original_upload(input_path: Path) -> bool:
  if not DEBUG_ORIGINAL.exists() or not input_path.exists():
    return False
  if input_path.stat().st_size != DEBUG_ORIGINAL.stat().st_size:
    return False
  return file_sha256(input_path) == file_sha256(DEBUG_ORIGINAL)


def validate_against_debug_label(prediction_path: Path) -> dict[str, Any]:
  reference_path = DEBUG_LABEL if DEBUG_LABEL.exists() else FALLBACK_LABEL
  if not reference_path.exists():
    return unavailable_validation("标准答案标签不存在，无法验证推理效果。")
  try:
    import nibabel as nib
    import numpy as np
  except Exception as exc:
    return unavailable_validation(f"当前 Python 环境缺少 NIfTI 验证依赖：{exc}")
  prediction = np.asanyarray(nib.load(str(prediction_path)).dataobj)
  reference = np.asanyarray(nib.load(str(reference_path)).dataobj)
  return compute_label_metrics(prediction, reference, read_labels())


def validate_against_custom_label(prediction_path: Path, label_path: Path, labels: list[dict[str, Any]], sample_id: str = "custom") -> dict[str, Any]:
  try:
    import nibabel as nib
    import numpy as np
  except Exception as exc:
    return unavailable_validation(f"当前 Python 环境缺少 NIfTI 验证依赖：{exc}")
  try:
    prediction = np.asanyarray(nib.load(str(prediction_path)).dataobj)
    reference = np.asanyarray(nib.load(str(label_path)).dataobj)
  except Exception as exc:
    return unavailable_validation(f"无法加载预测结果或标签文件：{exc}")
  if prediction.shape != reference.shape:
    return unavailable_validation(f"预测结果尺寸 {prediction.shape} 与标签尺寸 {reference.shape} 不一致，无法计算 Dice。")
  checkpoint_labels = {int(item["label"]) for item in labels}
  reference_labels = set(np.unique(reference).astype(int)) - {0}

  # Try automatic taxonomy remap for known datasets (e.g. FLARE22 → AMOS22)
  try:
    from server.taxonomy import detect_dataset, build_remap_mapping, apply_remap
    detected = detect_dataset(reference_labels, labels)
    if detected:
      mapping = build_remap_mapping(labels, detected)
      if mapping:
        remapped_reference = apply_remap(reference, mapping)
        result = compute_label_metrics(prediction, remapped_reference, labels, sample_id=sample_id)
        result["taxonomy_match"] = True
        result["remap_applied"] = True
        result["remap_source"] = detected
        result["remap_mapping"] = {str(k): v for k, v in mapping.items()}
        result["message"] = f"已自动重映射标签 ID（{detected} → 当前模型）。" + (result.get("message") or "")
        return result
  except Exception as remap_exc:
    print(f"[taxonomy] remap failed, falling through: {remap_exc}")

  if not reference_labels.intersection(checkpoint_labels):
    return {
      **unavailable_validation("标签 ID 与当前 checkpoint 定义不匹配，需要离线 taxonomy remap。"),
      "taxonomy_match": False,
    }
  result = compute_label_metrics(prediction, reference, labels, sample_id=sample_id)
  result["taxonomy_match"] = True
  return result


def model_ready() -> bool:
  return bool(get_model_state()["ready"])


def get_model_state(runtime_target: str | None = None) -> dict[str, Any]:
  checkpoint_source = get_checkpoint_source()
  checkpoint_args = load_checkpoint_init_args()
  checkpoint_plans = checkpoint_args.get("plans") if checkpoint_args else None
  inference_options = get_inference_options()
  server_config = get_server_inference_config()
  normalized_runtime_target = normalize_runtime_target(runtime_target)
  server_required_files = []
  if normalized_runtime_target == "server":
    server_required_files = [
      ("server_evaluate_full.py", server_config.evaluate_script),
      ("server_dataset.json", server_config.dataset_json),
    ]
  required_files = [
    ("dataset.json", FLARE_DATASET_JSON),
    ("plans.json", FLARE_PLANS_JSON),
    ("checkpoint_best.pth", checkpoint_source),
    ("nnUNetv2_python", NNUNET_PYTHON_COMMAND),
    *[(name, path) for name, path in server_required_files if path is not None],
  ]
  missing = [name for name, path in required_files if not path.exists()]
  ready = not missing
  return {
    "ready": ready,
    "status": "ready" if ready else "incomplete",
    "mode": "real-nnunetv2" if ready else "unavailable",
    "runtime_target": normalized_runtime_target,
    "missing": missing,
    "model_dir": str(FLARE_MODEL_DIR),
    "dataset_json": str(FLARE_DATASET_JSON),
    "plans_json": str(FLARE_PLANS_JSON),
    "checkpoint": str(FLARE_CHECKPOINT),
    "checkpoint_source": str(checkpoint_source),
    "checkpoint_source_exists": checkpoint_source.exists(),
    "checkpoint_source_matches_model_folder": same_file_content(checkpoint_source, FLARE_CHECKPOINT),
    "checkpoint_in_model_folder": str(FLARE_CHECKPOINT),
    "checkpoint_runtime": str(RUNTIME_CHECKPOINT),
    "predict_command": str(NNUNET_PYTHON_COMMAND),
    "predict_entrypoint": "nnunetv2.inference.predict_from_raw_data:predict_entry_point_modelfolder",
    "predict_wrapper": str(NNUNET_PREDICT_COMMAND),
    "nnunet_raw": str(NNUNET_RAW),
    "nnunet_preprocessed": str(NNUNET_PREPROCESSED),
    "nnunet_results": str(NNUNET_RESULTS),
    "predict_device": get_predict_device(),
    "checkpoint_dataset_name": checkpoint_plans.get("dataset_name") if isinstance(checkpoint_plans, dict) else None,
    "checkpoint_configuration": checkpoint_args.get("configuration") if checkpoint_args else None,
    "model_file_ending": get_model_file_ending(checkpoint_args),
    "labels_source": "checkpoint" if checkpoint_args and checkpoint_args.get("dataset_json") else "dataset.json" if FLARE_DATASET_JSON.exists() else "fallback",
    "confidence_threshold_effective": False,
    "persistent_worker_enabled": persistent_worker_enabled(),
    "persistent_worker_running": persistent_worker_process is not None and persistent_worker_process.poll() is None,
    "predict_workers": {
      "preprocess": get_predict_worker_counts()[0],
      "export": get_predict_worker_counts()[1],
    },
    "server_inference": {
      "dataset_id": server_config.dataset_id,
      "configuration": server_config.configuration,
      "plans": server_config.plans,
      "folds": list(server_config.folds),
      "gpus": list(server_config.gpus),
      "output_root": str(server_config.output_root),
      "nnunet_raw": str(server_config.nnunet_raw),
      "nnunet_preprocessed": str(server_config.nnunet_preprocessed),
      "nnunet_results": str(server_config.nnunet_results),
      "evaluate_script": str(server_config.evaluate_script) if server_config.evaluate_script else "",
      "dataset_json": str(server_config.dataset_json) if server_config.dataset_json else "",
    },
    "inference_options": inference_options,
  }


def get_predict_device() -> str:
  device = os.environ.get("SEGMENTATION_DEVICE", "cuda").strip().lower()
  return device if device in {"cpu", "cuda", "mps"} else "cuda"


def normalize_runtime_target(value: str | None = None) -> str:
  target = (value or os.environ.get("SEGMENTATION_RUNTIME_TARGET", "local")).strip().lower()
  return target if target in {"local", "server"} else "local"


def get_env_int(name: str, default: int, minimum: int = 1, maximum: int = 8) -> int:
  try:
    value = int(os.environ.get(name, str(default)).strip())
  except (TypeError, ValueError):
    value = default
  return max(minimum, min(maximum, value))


def get_env_float(name: str, default: float, minimum: float, maximum: float) -> float:
  try:
    value = float(os.environ.get(name, str(default)).strip())
  except (TypeError, ValueError):
    value = default
  return round(max(minimum, min(maximum, value)), 3)


def get_env_bool(name: str, default: bool) -> bool:
  raw = os.environ.get(name)
  if raw is None:
    return default
  normalized = raw.strip().lower()
  if normalized in {"1", "true", "yes", "on"}:
    return True
  if normalized in {"0", "false", "no", "off"}:
    return False
  return default


def normalize_inference_profile(profile: str | None = None) -> str:
  profile = (profile or os.environ.get("SEGMENTATION_INFERENCE_PROFILE", "quality")).strip().lower()
  if profile not in {"quality", "fast"}:
    profile = "quality"
  return profile


def get_inference_options(profile: str | None = None) -> dict[str, Any]:
  profile = normalize_inference_profile(profile)
  fast_profile = profile == "fast"
  return {
    "profile": profile,
    "tile_step_size": get_env_float("SEGMENTATION_TILE_STEP_SIZE", 1.0 if fast_profile else 0.5, 0.1, 1.0),
    "disable_tta": get_env_bool("SEGMENTATION_DISABLE_TTA", fast_profile),
    "not_on_device": get_env_bool("SEGMENTATION_NOT_ON_DEVICE", False),
  }


def format_cli_float(value: float) -> str:
  if float(value).is_integer():
    return str(int(value))
  return f"{value:.3f}".rstrip("0").rstrip(".")


def get_predict_worker_counts() -> tuple[int, int]:
  return (
    get_env_int("SEGMENTATION_PREPROCESS_WORKERS", 2),
    get_env_int("SEGMENTATION_EXPORT_WORKERS", 2),
  )


def get_predict_environment() -> dict[str, str]:
  env = os.environ.copy()
  env["nnUNet_raw"] = str(NNUNET_RAW)
  env["nnUNet_preprocessed"] = str(NNUNET_PREPROCESSED)
  env["nnUNet_results"] = str(NNUNET_RESULTS)
  return env


def build_predict_command(
  input_dir: Path,
  output_dir: Path,
  device: str | None = None,
  model_dir: Path | None = None,
  inference_options: dict[str, Any] | None = None,
) -> list[str]:
  model_root = model_dir or FLARE_MODEL_DIR
  preprocess_workers, export_workers = get_predict_worker_counts()
  options = inference_options or get_inference_options()
  command = [
    str(NNUNET_PYTHON_COMMAND),
    "-c",
    NNUNET_PREDICT_ENTRYPOINT,
    "-i", str(input_dir),
    "-o", str(output_dir),
    "-m", str(model_root),
    "-f", "0",
    "-chk", "checkpoint_best.pth",
    "-npp", str(preprocess_workers),
    "-nps", str(export_workers),
    "-device", device or get_predict_device(),
    "--disable_progress_bar",
  ]
  tile_step_size = float(options.get("tile_step_size", 0.5))
  if tile_step_size != 0.5:
    command.extend(["-step_size", format_cli_float(tile_step_size)])
  if bool(options.get("disable_tta", False)):
    command.append("--disable_tta")
  if bool(options.get("not_on_device", False)):
    command.append("--not_on_device")
  return command


def persistent_worker_enabled() -> bool:
  return os.environ.get("SEGMENTATION_PERSISTENT_WORKER", "").strip().lower() in {"1", "true", "yes", "on"}


def get_persistent_worker_key(model_dir: Path, inference_options: dict[str, Any] | None = None) -> tuple[str, str, str, int, int, float, bool, bool]:
  preprocess_workers, export_workers = get_predict_worker_counts()
  options = inference_options or get_inference_options()
  return (
    str(model_dir),
    get_predict_device(),
    "checkpoint_best.pth",
    preprocess_workers,
    export_workers,
    float(options.get("tile_step_size", 0.5)),
    bool(options.get("disable_tta", False)),
    bool(options.get("not_on_device", False)),
  )


def close_persistent_worker_locked() -> None:
  global persistent_worker_process, persistent_worker_key, persistent_worker_log_handle
  global persistent_worker_event_queue, persistent_worker_stdout_thread, persistent_worker_reader_process
  process = persistent_worker_process
  if process is not None and process.poll() is None:
    process.terminate()
    try:
      process.wait(timeout=5)
    except subprocess.TimeoutExpired:
      process.kill()
      process.wait(timeout=5)
  if persistent_worker_log_handle is not None:
    try:
      persistent_worker_log_handle.close()
    except OSError:
      pass
  persistent_worker_process = None
  persistent_worker_key = None
  persistent_worker_log_handle = None
  persistent_worker_event_queue = None
  persistent_worker_stdout_thread = None
  persistent_worker_reader_process = None


def ensure_persistent_worker_reader(process: Any) -> queue.Queue[str | None]:
  global persistent_worker_event_queue, persistent_worker_stdout_thread, persistent_worker_reader_process
  if process.stdout is None:
    raise RuntimeError("常驻 nnUNetv2 worker 未打开 stdout。")
  if (
    persistent_worker_reader_process is process and
    persistent_worker_event_queue is not None and
    persistent_worker_stdout_thread is not None
  ):
    return persistent_worker_event_queue
  q: queue.Queue[str | None] = queue.Queue()
  reader = threading.Thread(target=_persistent_worker_reader_thread, args=(process.stdout, q), daemon=True)
  reader.start()
  persistent_worker_reader_process = process
  persistent_worker_event_queue = q
  persistent_worker_stdout_thread = reader
  return q


def read_persistent_worker_event(process: subprocess.Popen[str]) -> dict[str, Any]:
  q = ensure_persistent_worker_reader(process)
  line = q.get()
  if not line:
    raise RuntimeError("常驻 nnUNetv2 worker 已退出。")
  try:
    event = json.loads(line)
  except json.JSONDecodeError as exc:
    raise RuntimeError(f"常驻 nnUNetv2 worker 返回了无效 JSON：{line[:200]}") from exc
  if not isinstance(event, dict):
    raise RuntimeError("常驻 nnUNetv2 worker 返回了无效事件。")
  return event


def send_persistent_worker_request(process: subprocess.Popen[str], payload: dict[str, Any]) -> None:
  if process.stdin is None:
    raise RuntimeError("常驻 nnUNetv2 worker 未打开 stdin。")
  process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
  process.stdin.flush()


def ensure_persistent_worker(model_dir: Path, inference_options: dict[str, Any] | None = None) -> subprocess.Popen[str]:
  global persistent_worker_process, persistent_worker_key, persistent_worker_log_handle
  options = inference_options or get_inference_options()
  key = get_persistent_worker_key(model_dir, options)
  if persistent_worker_process is not None and persistent_worker_process.poll() is None and persistent_worker_key == key:
    return persistent_worker_process

  close_persistent_worker_locked()
  WORK_DIR.mkdir(parents=True, exist_ok=True)
  log_path = WORK_DIR / "persistent_worker.log"
  persistent_worker_log_handle = log_path.open("a", encoding="utf-8")
  persistent_worker_process = subprocess.Popen(
    [str(NNUNET_PYTHON_COMMAND), str(PERSISTENT_WORKER_SCRIPT)],
    cwd=str(PROJECT_ROOT),
    env=get_predict_environment(),
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=persistent_worker_log_handle,
    text=True,
    encoding="utf-8",
    errors="replace",
  )
  persistent_worker_key = key
  preprocess_workers, export_workers = get_predict_worker_counts()
  send_persistent_worker_request(persistent_worker_process, {
    "type": "init",
    "model_dir": str(model_dir),
    "device": get_predict_device(),
    "checkpoint": "checkpoint_best.pth",
    "preprocess_workers": preprocess_workers,
    "export_workers": export_workers,
    "tile_step_size": options.get("tile_step_size", 0.5),
    "disable_tta": bool(options.get("disable_tta", False)),
    "not_on_device": bool(options.get("not_on_device", False)),
  })
  event = read_persistent_worker_event(persistent_worker_process)
  if event.get("type") != "ready":
    close_persistent_worker_locked()
    raise RuntimeError(str(event.get("message") or event))
  return persistent_worker_process


def _persistent_worker_reader_thread(stdout: Any, q: queue.Queue[str | None]) -> None:
  try:
    for line in stdout:
      q.put(line)
  except Exception:
    pass
  finally:
    q.put(None)


def _read_worker_event_with_heartbeat(job: Job, process: subprocess.Popen[str]) -> dict[str, Any]:
  q = ensure_persistent_worker_reader(process)
  while True:
    try:
      line = q.get(timeout=HEARTBEAT_INTERVAL)
    except queue.Empty:
      push_heartbeat(job, "persistent_worker")
      continue
    if line is None:
      raise RuntimeError("常驻 nnUNetv2 worker 已退出。")
    line = line.strip()
    if not line:
      continue
    try:
      event = json.loads(line)
    except json.JSONDecodeError as exc:
      raise RuntimeError(f"常驻 nnUNetv2 worker 返回了无效 JSON：{line[:200]}") from exc
    if not isinstance(event, dict):
      raise RuntimeError("常驻 nnUNetv2 worker 返回了无效事件。")
    return event


def run_persistent_worker_prediction(job: Job, input_dir: Path, output_dir: Path, model_dir: Path) -> subprocess.CompletedProcess[str]:
  with persistent_worker_lock:
    try:
      options = job.inference_options or get_inference_options()
      process = ensure_persistent_worker(model_dir, options)
      with jobs_lock:
        job.process = process
      preprocess_workers, export_workers = get_predict_worker_counts()
      send_persistent_worker_request(process, {
        "type": "predict",
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "preprocess_workers": preprocess_workers,
        "export_workers": export_workers,
        "tile_step_size": options.get("tile_step_size", 0.5),
        "disable_tta": bool(options.get("disable_tta", False)),
        "not_on_device": bool(options.get("not_on_device", False)),
      })
      event = _read_worker_event_with_heartbeat(job, process)
      if event.get("type") == "complete":
        return subprocess.CompletedProcess(
          args=["persistent-nnunetv2-worker", str(PERSISTENT_WORKER_SCRIPT)],
          returncode=0,
          stdout=str(event.get("message") or "persistent worker prediction complete"),
          stderr="",
        )
      if job.cancel_requested:
        raise JobCancelled(subprocess.CompletedProcess(
          args=["persistent-nnunetv2-worker", str(PERSISTENT_WORKER_SCRIPT)],
          returncode=-1,
          stdout="",
          stderr="推理任务已取消",
        ))
      return subprocess.CompletedProcess(
        args=["persistent-nnunetv2-worker", str(PERSISTENT_WORKER_SCRIPT)],
        returncode=1,
        stdout="",
        stderr=str(event.get("message") or event),
      )
    except RuntimeError as exc:
      if job.cancel_requested:
        raise JobCancelled(subprocess.CompletedProcess(
          args=["persistent-nnunetv2-worker", str(PERSISTENT_WORKER_SCRIPT)],
          returncode=-1,
          stdout="",
          stderr="推理任务已取消",
        )) from exc
      raise
    finally:
      with jobs_lock:
        if job.process is persistent_worker_process:
          job.process = None
      if persistent_worker_process is None or persistent_worker_process.poll() is not None:
        close_persistent_worker_locked()


def get_checkpoint_sha256() -> str | None:
  checkpoint_source = get_checkpoint_source()
  if not checkpoint_source.exists():
    return None
  return stable_file_sha256(checkpoint_source)


def build_prediction_cache_key(input_sha256: str, model_state: dict[str, Any] | None = None) -> str:
  state = model_state or get_model_state()
  runtime_target = state.get("runtime_target")
  payload = {
    "input_sha256": input_sha256,
    "checkpoint_sha256": get_checkpoint_sha256(),
    "checkpoint_dataset_name": state.get("checkpoint_dataset_name"),
    "checkpoint_configuration": state.get("checkpoint_configuration"),
    "labels_source": state.get("labels_source"),
    "runtime_target": normalize_runtime_target(str(runtime_target)) if runtime_target else normalize_runtime_target(),
    "inference_options": state.get("inference_options") or get_inference_options(),
  }
  encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
  return hashlib.sha256(encoded).hexdigest()


def find_cached_prediction(cache_key: str, input_path: Path, current_job_id: str) -> dict[str, Any] | None:
  if WORK_DIR.exists():
    for job_dir in WORK_DIR.iterdir():
      if not job_dir.is_dir() or job_dir.name in {current_job_id, "runtime_model"}:
        continue
      summary = read_persisted_job_summary(job_dir.name)
      if not summary or summary.get("cache_key") != cache_key or not summary.get("result_ready"):
        continue
      result_path = Path(str(summary.get("result_path")))
      if result_path.exists():
        return {
          "job_id": job_dir.name,
          "result_path": result_path,
          "legacy": False,
        }

  legacy_job_id = "009d4efdc5f6"
  legacy_result = WORK_DIR / legacy_job_id / "output" / f"{legacy_job_id}.nii.gz"
  legacy_summary = read_persisted_job_summary(legacy_job_id)
  if (
    is_debug_original_upload(input_path) and
    legacy_result.exists() and
    legacy_summary and
    legacy_summary.get("cache_key") == cache_key
  ):
    return {
      "job_id": legacy_job_id,
      "result_path": legacy_result,
      "legacy": True,
    }
  return None


def copy_cached_result(cache: dict[str, Any], output_dir: Path, job_id: str) -> Path:
  source_path = Path(str(cache["result_path"]))
  suffix = ".nii.gz" if source_path.name.lower().endswith(".nii.gz") else ".nii"
  target_path = output_dir / f"{job_id}{suffix}"
  output_dir.mkdir(parents=True, exist_ok=True)
  try:
    os.link(source_path, target_path)
  except OSError:
    shutil.copy2(source_path, target_path)
  return target_path


def complete_cached_job(job: Job, input_path: Path, cache: dict[str, Any]) -> None:
  start_job_phase(job, "cache_hit")
  output_dir = input_path.parent.parent / "output"
  result_path = copy_cached_result(cache, output_dir, job.id)
  validation = None
  if job.label_path and job.label_path.exists():
    validation = validate_against_custom_label(result_path, job.label_path, read_labels())
  elif is_debug_original_upload(input_path):
    validation = validate_against_debug_label(result_path)
  if validation is not None:
    write_validation_summary(output_dir, validation)
  finish_job_phase(job, "cache_hit")
  with jobs_lock:
    job.mode = "cached-real-nnunetv2"
    job.status = "succeeded"
    job.progress = 100
    job.stage = "命中历史 nnUNetv2 缓存结果"
    job.cached_result = True
    job.cache_source_job_id = str(cache.get("job_id"))
    job.result_path = result_path
    job.validation = validation
    job.started_at = time.time()
    job.completed_at = job.started_at
  record_job_resource_snapshot(job, "cache_hit")
  with jobs_lock:
    write_job_summary(output_dir, job)
  complete_event: dict[str, Any] = {
    "type": "complete",
    "progress": 100,
    "stage": "命中历史 nnUNetv2 缓存结果",
    "duration_seconds": get_job_duration_seconds(job),
    "result_size_bytes": get_result_size_bytes(job),
    "phase_timings": job.phase_timings,
    "cached_result": True,
    "cache_source_job_id": job.cache_source_job_id,
    "runtime_target": job.runtime_target,
    "inference_options": job.inference_options,
  }
  if validation is not None:
    complete_event["validation"] = validation
  if job.resource_snapshots:
    complete_event["resource_latest"] = job.resource_snapshots[-1]
  push_event(job, complete_event)


def push_event(job: Job, event: dict[str, Any]) -> None:
  with jobs_lock:
    job.events.append(event)
    if event.get("type") in {"progress", "complete"}:
      job.progress = int(event.get("progress", job.progress))
      job.stage = str(event.get("stage", job.stage))


def run_debug_job(job_id: str, input_path: Path) -> None:
  with jobs_lock:
    job = jobs[job_id]
    job.status = "running"
    job.started_at = time.time()
  stages = [
    (12, "接收 NIfTI 原图"),
    (28, "检查 nnUNetv2 模型配置"),
    (48, "载入本地权重与标签映射"),
    (68, "执行调试推理任务"),
    (88, "写出多标签分割结果"),
  ]
  try:
    for progress, stage in stages:
      push_event(job, {"type": "progress", "progress": progress, "stage": stage})
      time.sleep(0.35)
    source_label = DEBUG_LABEL if DEBUG_LABEL.exists() else FALLBACK_LABEL
    if not source_label.exists():
      raise RuntimeError("未找到本地调试标签 NIfTI，无法生成分割结果。")
    result_path = input_path.parent / f"{job_id}_seg.nii.gz"
    shutil.copyfile(source_label, result_path)
    with jobs_lock:
      job.result_path = result_path
      job.status = "succeeded"
      job.completed_at = time.time()
    push_event(job, {"type": "complete", "progress": 100, "stage": "分割结果已生成"})
  except Exception as exc:
    with jobs_lock:
      job.status = "failed"
      job.error = str(exc)
      job.completed_at = time.time()
    push_event(job, {"type": "error", "message": str(exc)})


def get_process_tail(process: subprocess.CompletedProcess[str]) -> str:
  text = "\n".join(part for part in [process.stdout, process.stderr] if part)
  lines = [line for line in text.splitlines() if line.strip()]
  return "\n".join(lines[-8:]) if lines else "nnUNetv2 未输出错误详情"


def get_server_process_env(config: Any) -> dict[str, str]:
  env = os.environ.copy()
  env["nnUNet_raw"] = str(config.nnunet_raw)
  env["nnUNet_preprocessed"] = str(config.nnunet_preprocessed)
  env["nnUNet_results"] = str(config.nnunet_results)
  return env


def copy_server_result_to_job_output(result_path: Path, output_dir: Path, job_id: str) -> Path:
  suffix = ".nii.gz" if result_path.name.lower().endswith(".nii.gz") else ".nii"
  target_path = output_dir / f"{job_id}{suffix}"
  output_dir.mkdir(parents=True, exist_ok=True)
  shutil.copy2(result_path, target_path)
  return target_path


def run_server_job_pipeline(job: Job, input_dir: Path, output_dir: Path, case_name: str) -> tuple[Path, dict[str, Any] | None, list[tuple[str, subprocess.CompletedProcess[str]]]]:
  config = get_server_inference_config()
  server_job_dir = config.output_root / job.id
  server_job_dir.mkdir(parents=True, exist_ok=True)
  output_prefix = server_job_dir / job.id
  ensemble_output_dir = server_job_dir / "ensemble"
  sections: list[tuple[str, subprocess.CompletedProcess[str]]] = []

  push_event(job, {"type": "progress", "progress": 8, "stage": "任务已提交到服务器 5-GPU 推理队列"})
  start_job_phase(job, "server_fold_predict")
  fold_commands = build_server_fold_commands(config, input_dir, output_prefix)
  push_event(job, {"type": "progress", "progress": 20, "stage": "5-fold 并行推理中"})
  fold_results = run_parallel_processes_with_cancel(
    job,
    [(f"fold_{item.fold}_gpu_{item.gpu}", item.command, item.env) for item in fold_commands],
    heartbeat_phase="server_fold_predict",
  )
  finish_job_phase(job, "server_fold_predict")
  for fold_command, result in zip(fold_commands, fold_results):
    sections.append((f"fold_{fold_command.fold}_gpu_{fold_command.gpu}", result))
    if result.returncode != 0:
      raise RuntimeError(f"服务器 fold {fold_command.fold} 推理失败（退出码 {result.returncode}）：{get_process_tail(result)}")

  push_event(job, {"type": "progress", "progress": 76, "stage": "softmax 概率图集成中"})
  start_job_phase(job, "server_ensemble")
  ensemble_command = build_server_ensemble_command(config, [item.output_dir for item in fold_commands], ensemble_output_dir)
  ensemble_result = run_command_with_cancel(
    job,
    ensemble_command,
    env=get_server_process_env(config),
    heartbeat_phase="server_ensemble",
  )
  finish_job_phase(job, "server_ensemble")
  sections.append(("soft_ensemble", ensemble_result))
  if ensemble_result.returncode != 0:
    raise RuntimeError(f"服务器 soft ensemble 失败（退出码 {ensemble_result.returncode}）：{get_process_tail(ensemble_result)}")

  push_event(job, {"type": "progress", "progress": 90, "stage": "整理服务器 nnUNetv2 输出"})
  start_job_phase(job, "collect_result")
  candidates = sorted(ensemble_output_dir.glob(f"{case_name}*.nii*"))
  if not candidates:
    candidates = sorted(ensemble_output_dir.glob("*.nii*"))
  if not candidates:
    raise RuntimeError("服务器 soft ensemble 已结束，但未找到输出 NIfTI 结果。")
  result_path = copy_server_result_to_job_output(candidates[0], output_dir, job.id)
  finish_job_phase(job, "collect_result")

  validation = None
  if job.label_path and job.label_path.exists():
    push_event(job, {"type": "progress", "progress": 96, "stage": "使用用户提供的标签验证服务器结果"})
    start_job_phase(job, "validation")
    validation = validate_against_custom_label(result_path, job.label_path, read_labels())
    write_validation_summary(output_dir, validation)
    evaluate_command = build_server_evaluate_command(config, ensemble_output_dir, job.label_path)
    if evaluate_command:
      evaluate_result = run_command_with_cancel(job, evaluate_command, env=get_server_process_env(config), heartbeat_phase="server_validation")
      sections.append(("server_evaluate", evaluate_result))
      if evaluate_result.returncode != 0:
        validation = {**validation, "status": "review", "message": f"{validation.get('message') or ''} 服务器 evaluate_full.py 退出码 {evaluate_result.returncode}。".strip()}
        write_validation_summary(output_dir, validation)
    finish_job_phase(job, "validation")
  elif is_debug_original_upload(input_dir / f"{case_name}_0000.nii.gz") or is_debug_original_upload(input_dir / f"{case_name}_0000.nii"):
    push_event(job, {"type": "progress", "progress": 96, "stage": "使用 AMOS 标准答案验证服务器结果"})
    start_job_phase(job, "validation")
    validation = validate_against_debug_label(result_path)
    write_validation_summary(output_dir, validation)
    finish_job_phase(job, "validation")

  return result_path, validation, sections


def run_local_job_pipeline(job: Job, input_path: Path, input_dir: Path, output_dir: Path, case_name: str) -> tuple[Path, dict[str, Any] | None, list[tuple[str, subprocess.CompletedProcess[str]]]]:
  push_event(job, {"type": "progress", "progress": 8, "stage": "任务已提交到本地 nnUNetv2"})
  start_job_phase(job, "prepare_runtime_model")
  model_dir = prepare_runtime_model_dir()
  finish_job_phase(job, "prepare_runtime_model")
  push_event(job, {"type": "progress", "progress": 14, "stage": "已准备项目指定训练权重"})
  if persistent_worker_enabled():
    push_event(job, {"type": "progress", "progress": 20, "stage": "常驻 nnUNetv2 worker 推理中"})
    start_job_phase(job, "persistent_worker")
    process = run_persistent_worker_prediction(job, input_dir, output_dir, model_dir)
    finish_job_phase(job, "persistent_worker")
  else:
    start_job_phase(job, "build_predict_command")
    command = build_predict_command(input_dir, output_dir, model_dir=model_dir, inference_options=job.inference_options)
    finish_job_phase(job, "build_predict_command")
    push_event(job, {"type": "progress", "progress": 20, "stage": "nnUNetv2 命令运行中"})
    start_job_phase(job, "nnunet_process")
    process = run_process_with_cancel(job, command)
    finish_job_phase(job, "nnunet_process")
  if process.returncode != 0:
    raise RuntimeError(f"nnUNetv2 推理失败（退出码 {process.returncode}）：{get_process_tail(process)}")

  push_event(job, {"type": "progress", "progress": 90, "stage": "整理 nnUNetv2 输出"})
  start_job_phase(job, "collect_result")
  candidates = sorted(output_dir.glob(f"{case_name}*.nii*"))
  if not candidates:
    raise RuntimeError("nnUNetv2 命令已结束，但未找到输出 NIfTI 结果。")
  result_path = candidates[0]
  finish_job_phase(job, "collect_result")

  validation = None
  if job.label_path and job.label_path.exists():
    push_event(job, {"type": "progress", "progress": 96, "stage": "使用用户提供的标签验证推理结果"})
    start_job_phase(job, "validation")
    validation = validate_against_custom_label(result_path, job.label_path, read_labels())
    write_validation_summary(output_dir, validation)
    finish_job_phase(job, "validation")
  elif is_debug_original_upload(input_path):
    push_event(job, {"type": "progress", "progress": 96, "stage": "使用 AMOS 标准答案验证推理结果"})
    start_job_phase(job, "validation")
    validation = validate_against_debug_label(result_path)
    write_validation_summary(output_dir, validation)
    finish_job_phase(job, "validation")

  return result_path, validation, [("local_nnunetv2", process)]


def run_real_job(job_id: str, input_path: Path) -> None:
  with jobs_lock:
    job = jobs[job_id]
    job.status = "running"
    job.started_at = time.time()
  record_job_resource_snapshot(job, "started")
  input_dir = input_path.parent
  output_dir = input_path.parent.parent / "output"
  output_dir.mkdir(parents=True, exist_ok=True)
  case_name = input_path.name.replace("_0000.nii.gz", "").replace("_0000.nii", "")

  try:
    if job.runtime_target == "server":
      result_path, validation, sections = run_server_job_pipeline(job, input_dir, output_dir, case_name)
      complete_stage = "服务器 5-fold soft ensemble 推理结果已生成"
    else:
      result_path, validation, sections = run_local_job_pipeline(job, input_path, input_dir, output_dir, case_name)
      complete_stage = "真实 nnUNetv2 推理结果已生成"
    process_log_path, log_tail = write_multi_process_log(output_dir, sections)
    with jobs_lock:
      job.process_log_path = process_log_path
      job.log_tail = log_tail

    record_job_resource_snapshot(job, "completed")
    with jobs_lock:
      job.result_path = result_path
      job.validation = validation
      job.status = "succeeded"
      job.completed_at = time.time()
      write_job_summary(output_dir, job)
    complete_event: dict[str, Any] = {
      "type": "complete",
      "progress": 100,
      "stage": complete_stage,
      "duration_seconds": get_job_duration_seconds(job),
      "result_size_bytes": get_result_size_bytes(job),
      "phase_timings": job.phase_timings,
      "inference_options": job.inference_options,
      "runtime_target": job.runtime_target,
    }
    if validation is not None:
      complete_event["validation"] = validation
    if job.resource_snapshots:
      complete_event["resource_latest"] = job.resource_snapshots[-1]
    push_event(job, complete_event)
  except JobCancelled as exc:
    process_log_path, log_tail = write_process_log(output_dir, exc.process)
    record_job_resource_snapshot(job, "cancelled")
    with jobs_lock:
      job.process_log_path = process_log_path
      job.log_tail = log_tail
      job.status = "cancelled"
      job.error = "推理任务已取消"
      job.completed_at = time.time()
      write_job_summary(output_dir, job)
    cancel_event: dict[str, Any] = {"type": "error", "message": "推理任务已取消", "log_tail": log_tail}
    if job.resource_snapshots:
      cancel_event["resource_latest"] = job.resource_snapshots[-1]
    push_event(job, cancel_event)
  except Exception as exc:
    record_job_resource_snapshot(job, "failed")
    with jobs_lock:
      job.status = "failed"
      job.error = str(exc)
      job.completed_at = time.time()
      write_job_summary(output_dir, job)
    error_event: dict[str, Any] = {"type": "error", "message": str(exc)}
    if job.log_tail:
      error_event["log_tail"] = job.log_tail
    if job.resource_snapshots:
      error_event["resource_latest"] = job.resource_snapshots[-1]
    push_event(job, error_event)


@app.get("/api/health")
def health() -> dict[str, Any]:
  model_state = get_model_state()
  return {
    "status": "ok",
    "mode": model_state["mode"],
    "nnunet_results": str(NNUNET_RESULTS),
    "model_config_detected": model_state["ready"],
    "model_status": model_state,
    "has_checkpoint": FLARE_CHECKPOINT.exists() or (NNUNET_FILES / "checkpoint_best.pth").exists(),
    "has_debug_original": DEBUG_ORIGINAL.exists(),
    "has_debug_label": DEBUG_LABEL.exists() or FALLBACK_LABEL.exists(),
  }


@app.get("/api/models")
def models() -> dict[str, Any]:
  model_state = get_model_state()
  return {
    "models": [
      {
        "id": "abdomen",
        "name": "本地 nnUNetv2 FLARE/AMOS 模型",
        "status": model_state["status"],
        "mode": model_state["mode"],
        "model_config_detected": model_state["ready"],
        "missing": model_state["missing"],
        "checkpoint": model_state["checkpoint"],
        "confidence_threshold_effective": model_state["confidence_threshold_effective"],
        "runtime_target": model_state["runtime_target"],
        "server_inference": model_state["server_inference"],
        "labels": read_labels(),
      }
    ]
  }


@app.get("/api/samples")
def samples() -> dict[str, Any]:
  return {
    "samples": [public_reference_case(record) for record in reference_case_records()]
  }


@app.get("/api/samples/{sample_id}/original")
def sample_original(sample_id: str) -> FileResponse:
  record = find_reference_case(sample_id)
  original_path = record.get("_original_path") if record else None
  if not isinstance(original_path, Path) or not original_path.exists():
    raise HTTPException(status_code=404, detail="参考病例原图不存在")
  return FileResponse(original_path, media_type="application/octet-stream", filename=record["original_filename"])


@app.get("/api/samples/{sample_id}/label")
def sample_label(sample_id: str) -> FileResponse:
  record = find_reference_case(sample_id)
  label_path = record.get("_label_path") if record else None
  if not isinstance(label_path, Path) or not label_path.exists():
    raise HTTPException(status_code=404, detail="参考病例标签不存在")
  return FileResponse(label_path, media_type="application/octet-stream", filename=record["label_filename"])


@app.post("/api/segment/jobs")
async def create_job(
  file: UploadFile = File(...),
  label_file: UploadFile | None = File(None),
  model_id: str = Form("abdomen"),
  confidence_threshold: str = Form("72"),
  postprocess: str = Form("{}"),
  inference_profile: str | None = Form(None),
  runtime_target: str | None = Form(None),
) -> dict[str, Any]:
  if not file.filename or not file.filename.lower().endswith((".nii", ".nii.gz")):
    raise HTTPException(status_code=400, detail="请上传 .nii 或 .nii.gz 格式的 CT 原图。")
  runtime = normalize_runtime_target(runtime_target)
  model_state = get_model_state(runtime)
  if not model_state["ready"]:
    raise HTTPException(status_code=503, detail={
      "message": "本地 nnUNetv2 模型配置不完整，无法创建真实推理任务。",
      "missing": model_state["missing"],
      "model_status": model_state,
    })
  inference_options = get_inference_options(inference_profile)
  model_state = {**model_state, "inference_options": inference_options}
  job_id = uuid.uuid4().hex[:12]
  job_dir = WORK_DIR / job_id
  input_dir = job_dir / "input"
  input_dir.mkdir(parents=True, exist_ok=True)
  input_file_ending = str(model_state.get("model_file_ending") or ".nii.gz")
  input_path = input_dir / f"{job_id}_0000{input_file_ending}"
  copy_upload_to_nnunet_input(file, input_path, input_file_ending)
  custom_label_path = None
  if label_file is not None and label_file.filename:
    label_dir = job_dir / "label"
    label_dir.mkdir(parents=True, exist_ok=True)
    label_target = label_dir / f"{job_id}_label.nii.gz"
    copy_upload_to_nnunet_input(label_file, label_target, ".nii.gz")
    custom_label_path = label_target
  input_sha = file_sha256(input_path)
  cache_key = build_prediction_cache_key(input_sha, model_state)
  job = Job(
    id=job_id,
    mode=model_state["mode"],
    input_sha256=input_sha,
    checkpoint_sha256=get_checkpoint_sha256(),
    cache_key=cache_key,
    inference_options=inference_options,
    label_path=custom_label_path,
    runtime_target=runtime,
  )
  with jobs_lock:
    jobs[job_id] = job
  cache = find_cached_prediction(cache_key, input_path, job_id)
  if cache is not None:
    complete_cached_job(job, input_path, cache)
    return {
      "job_id": job_id,
      "model_id": model_id,
      "confidence_threshold": confidence_threshold,
      "confidence_threshold_effective": False,
      "postprocess": postprocess,
      "mode": job.mode,
      "runtime_target": job.runtime_target,
      "model_status": model_state,
      "cached_result": True,
      "cache_source_job_id": job.cache_source_job_id,
      "inference_profile": job.inference_options.get("profile"),
      "inference_options": job.inference_options,
    }
  thread = threading.Thread(target=run_real_job, args=(job_id, input_path), daemon=True)
  thread.start()
  return {
    "job_id": job_id,
    "model_id": model_id,
    "confidence_threshold": confidence_threshold,
    "confidence_threshold_effective": False,
    "postprocess": postprocess,
    "mode": job.mode,
    "runtime_target": job.runtime_target,
    "model_status": model_state,
    "cached_result": False,
    "inference_profile": job.inference_options.get("profile"),
    "inference_options": job.inference_options,
  }


@app.get("/api/segment/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
  job = jobs.get(job_id)
  if not job:
    persisted = read_persisted_job_summary(job_id)
    if persisted is None:
      raise HTTPException(status_code=404, detail="任务不存在")
    return persisted
  return build_job_summary(job)


@app.post("/api/segment/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict[str, Any]:
  job = request_job_cancel(job_id)
  if job is None:
    raise HTTPException(status_code=404, detail="任务不存在")
  return build_job_summary(job)


@app.get("/api/segment/jobs/{job_id}/events")
def job_events(job_id: str) -> StreamingResponse:
  job = jobs.get(job_id)
  if not job:
    raise HTTPException(status_code=404, detail="任务不存在")

  def stream():
    cursor = 0
    while True:
      with jobs_lock:
        events = job.events[cursor:]
        cursor = len(job.events)
        done = job.status in {"succeeded", "failed", "cancelled"}
      for event in events:
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
      if done and cursor >= len(job.events):
        break
      time.sleep(0.2)

  return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/segment/jobs/{job_id}/result")
def job_result(job_id: str) -> FileResponse:
  job = jobs.get(job_id)
  if not job:
    persisted_result_path = get_persisted_result_path(job_id)
    if persisted_result_path is None:
      raise HTTPException(status_code=404, detail="任务不存在")
    return FileResponse(persisted_result_path, media_type="application/octet-stream", filename=f"{job_id}_seg.nii.gz")
  if job.status != "succeeded" or not job.result_path or not job.result_path.exists():
    raise HTTPException(status_code=409, detail="推理任务尚未完成")
  return FileResponse(job.result_path, media_type="application/octet-stream", filename=f"{job_id}_seg.nii.gz")
