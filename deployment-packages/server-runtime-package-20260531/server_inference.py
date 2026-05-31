from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class ServerFoldCommand:
  fold: str
  gpu: str
  output_dir: Path
  command: list[str]
  env: dict[str, str]


@dataclass(frozen=True)
class ServerInferenceConfig:
  nnunet_raw: Path
  nnunet_preprocessed: Path
  nnunet_results: Path
  output_root: Path
  dataset_id: str
  configuration: str
  plans: str
  folds: tuple[str, ...]
  gpus: tuple[str, ...]
  preprocess_workers: int
  ensemble_processes: int
  predict_command: str
  ensemble_command: str
  python_command: str
  evaluate_script: Path | None
  labels_dir: Path | None
  dataset_json: Path | None


def _csv(value: str | None, fallback: tuple[str, ...]) -> tuple[str, ...]:
  if not value:
    return fallback
  parsed = tuple(item.strip() for item in value.split(",") if item.strip())
  return parsed or fallback


def _int_env(env: Mapping[str, str], name: str, default: int, minimum: int = 1, maximum: int = 64) -> int:
  try:
    value = int(env.get(name, str(default)).strip())
  except (TypeError, ValueError):
    value = default
  return max(minimum, min(maximum, value))


def _path_env(env: Mapping[str, str], name: str, default: str) -> Path:
  return Path(env.get(name, default)).expanduser()


def get_server_inference_config(env: Mapping[str, str] | None = None) -> ServerInferenceConfig:
  source = env or os.environ
  nnunet_raw = _path_env(source, "SEGMENTATION_SERVER_NNUNET_RAW", "/mnt/data0/LUO_Zheng/nnUNet_raw")
  nnunet_results = _path_env(source, "SEGMENTATION_SERVER_NNUNET_RESULTS", "/mnt/data0/LUO_Zheng/nnUNet_results")
  dataset_id = source.get("SEGMENTATION_SERVER_DATASET_ID", "1").strip() or "1"
  configuration = source.get("SEGMENTATION_SERVER_CONFIG", "3d_fullres").strip() or "3d_fullres"
  plans = source.get("SEGMENTATION_SERVER_PLANS", "nnUNetResEncUNetXLPlans").strip() or "nnUNetResEncUNetXLPlans"
  folds = _csv(source.get("SEGMENTATION_SERVER_FOLDS"), ("0", "1", "2", "3", "4"))
  gpus = _csv(source.get("SEGMENTATION_SERVER_GPUS"), ("0", "1", "2", "3", "4"))
  if len(gpus) < len(folds):
    gpus = gpus + tuple(gpus[-1] for _ in range(len(folds) - len(gpus)))
  dataset_json_default = nnunet_results / "Dataset001_AMOS22" / f"nnUNetTrainer__{plans}__{configuration}" / "dataset.json"
  evaluate_script = source.get("SEGMENTATION_SERVER_EVALUATE_SCRIPT", "/mnt/data0/LUO_Zheng/evaluate_full.py").strip()
  labels_dir = source.get("SEGMENTATION_SERVER_LABELS_DIR", "/mnt/data0/LUO_Zheng/amos22/amos22/labelsVa").strip()
  dataset_json = source.get("SEGMENTATION_SERVER_DATASET_JSON", str(dataset_json_default)).strip()
  return ServerInferenceConfig(
    nnunet_raw=nnunet_raw,
    nnunet_preprocessed=_path_env(source, "SEGMENTATION_SERVER_NNUNET_PREPROCESSED", "/mnt/data0/LUO_Zheng/nnUNet_preprocessed"),
    nnunet_results=nnunet_results,
    output_root=_path_env(source, "SEGMENTATION_SERVER_OUTPUT_ROOT", "/mnt/data0/LUO_Zheng/result/gui_jobs"),
    dataset_id=dataset_id,
    configuration=configuration,
    plans=plans,
    folds=folds,
    gpus=gpus[:len(folds)],
    preprocess_workers=_int_env(source, "SEGMENTATION_SERVER_PREPROCESS_WORKERS", 4),
    ensemble_processes=_int_env(source, "SEGMENTATION_SERVER_ENSEMBLE_PROCESSES", 8),
    predict_command=source.get("SEGMENTATION_SERVER_PREDICT_COMMAND", "nnUNetv2_predict").strip() or "nnUNetv2_predict",
    ensemble_command=source.get("SEGMENTATION_SERVER_ENSEMBLE_COMMAND", "nnUNetv2_ensemble").strip() or "nnUNetv2_ensemble",
    python_command=source.get("SEGMENTATION_SERVER_PYTHON_COMMAND", "python").strip() or "python",
    evaluate_script=Path(evaluate_script) if evaluate_script else None,
    labels_dir=Path(labels_dir) if labels_dir else None,
    dataset_json=Path(dataset_json) if dataset_json else None,
  )


def server_inference_env(config: ServerInferenceConfig, gpu: str | None = None) -> dict[str, str]:
  env = os.environ.copy()
  env["nnUNet_raw"] = str(config.nnunet_raw)
  env["nnUNet_preprocessed"] = str(config.nnunet_preprocessed)
  env["nnUNet_results"] = str(config.nnunet_results)
  if gpu is not None:
    env["CUDA_VISIBLE_DEVICES"] = gpu
  return env


def build_server_fold_commands(config: ServerInferenceConfig, input_dir: Path, output_prefix: Path) -> list[ServerFoldCommand]:
  commands: list[ServerFoldCommand] = []
  for fold, gpu in zip(config.folds, config.gpus):
    output_dir = Path(f"{output_prefix}_f{fold}")
    command = [
      config.predict_command,
      "-d", config.dataset_id,
      "-c", config.configuration,
      "-p", config.plans,
      "-i", str(input_dir),
      "-o", str(output_dir),
      "-f", fold,
      "-npp", str(config.preprocess_workers),
      "--save_probabilities",
    ]
    commands.append(ServerFoldCommand(fold=fold, gpu=gpu, output_dir=output_dir, command=command, env=server_inference_env(config, gpu)))
  return commands


def build_server_ensemble_command(config: ServerInferenceConfig, fold_output_dirs: list[Path], output_dir: Path) -> list[str]:
  return [
    config.ensemble_command,
    "-i",
    *(str(path) for path in fold_output_dirs),
    "-o", str(output_dir),
    "-np", str(config.ensemble_processes),
  ]


def build_server_evaluate_command(config: ServerInferenceConfig, prediction_dir: Path, label_path: Path | None = None) -> list[str] | None:
  if not config.evaluate_script:
    return None
  reference = label_path or config.labels_dir
  if reference is None:
    return None
  command = [config.python_command, str(config.evaluate_script), str(prediction_dir), str(reference)]
  if config.dataset_json:
    command.extend(["--dataset_json", str(config.dataset_json)])
  command.extend(["--np", str(config.ensemble_processes)])
  return command
