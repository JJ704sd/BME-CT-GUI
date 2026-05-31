from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

protocol_stdout = sys.stdout
sys.stdout = sys.stderr

predictor = None
initialized_model_dir: str | None = None
initialized_device: str | None = None


def as_bool(value: Any, default: bool = False) -> bool:
  if isinstance(value, bool):
    return value
  if value is None:
    return default
  normalized = str(value).strip().lower()
  if normalized in {"1", "true", "yes", "on"}:
    return True
  if normalized in {"0", "false", "no", "off"}:
    return False
  return default


def send(payload: dict[str, Any]) -> None:
  protocol_stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
  protocol_stdout.flush()


def handle_init(payload: dict[str, Any]) -> None:
  global predictor, initialized_model_dir, initialized_device
  import torch
  from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

  model_dir = str(payload["model_dir"])
  checkpoint_name = str(payload.get("checkpoint") or "checkpoint_best.pth")
  device = str(payload.get("device") or "cuda")
  tile_step_size = float(payload.get("tile_step_size") or 0.5)
  disable_tta = as_bool(payload.get("disable_tta"), False)
  not_on_device = as_bool(payload.get("not_on_device"), False)
  initialized_model_dir = model_dir
  initialized_device = device
  predictor = nnUNetPredictor(
    tile_step_size=tile_step_size,
    use_gaussian=True,
    use_mirroring=not disable_tta,
    perform_everything_on_device=not not_on_device,
    device=torch.device(device),
    verbose=False,
    verbose_preprocessing=False,
    allow_tqdm=False,
  )
  predictor.initialize_from_trained_model_folder(
    model_dir,
    use_folds=(0,),
    checkpoint_name=checkpoint_name,
  )
  send({
    "type": "ready",
    "message": "常驻 nnUNetv2 worker 已初始化",
    "model_dir": model_dir,
    "device": device,
    "checkpoint": checkpoint_name,
    "tile_step_size": tile_step_size,
    "disable_tta": disable_tta,
    "not_on_device": not_on_device,
  })


def handle_predict(payload: dict[str, Any]) -> None:
  if predictor is None:
    raise RuntimeError("worker not initialized")
  input_dir = str(payload["input_dir"])
  output_dir = str(payload["output_dir"])
  preprocess_workers = int(payload.get("preprocess_workers") or 2)
  export_workers = int(payload.get("export_workers") or 2)
  predictor.predict_from_files(
    input_dir,
    output_dir,
    save_probabilities=False,
    overwrite=True,
    num_processes_preprocessing=preprocess_workers,
    num_processes_segmentation_export=export_workers,
  )
  send({
    "type": "complete",
    "message": "常驻 nnUNetv2 worker 推理完成",
    "input_dir": input_dir,
    "output_dir": output_dir,
    "model_dir": initialized_model_dir,
    "device": initialized_device,
  })


def main() -> None:
  for raw_line in sys.stdin:
    line = raw_line.strip()
    if not line:
      continue
    try:
      payload = json.loads(line)
    except json.JSONDecodeError as exc:
      send({"type": "error", "message": f"无效 JSON：{exc}"})
      continue
    request_type = payload.get("type")
    try:
      if request_type == "init":
        handle_init(payload)
      elif request_type == "predict":
        handle_predict(payload)
      elif request_type == "shutdown":
        send({"type": "bye", "message": "常驻 nnUNetv2 worker 已退出"})
        break
      else:
        send({"type": "error", "message": f"未知请求类型：{request_type}"})
    except Exception as exc:
      traceback.print_exc(file=sys.stderr)
      send({"type": "error", "message": str(exc)})


if __name__ == "__main__":
  main()
