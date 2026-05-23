from __future__ import annotations

import json
import os
import hashlib
import shutil
import subprocess
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

FLARE_MODEL_DIR = NNUNET_RESULTS / "Dataset001_FLARE" / "nnUNetTrainer__nnUNetPlans__2d"
FLARE_DATASET_JSON = FLARE_MODEL_DIR / "dataset.json"
FLARE_PLANS_JSON = FLARE_MODEL_DIR / "plans.json"
FLARE_CHECKPOINT = FLARE_MODEL_DIR / "fold_0" / "checkpoint_best.pth"
RUNTIME_MODEL_DIR = WORK_DIR / "runtime_model" / "nnUNetTrainer__nnUNetPlans__2d"
RUNTIME_CHECKPOINT = RUNTIME_MODEL_DIR / "fold_0" / "checkpoint_best.pth"
NNUNET_PREDICT_COMMAND = PROJECT_ROOT / "nnunet_env" / "Scripts" / "nnUNetv2_predict_from_modelfolder.exe"
NNUNET_PYTHON_COMMAND = PROJECT_ROOT / "nnunet_env" / "Scripts" / "python.exe"
NNUNET_PREDICT_ENTRYPOINT = (
  "import sys; "
  "from nnunetv2.inference.predict_from_raw_data import predict_entry_point_modelfolder; "
  "sys.argv=['nnUNetv2_predict_from_modelfolder'] + sys.argv[1:]; "
  "predict_entry_point_modelfolder()"
)
VALIDATION_MEAN_DICE_THRESHOLD = 0.85
VALIDATION_MIN_DICE_THRESHOLD = 0.70


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
  log_tail: str | None = None
  process_log_path: Path | None = None
  events: list[dict[str, Any]] = field(default_factory=list)


jobs: dict[str, Job] = {}
jobs_lock = threading.Lock()

app = FastAPI(title="Segmentation GUI nnUNetv2 Bridge")
app.add_middleware(
  CORSMiddleware,
  allow_origin_regex=r"http://(127\.0\.0\.1|localhost):\d+",
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


def get_job_duration_seconds(job: Job) -> float | None:
  if job.started_at is None:
    return None
  end_time = job.completed_at if job.completed_at is not None else time.time()
  return round(max(0.0, end_time - job.started_at), 3)


def get_result_size_bytes(job: Job) -> int | None:
  if job.result_path is None or not job.result_path.exists():
    return None
  return job.result_path.stat().st_size


def build_job_summary(job: Job) -> dict[str, Any]:
  return {
    "job_id": job.id,
    "status": job.status,
    "progress": job.progress,
    "stage": job.stage,
    "mode": job.mode,
    "error": job.error,
    "started_at": job.started_at,
    "completed_at": job.completed_at,
    "duration_seconds": get_job_duration_seconds(job),
    "result_ready": job.status == "succeeded" and job.result_path is not None and job.result_path.exists(),
    "result_path": str(job.result_path) if job.result_path else None,
    "result_size_bytes": get_result_size_bytes(job),
    "log_tail": job.log_tail,
    "process_log_path": str(job.process_log_path) if job.process_log_path else None,
    "validation": job.validation,
  }


def write_job_summary(output_dir: Path, job: Job) -> Path:
  output_dir.mkdir(parents=True, exist_ok=True)
  summary_path = output_dir / "job_summary.json"
  summary_path.write_text(
    json.dumps(build_job_summary(job), ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
  )
  return summary_path


def write_process_log(output_dir: Path, process: subprocess.CompletedProcess[str]) -> tuple[Path, str]:
  output_dir.mkdir(parents=True, exist_ok=True)
  log_path = output_dir / "nnunetv2_process.log"
  log_text = "\n".join([
    f"COMMAND: {' '.join(str(part) for part in process.args)}",
    f"RETURN_CODE: {process.returncode}",
    "",
    "STDOUT:",
    process.stdout or "",
    "",
    "STDERR:",
    process.stderr or "",
  ])
  log_path.write_text(log_text, encoding="utf-8")
  return log_path, get_process_tail(process)


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
      "result_ready": True,
      "result_path": str(result_path),
      "result_size_bytes": result_path.stat().st_size,
      "log_tail": log_tail,
      "process_log_path": str(process_log_path) if process_log_path.exists() else None,
      "validation": validation,
    }
  summary = json.loads(summary_path.read_text(encoding="utf-8"))
  if not isinstance(summary, dict):
    return None

  result_path = Path(str(summary.get("result_path"))) if summary.get("result_path") else None
  result_ready = bool(summary.get("status") == "succeeded" and result_path and result_path.exists())
  summary["result_ready"] = result_ready
  summary["result_size_bytes"] = result_path.stat().st_size if result_ready and result_path else None

  if summary.get("validation") is None:
    validation_path = output_dir / "validation_summary.json"
    if validation_path.exists():
      summary["validation"] = json.loads(validation_path.read_text(encoding="utf-8"))

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
  if left.stat().st_size != right.stat().st_size:
    return False
  return file_sha256(left) == file_sha256(right)


def get_checkpoint_source() -> Path:
  return PROJECT_CHECKPOINT if PROJECT_CHECKPOINT.exists() else FLARE_CHECKPOINT


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


def model_ready() -> bool:
  return bool(get_model_state()["ready"])


def get_model_state() -> dict[str, Any]:
  checkpoint_source = get_checkpoint_source()
  checkpoint_args = load_checkpoint_init_args()
  checkpoint_plans = checkpoint_args.get("plans") if checkpoint_args else None
  required_files = [
    ("dataset.json", FLARE_DATASET_JSON),
    ("plans.json", FLARE_PLANS_JSON),
    ("checkpoint_best.pth", checkpoint_source),
    ("nnUNetv2_python", NNUNET_PYTHON_COMMAND),
  ]
  missing = [name for name, path in required_files if not path.exists()]
  ready = not missing
  return {
    "ready": ready,
    "status": "ready" if ready else "incomplete",
    "mode": "real-nnunetv2" if ready else "unavailable",
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
    "labels_source": "checkpoint" if checkpoint_args and checkpoint_args.get("dataset_json") else "dataset.json" if FLARE_DATASET_JSON.exists() else "fallback",
    "confidence_threshold_effective": False,
  }


def get_predict_device() -> str:
  device = os.environ.get("SEGMENTATION_DEVICE", "cpu").strip().lower()
  return device if device in {"cpu", "cuda", "mps"} else "cpu"


def get_predict_environment() -> dict[str, str]:
  env = os.environ.copy()
  env["nnUNet_raw"] = str(NNUNET_RAW)
  env["nnUNet_preprocessed"] = str(NNUNET_PREPROCESSED)
  env["nnUNet_results"] = str(NNUNET_RESULTS)
  return env


def build_predict_command(input_dir: Path, output_dir: Path, device: str | None = None, model_dir: Path | None = None) -> list[str]:
  model_root = model_dir or FLARE_MODEL_DIR
  return [
    str(NNUNET_PYTHON_COMMAND),
    "-c",
    NNUNET_PREDICT_ENTRYPOINT,
    "-i", str(input_dir),
    "-o", str(output_dir),
    "-m", str(model_root),
    "-f", "0",
    "-chk", "checkpoint_best.pth",
    "-npp", "1",
    "-nps", "1",
    "-device", device or get_predict_device(),
    "--disable_progress_bar",
  ]


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


def run_real_job(job_id: str, input_path: Path) -> None:
  with jobs_lock:
    job = jobs[job_id]
    job.status = "running"
    job.started_at = time.time()
  input_dir = input_path.parent
  output_dir = input_path.parent.parent / "output"
  output_dir.mkdir(parents=True, exist_ok=True)
  case_name = input_path.name.replace("_0000.nii.gz", "").replace("_0000.nii", "")

  try:
    push_event(job, {"type": "progress", "progress": 8, "stage": "任务已提交到本地 nnUNetv2"})
    model_dir = prepare_runtime_model_dir()
    push_event(job, {"type": "progress", "progress": 14, "stage": "已准备项目指定训练权重"})
    command = build_predict_command(input_dir, output_dir, model_dir=model_dir)
    push_event(job, {"type": "progress", "progress": 20, "stage": "nnUNetv2 命令运行中"})
    process = subprocess.run(
      command,
      cwd=str(PROJECT_ROOT),
      env=get_predict_environment(),
      capture_output=True,
      text=True,
      encoding="utf-8",
      errors="replace",
    )
    process_log_path, log_tail = write_process_log(output_dir, process)
    with jobs_lock:
      job.process_log_path = process_log_path
      job.log_tail = log_tail
    if process.returncode != 0:
      raise RuntimeError(f"nnUNetv2 推理失败（退出码 {process.returncode}）：{get_process_tail(process)}")

    push_event(job, {"type": "progress", "progress": 90, "stage": "整理 nnUNetv2 输出"})
    candidates = sorted(output_dir.glob(f"{case_name}*.nii*"))
    if not candidates:
      raise RuntimeError("nnUNetv2 命令已结束，但未找到输出 NIfTI 结果。")
    result_path = candidates[0]
    validation = None
    if is_debug_original_upload(input_path):
      push_event(job, {"type": "progress", "progress": 96, "stage": "使用 AMOS 标准答案验证推理结果"})
      validation = validate_against_debug_label(result_path)
      write_validation_summary(output_dir, validation)

    with jobs_lock:
      job.result_path = result_path
      job.validation = validation
      job.status = "succeeded"
      job.completed_at = time.time()
      write_job_summary(output_dir, job)
    complete_event: dict[str, Any] = {
      "type": "complete",
      "progress": 100,
      "stage": "真实 nnUNetv2 推理结果已生成",
      "duration_seconds": get_job_duration_seconds(job),
      "result_size_bytes": get_result_size_bytes(job),
    }
    if validation is not None:
      complete_event["validation"] = validation
    push_event(job, complete_event)
  except Exception as exc:
    with jobs_lock:
      job.status = "failed"
      job.error = str(exc)
      job.completed_at = time.time()
      write_job_summary(output_dir, job)
    error_event: dict[str, Any] = {"type": "error", "message": str(exc)}
    if job.log_tail:
      error_event["log_tail"] = job.log_tail
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
        "labels": read_labels(),
      }
    ]
  }


@app.get("/api/samples")
def samples() -> dict[str, Any]:
  return {
    "samples": [
      {
        "id": "amos_0117",
        "original": str(DEBUG_ORIGINAL),
        "label": str(DEBUG_LABEL if DEBUG_LABEL.exists() else FALLBACK_LABEL),
        "validation_reference": str(DEBUG_LABEL if DEBUG_LABEL.exists() else FALLBACK_LABEL),
        "validation_available": DEBUG_ORIGINAL.exists() and (DEBUG_LABEL.exists() or FALLBACK_LABEL.exists()),
      }
    ]
  }


@app.get("/api/samples/{sample_id}/original")
def sample_original(sample_id: str) -> FileResponse:
  if sample_id != "amos_0117" or not DEBUG_ORIGINAL.exists():
    raise HTTPException(status_code=404, detail="样例原图不存在")
  return FileResponse(DEBUG_ORIGINAL, media_type="application/octet-stream", filename="amos_0117_original.nii.gz")


@app.get("/api/samples/{sample_id}/label")
def sample_label(sample_id: str) -> FileResponse:
  source_label = DEBUG_LABEL if DEBUG_LABEL.exists() else FALLBACK_LABEL
  if sample_id != "amos_0117" or not source_label.exists():
    raise HTTPException(status_code=404, detail="样例标签不存在")
  return FileResponse(source_label, media_type="application/octet-stream", filename="amos_0117_label.nii.gz")


@app.post("/api/segment/jobs")
async def create_job(
  file: UploadFile = File(...),
  model_id: str = Form("abdomen"),
  confidence_threshold: str = Form("72"),
  postprocess: str = Form("{}"),
) -> dict[str, Any]:
  if not file.filename or not file.filename.lower().endswith((".nii", ".nii.gz")):
    raise HTTPException(status_code=400, detail="请上传 .nii 或 .nii.gz 格式的 CT 原图。")
  model_state = get_model_state()
  if not model_state["ready"]:
    raise HTTPException(status_code=503, detail={
      "message": "本地 nnUNetv2 模型配置不完整，无法创建真实推理任务。",
      "missing": model_state["missing"],
      "model_status": model_state,
    })
  job_id = uuid.uuid4().hex[:12]
  job_dir = WORK_DIR / job_id
  input_dir = job_dir / "input"
  input_dir.mkdir(parents=True, exist_ok=True)
  suffix = ".nii.gz" if file.filename.lower().endswith(".nii.gz") else ".nii"
  input_path = input_dir / f"{job_id}_0000{suffix}"
  with input_path.open("wb") as target:
    shutil.copyfileobj(file.file, target)
  job = Job(id=job_id, mode=model_state["mode"])
  with jobs_lock:
    jobs[job_id] = job
  thread = threading.Thread(target=run_real_job, args=(job_id, input_path), daemon=True)
  thread.start()
  return {
    "job_id": job_id,
    "model_id": model_id,
    "confidence_threshold": confidence_threshold,
    "confidence_threshold_effective": False,
    "postprocess": postprocess,
    "mode": job.mode,
    "model_status": model_state,
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
        done = job.status in {"succeeded", "failed"}
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
