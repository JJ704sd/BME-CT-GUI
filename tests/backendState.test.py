from __future__ import annotations

import importlib.util
import gzip
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_MAIN = PROJECT_ROOT / "server" / "main.py"

AMOS_CHECKPOINT_ARGS = {
    "configuration": "3d_fullres",
    "plans": {"dataset_name": "Dataset001_AMOS22"},
    "dataset_json": {
        "labels": {
            "background": 0,
            "spleen": 1,
            "right_kidney": 2,
            "left_kidney": 3,
            "gall_bladder": 4,
            "esophagus": 5,
            "liver": 6,
            "stomach": 7,
            "aorta": 8,
            "postcava": 9,
            "pancreas": 10,
            "right_adrenal_gland": 11,
            "left_adrenal_gland": 12,
            "duodenum": 13,
            "bladder": 14,
            "prostate_or_uterus": 15,
        }
    },
}


def load_server_module():
    spec = importlib.util.spec_from_file_location("segmentation_gui_server", SERVER_MAIN)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load server/main.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_test_output_dir(name: str) -> Path:
    preferred_root = os.environ.get("SEGMENTATION_TEST_TMP")
    if preferred_root:
        root = Path(preferred_root)
    else:
        root = Path.cwd() / ".test-output"
    output_dir = root / name
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def test_model_state_reports_missing_required_files():
    server = load_server_module()

    base = Path(r"D:\BME2026\BME_CT_Seg\missing-model")
    with patch.object(server, "FLARE_DATASET_JSON", base / "dataset.json"), \
         patch.object(server, "FLARE_PLANS_JSON", base / "plans.json"), \
         patch.object(server, "FLARE_CHECKPOINT", base / "fold_0" / "checkpoint_best.pth"), \
         patch.object(server, "PROJECT_CHECKPOINT", base / "checkpoint_best.pth"), \
         patch.object(server, "NNUNET_PYTHON_COMMAND", base / "missing_python.exe", create=True):
        state = server.get_model_state()

    assert state["status"] == "incomplete"
    assert state["mode"] == "unavailable"
    assert set(state["missing"]) == {"dataset.json", "plans.json", "checkpoint_best.pth", "nnUNetv2_python"}
    assert state["ready"] is False


def test_server_inference_config_reads_luozheng_runtime_env():
    server = load_server_module()

    with patch.dict(os.environ, {
        "SEGMENTATION_SERVER_GPUS": "0,1,2,3,4",
        "SEGMENTATION_SERVER_FOLDS": "0,1,2,3,4",
        "SEGMENTATION_SERVER_DATASET_ID": "1",
        "SEGMENTATION_SERVER_CONFIG": "3d_fullres",
        "SEGMENTATION_SERVER_PLANS": "nnUNetResEncUNetXLPlans",
        "SEGMENTATION_SERVER_NNUNET_RAW": "/mnt/data0/LUO_Zheng/nnUNet_raw",
        "SEGMENTATION_SERVER_NNUNET_PREPROCESSED": "/mnt/data0/LUO_Zheng/nnUNet_preprocessed",
        "SEGMENTATION_SERVER_NNUNET_RESULTS": "/mnt/data0/LUO_Zheng/nnUNet_results",
        "SEGMENTATION_SERVER_OUTPUT_ROOT": "/mnt/data0/LUO_Zheng/result/gui_jobs",
        "SEGMENTATION_SERVER_EVALUATE_SCRIPT": "/mnt/data0/LUO_Zheng/evaluate_full.py",
        "SEGMENTATION_SERVER_LABELS_DIR": "/mnt/data0/LUO_Zheng/amos22/amos22/labelsVa",
        "SEGMENTATION_SERVER_DATASET_JSON": "/mnt/data0/LUO_Zheng/nnUNet_results/Dataset001_AMOS22/nnUNetTrainer__nnUNetResEncUNetXLPlans__3d_fullres/dataset.json",
        "SEGMENTATION_SERVER_PREPROCESS_WORKERS": "4",
        "SEGMENTATION_SERVER_ENSEMBLE_PROCESSES": "8",
    }, clear=True):
        config = server.get_server_inference_config()

    assert config.gpus == ("0", "1", "2", "3", "4")
    assert config.folds == ("0", "1", "2", "3", "4")
    assert config.dataset_id == "1"
    assert config.configuration == "3d_fullres"
    assert config.plans == "nnUNetResEncUNetXLPlans"
    assert config.nnunet_raw == Path("/mnt/data0/LUO_Zheng/nnUNet_raw")
    assert config.nnunet_preprocessed == Path("/mnt/data0/LUO_Zheng/nnUNet_preprocessed")
    assert config.nnunet_results == Path("/mnt/data0/LUO_Zheng/nnUNet_results")
    assert config.output_root == Path("/mnt/data0/LUO_Zheng/result/gui_jobs")
    assert config.evaluate_script == Path("/mnt/data0/LUO_Zheng/evaluate_full.py")
    assert config.labels_dir == Path("/mnt/data0/LUO_Zheng/amos22/amos22/labelsVa")
    assert config.dataset_json == Path("/mnt/data0/LUO_Zheng/nnUNet_results/Dataset001_AMOS22/nnUNetTrainer__nnUNetResEncUNetXLPlans__3d_fullres/dataset.json")
    assert config.preprocess_workers == 4
    assert config.ensemble_processes == 8


def test_model_state_checks_server_required_files_only_for_server_runtime():
    server = load_server_module()

    base = make_test_output_dir("server-runtime-required-files")
    local_model = base / "local-model"
    local_model.mkdir(parents=True, exist_ok=True)
    dataset_json = local_model / "dataset.json"
    plans_json = local_model / "plans.json"
    checkpoint = local_model / "checkpoint_best.pth"
    predict_command = base / "python.exe"
    for path in [dataset_json, plans_json, checkpoint, predict_command]:
        path.write_text("ok", encoding="utf-8")

    missing_eval = base / "missing-evaluate_full.py"
    missing_server_dataset = base / "missing-server-dataset.json"

    with patch.dict(os.environ, {
        "SEGMENTATION_RUNTIME_TARGET": "server",
        "SEGMENTATION_SERVER_EVALUATE_SCRIPT": str(missing_eval),
        "SEGMENTATION_SERVER_DATASET_JSON": str(missing_server_dataset),
    }, clear=True), \
         patch.object(server, "FLARE_DATASET_JSON", dataset_json), \
         patch.object(server, "FLARE_PLANS_JSON", plans_json), \
         patch.object(server, "FLARE_CHECKPOINT", checkpoint), \
         patch.object(server, "PROJECT_CHECKPOINT", checkpoint), \
         patch.object(server, "NNUNET_PYTHON_COMMAND", predict_command, create=True), \
         patch.object(server, "load_checkpoint_init_args", return_value=AMOS_CHECKPOINT_ARGS):
        server_state = server.get_model_state()

    with patch.dict(os.environ, {
        "SEGMENTATION_RUNTIME_TARGET": "local",
        "SEGMENTATION_SERVER_EVALUATE_SCRIPT": str(missing_eval),
        "SEGMENTATION_SERVER_DATASET_JSON": str(missing_server_dataset),
    }, clear=True), \
         patch.object(server, "FLARE_DATASET_JSON", dataset_json), \
         patch.object(server, "FLARE_PLANS_JSON", plans_json), \
         patch.object(server, "FLARE_CHECKPOINT", checkpoint), \
         patch.object(server, "PROJECT_CHECKPOINT", checkpoint), \
         patch.object(server, "NNUNET_PYTHON_COMMAND", predict_command, create=True), \
         patch.object(server, "load_checkpoint_init_args", return_value=AMOS_CHECKPOINT_ARGS):
        local_state = server.get_model_state()

    assert server_state["runtime_target"] == "server"
    assert server_state["status"] == "incomplete"
    assert set(server_state["missing"]) == {"server_evaluate_full.py", "server_dataset.json"}
    assert server_state["server_inference"]["evaluate_script"] == str(missing_eval)
    assert server_state["server_inference"]["dataset_json"] == str(missing_server_dataset)

    assert local_state["runtime_target"] == "local"
    assert local_state["status"] == "ready"
    assert local_state["missing"] == []


def test_server_runtime_ready_does_not_require_local_model_files():
    server = load_server_module()

    base = make_test_output_dir("server-runtime-ignores-local-files")
    missing_local = base / "missing-local"
    evaluate_script = base / "evaluate_full.py"
    server_dataset = base / "server-dataset.json"
    server_raw = base / "server_nnunet_raw"
    server_preprocessed = base / "server_nnunet_preprocessed"
    server_results = base / "server_nnunet_results"
    server_output_root = base / "server_output_root"
    for path in (server_raw, server_preprocessed, server_results, server_output_root):
        path.mkdir(parents=True, exist_ok=True)
    evaluate_script.write_text("ok", encoding="utf-8")
    server_dataset.write_text("ok", encoding="utf-8")

    with patch.dict(os.environ, {
        "SEGMENTATION_RUNTIME_TARGET": "server",
        "SEGMENTATION_SERVER_EVALUATE_SCRIPT": str(evaluate_script),
        "SEGMENTATION_SERVER_DATASET_JSON": str(server_dataset),
        "SEGMENTATION_SERVER_NNUNET_RAW": str(server_raw),
        "SEGMENTATION_SERVER_NNUNET_PREPROCESSED": str(server_preprocessed),
        "SEGMENTATION_SERVER_NNUNET_RESULTS": str(server_results),
        "SEGMENTATION_SERVER_OUTPUT_ROOT": str(server_output_root),
    }, clear=True), \
         patch.object(server, "FLARE_DATASET_JSON", missing_local / "dataset.json"), \
         patch.object(server, "FLARE_PLANS_JSON", missing_local / "plans.json"), \
         patch.object(server, "FLARE_CHECKPOINT", missing_local / "checkpoint_best.pth"), \
         patch.object(server, "PROJECT_CHECKPOINT", missing_local / "checkpoint_best.pth"), \
         patch.object(server, "NNUNET_PYTHON_COMMAND", missing_local / "python.exe", create=True), \
         patch.object(server, "load_checkpoint_init_args", return_value=AMOS_CHECKPOINT_ARGS):
        state = server.get_model_state()

    assert state["runtime_target"] == "server"
    assert state["status"] == "ready"
    assert state["missing"] == []


def test_server_runtime_reports_missing_server_paths():
    """runtime_target=server 必须严格检查 6 个 server 路径：缺少时 missing
    包含对应项；这样 create_job 不会因 Linux 默认路径在 Windows 上
    /mnt/data0/... 不存在而误判 ready。"""
    server = load_server_module()

    base = make_test_output_dir("server-runtime-missing-server-paths")
    evaluate_script = base / "evaluate_full.py"
    server_dataset = base / "server-dataset.json"
    server_raw = base / "server_nnunet_raw"
    server_preprocessed = base / "server_nnunet_preprocessed"
    server_results = base / "server_nnunet_results"
    server_output_root = base / "server_output_root"
    evaluate_script.write_text("ok", encoding="utf-8")
    server_dataset.write_text("ok", encoding="utf-8")
    # 故意不 mkdir raw / preprocessed / results / output_root

    with patch.dict(os.environ, {
        "SEGMENTATION_RUNTIME_TARGET": "server",
        "SEGMENTATION_SERVER_EVALUATE_SCRIPT": str(evaluate_script),
        "SEGMENTATION_SERVER_DATASET_JSON": str(server_dataset),
        "SEGMENTATION_SERVER_NNUNET_RAW": str(server_raw),
        "SEGMENTATION_SERVER_NNUNET_PREPROCESSED": str(server_preprocessed),
        "SEGMENTATION_SERVER_NNUNET_RESULTS": str(server_results),
        "SEGMENTATION_SERVER_OUTPUT_ROOT": str(server_output_root),
    }, clear=True), \
         patch.object(server, "load_checkpoint_init_args", return_value=AMOS_CHECKPOINT_ARGS):
        state = server.get_model_state()

    assert state["runtime_target"] == "server"
    assert state["status"] == "incomplete"
    assert "server_nnunet_raw" in state["missing"]
    assert "server_nnunet_preprocessed" in state["missing"]
    assert "server_nnunet_results" in state["missing"]
    assert "server_output_root" in state["missing"]


def test_local_runtime_does_not_check_server_paths():
    """runtime_target=local 仍只检查 4 个本地文件，绝不能因 server 路径缺失而
    误报 missing。"""
    server = load_server_module()

    base = make_test_output_dir("local-runtime-ignores-server-paths")
    evaluate_script = base / "evaluate_full.py"
    server_dataset = base / "server-dataset.json"
    server_raw = base / "server_nnunet_raw"
    server_preprocessed = base / "server_nnunet_preprocessed"
    server_results = base / "server_nnunet_results"
    server_output_root = base / "server_output_root"
    evaluate_script.write_text("ok", encoding="utf-8")
    server_dataset.write_text("ok", encoding="utf-8")
    # server 4 个路径都缺失；本地 4 个文件必须独立检查

    with patch.dict(os.environ, {
        "SEGMENTATION_RUNTIME_TARGET": "local",
        "SEGMENTATION_SERVER_EVALUATE_SCRIPT": str(evaluate_script),
        "SEGMENTATION_SERVER_DATASET_JSON": str(server_dataset),
        "SEGMENTATION_SERVER_NNUNET_RAW": str(server_raw),
        "SEGMENTATION_SERVER_NNUNET_PREPROCESSED": str(server_preprocessed),
        "SEGMENTATION_SERVER_NNUNET_RESULTS": str(server_results),
        "SEGMENTATION_SERVER_OUTPUT_ROOT": str(server_output_root),
    }, clear=True), \
         patch.object(server, "load_checkpoint_init_args", return_value=AMOS_CHECKPOINT_ARGS), \
         patch.object(server, "FLARE_DATASET_JSON", base / "FLARE_DATASET_JSON"), \
         patch.object(server, "FLARE_PLANS_JSON", base / "FLARE_PLANS_JSON"), \
         patch.object(server, "FLARE_CHECKPOINT", base / "FLARE_CHECKPOINT"), \
         patch.object(server, "PROJECT_CHECKPOINT", base / "FLARE_CHECKPOINT"), \
         patch.object(server, "NNUNET_PYTHON_COMMAND", base / "python.exe", create=True):
        state = server.get_model_state()

    assert state["runtime_target"] == "local"
    assert "server_nnunet_raw" not in state["missing"]
    assert "server_nnunet_preprocessed" not in state["missing"]
    assert "server_nnunet_results" not in state["missing"]
    assert "server_output_root" not in state["missing"]
    assert "dataset.json" in state["missing"]
    assert "plans.json" in state["missing"]
    assert "checkpoint_best.pth" in state["missing"]
    assert "nnUNetv2_python" in state["missing"]


def test_health_and_models_expose_server_runtime_config():
    server = load_server_module()

    model_state = {
        "ready": True,
        "status": "ready",
        "mode": "real-nnunetv2",
        "runtime_target": "server",
        "missing": [],
        "checkpoint": "checkpoint_best.pth",
        "confidence_threshold_effective": False,
        "server_inference": {
            "dataset_id": "1",
            "configuration": "3d_fullres",
            "plans": "nnUNetResEncUNetXLPlans",
            "folds": ["0", "1", "2", "3", "4"],
            "gpus": ["0", "1", "2", "3", "4"],
            "output_root": "/mnt/data0/LUO_Zheng/result/gui_jobs",
            "evaluate_script": "/mnt/data0/LUO_Zheng/evaluate_full.py",
            "dataset_json": "/mnt/data0/LUO_Zheng/nnUNet_results/Dataset001_AMOS22/nnUNetTrainer__nnUNetResEncUNetXLPlans__3d_fullres/dataset.json",
        },
    }

    with patch.object(server, "get_model_state", return_value=model_state), \
         patch.object(server, "read_labels", return_value=[]):
        client = TestClient(server.app)
        health = client.get("/api/health").json()
        models = client.get("/api/models").json()

    assert health["model_status"]["runtime_target"] == "server"
    assert health["model_status"]["server_inference"]["gpus"] == ["0", "1", "2", "3", "4"]
    assert models["models"][0]["runtime_target"] == "server"
    assert models["models"][0]["server_inference"]["plans"] == "nnUNetResEncUNetXLPlans"


def test_create_server_job_rejects_missing_server_runtime_files():
    server = load_server_module()

    base = make_test_output_dir("server-job-missing-runtime-files")
    local_model = base / "local-model"
    local_model.mkdir(parents=True, exist_ok=True)
    dataset_json = local_model / "dataset.json"
    plans_json = local_model / "plans.json"
    checkpoint = local_model / "checkpoint_best.pth"
    predict_command = base / "python.exe"
    for path in [dataset_json, plans_json, checkpoint, predict_command]:
        path.write_text("ok", encoding="utf-8")

    missing_eval = base / "missing-evaluate_full.py"
    missing_server_dataset = base / "missing-server-dataset.json"

    with patch.dict(os.environ, {
        "SEGMENTATION_SERVER_EVALUATE_SCRIPT": str(missing_eval),
        "SEGMENTATION_SERVER_DATASET_JSON": str(missing_server_dataset),
    }, clear=True), \
         patch.object(server, "WORK_DIR", base / "work"), \
         patch.object(server, "FLARE_DATASET_JSON", dataset_json), \
         patch.object(server, "FLARE_PLANS_JSON", plans_json), \
         patch.object(server, "FLARE_CHECKPOINT", checkpoint), \
         patch.object(server, "PROJECT_CHECKPOINT", checkpoint), \
         patch.object(server, "NNUNET_PYTHON_COMMAND", predict_command, create=True), \
         patch.object(server, "load_checkpoint_init_args", return_value=AMOS_CHECKPOINT_ARGS):
        client = TestClient(server.app)
        response = client.post(
            "/api/segment/jobs",
            files={"file": ("case_0000.nii.gz", b"nifti", "application/octet-stream")},
            data={"model_id": "abdomen", "runtime_target": "server"},
        )

    assert response.status_code == 503
    body = response.json()["detail"]
    assert body["model_status"]["runtime_target"] == "server"
    assert set(body["missing"]) == {"server_evaluate_full.py", "server_dataset.json"}


def test_create_job_rejects_when_model_is_not_ready():
    server = load_server_module()

    with patch.object(server, "get_model_state", return_value={
        "ready": False,
        "status": "incomplete",
        "mode": "unavailable",
        "missing": ["plans.json"],
    }):
        client = TestClient(server.app)
        response = client.post(
            "/api/segment/jobs",
            files={"file": ("case_0000.nii.gz", b"nifti", "application/octet-stream")},
            data={"model_id": "abdomen"},
        )

    assert response.status_code == 503
    assert "plans.json" in response.text
    body = response.json()["detail"]
    assert "本地 nnUNetv2" in body["message"]
    assert "服务器" not in body["message"]


def test_create_job_503_message_reflects_server_runtime():
    server = load_server_module()

    with patch.object(server, "get_model_state", return_value={
        "ready": False,
        "status": "incomplete",
        "mode": "unavailable",
        "runtime_target": "server",
        "missing": ["server_evaluate_full.py", "server_dataset.json"],
    }):
        client = TestClient(server.app)
        response = client.post(
            "/api/segment/jobs",
            files={"file": ("case_0000.nii.gz", b"nifti", "application/octet-stream")},
            data={"model_id": "abdomen", "runtime_target": "server"},
        )

    assert response.status_code == 503
    body = response.json()["detail"]
    assert "服务器推理" in body["message"]
    assert "本地 nnUNetv2" not in body["message"]
    assert body["model_status"]["runtime_target"] == "server"


def test_server_source_does_not_log_uploaded_filenames():
    source = SERVER_MAIN.read_text(encoding="utf-8")
    assert "[create_job] received file=" not in source


def test_predict_command_uses_model_folder_and_job_io():
    server = load_server_module()

    with patch.dict(os.environ, {
        "SEGMENTATION_PREPROCESS_WORKERS": "3",
        "SEGMENTATION_EXPORT_WORKERS": "2",
        "SEGMENTATION_INFERENCE_PROFILE": "quality",
        "SEGMENTATION_DISABLE_TTA": "0",
        "SEGMENTATION_TILE_STEP_SIZE": "0.5",
    }, clear=True):
        command = server.build_predict_command(
            input_dir=Path("work/input"),
            output_dir=Path("work/output"),
            device="cpu",
            model_dir=Path("runtime/model"),
        )

    assert str(server.NNUNET_PYTHON_COMMAND) == command[0]
    assert command[1] == "-c"
    assert "predict_entry_point_modelfolder" in command[2]
    assert command[3:] == [
        "-i", "work\\input",
        "-o", "work\\output",
        "-m", "runtime\\model",
        "-f", "0",
        "-chk", "checkpoint_best.pth",
        "-npp", "3",
        "-nps", "2",
        "-device", "cpu",
        "--disable_progress_bar",
    ]


def test_predict_worker_counts_have_safe_defaults_and_clamps():
    server = load_server_module()

    with patch.dict(os.environ, {}, clear=True):
        assert server.get_predict_worker_counts() == (2, 2)
    with patch.dict(os.environ, {
        "SEGMENTATION_PREPROCESS_WORKERS": "0",
        "SEGMENTATION_EXPORT_WORKERS": "99",
    }):
        assert server.get_predict_worker_counts() == (1, 8)
    with patch.dict(os.environ, {
        "SEGMENTATION_PREPROCESS_WORKERS": "bad",
        "SEGMENTATION_EXPORT_WORKERS": "bad",
    }):
        assert server.get_predict_worker_counts() == (2, 2)


def test_fast_inference_profile_controls_nnunet_prediction_flags():
    server = load_server_module()

    with patch.dict(os.environ, {
        "SEGMENTATION_INFERENCE_PROFILE": "fast",
        "SEGMENTATION_NOT_ON_DEVICE": "1",
    }, clear=True):
        options = server.get_inference_options()
        command = server.build_predict_command(
            input_dir=Path("work/input"),
            output_dir=Path("work/output"),
            device="cuda",
            model_dir=Path("runtime/model"),
            inference_options=options,
        )

    assert options == {
        "profile": "fast",
        "tile_step_size": 1.0,
        "disable_tta": True,
        "not_on_device": True,
    }
    assert "-step_size" in command
    assert command[command.index("-step_size") + 1] == "1"
    assert "--disable_tta" in command
    assert "--not_on_device" in command


def test_create_job_uses_requested_inference_profile_for_options_and_cache_key():
    server = load_server_module()
    temp_root = make_test_output_dir(f"requested-profile-job-{os.getpid()}")
    captured_model_state = {}

    class NoopThread:
        def __init__(self, *_args, **_kwargs):
            pass

        def start(self):
            pass

    def fake_cache_key(_input_sha, model_state):
        captured_model_state.update(model_state)
        return "requested-profile-cache-key"

    with patch.dict(os.environ, {
        "SEGMENTATION_INFERENCE_PROFILE": "quality",
    }, clear=True), \
         patch.object(server, "WORK_DIR", temp_root), \
         patch.object(server, "get_model_state", return_value={
             "ready": True,
             "status": "ready",
             "mode": "real-nnunetv2",
             "missing": [],
         }), \
         patch.object(server, "build_prediction_cache_key", side_effect=fake_cache_key), \
         patch.object(server, "find_cached_prediction", return_value=None), \
         patch.object(server.threading, "Thread", NoopThread):
        client = TestClient(server.app)
        response = client.post(
            "/api/segment/jobs",
            files={"file": ("case_0000.nii.gz", b"profile-input", "application/octet-stream")},
            data={"model_id": "abdomen", "inference_profile": "fast", "runtime_target": "server", "label_taxonomy": "AMOS22"},
        )
        body = response.json()
        state = client.get(f"/api/segment/jobs/{body['job_id']}").json()

    expected_options = {
        "profile": "fast",
        "tile_step_size": 1.0,
        "disable_tta": True,
        "not_on_device": False,
    }
    assert response.status_code == 200
    assert body["inference_profile"] == "fast"
    assert body["inference_options"] == expected_options
    assert body["runtime_target"] == "server"
    assert body["label_taxonomy"] == "AMOS22"
    assert state["inference_profile"] == "fast"
    assert state["inference_options"] == expected_options
    assert state["runtime_target"] == "server"
    assert state["label_taxonomy"] == "AMOS22"
    assert captured_model_state["inference_options"] == expected_options


def test_create_job_normalizes_nii_upload_to_model_file_ending():
    server = load_server_module()
    temp_root = make_test_output_dir(f"normalized-input-ending-{os.getpid()}")

    class NoopThread:
        def __init__(self, *_args, **_kwargs):
            pass

        def start(self):
            pass

    with patch.object(server, "WORK_DIR", temp_root), \
         patch.object(server, "get_model_state", return_value={
             "ready": True,
             "status": "ready",
             "mode": "real-nnunetv2",
             "missing": [],
             "model_file_ending": ".nii.gz",
         }), \
         patch.object(server, "find_cached_prediction", return_value=None), \
         patch.object(server.threading, "Thread", NoopThread):
        client = TestClient(server.app)
        response = client.post(
            "/api/segment/jobs",
            files={"file": ("case_0000.nii", b"plain-nifti-bytes", "application/octet-stream")},
            data={"model_id": "abdomen"},
        )
        body = response.json()

    input_dir = temp_root / body["job_id"] / "input"
    normalized = input_dir / f"{body['job_id']}_0000.nii.gz"
    legacy_plain = input_dir / f"{body['job_id']}_0000.nii"

    assert response.status_code == 200
    assert normalized.exists()
    assert not legacy_plain.exists()
    assert gzip.decompress(normalized.read_bytes()) == b"plain-nifti-bytes"


def test_prediction_cache_key_changes_with_inference_options():
    server = load_server_module()
    base_state = {
        "checkpoint_dataset_name": "Dataset001_AMOS22",
        "checkpoint_configuration": "3d_fullres",
        "labels_source": "checkpoint",
    }

    with patch.object(server, "get_checkpoint_sha256", return_value="checkpoint-sha"):
        quality_key = server.build_prediction_cache_key("input-sha", {
            **base_state,
            "inference_options": {
                "profile": "quality",
                "tile_step_size": 0.5,
                "disable_tta": False,
                "not_on_device": False,
            },
        })
        fast_key = server.build_prediction_cache_key("input-sha", {
            **base_state,
            "inference_options": {
                "profile": "fast",
                "tile_step_size": 1.0,
                "disable_tta": True,
                "not_on_device": False,
            },
        })

    assert quality_key != fast_key


def test_legacy_reference_cache_requires_matching_summary_cache_key():
    server = load_server_module()
    temp_root = make_test_output_dir("legacy-cache-key-guard")
    current_job_id = "current0001"
    legacy_job_id = "009d4efdc5f6"
    input_dir = temp_root / current_job_id / "input"
    legacy_output = temp_root / legacy_job_id / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    legacy_output.mkdir(parents=True, exist_ok=True)
    debug_original = temp_root / "amos_0117.nii.gz"
    input_path = input_dir / f"{current_job_id}_0000.nii.gz"
    debug_original.write_bytes(b"same-debug-input")
    input_path.write_bytes(b"same-debug-input")
    (legacy_output / f"{legacy_job_id}.nii.gz").write_bytes(b"legacy-result")

    with patch.object(server, "WORK_DIR", temp_root), \
         patch.object(server, "DEBUG_ORIGINAL", debug_original):
        assert server.find_cached_prediction("new-cache-key", input_path, current_job_id) is None


def test_persistent_worker_key_includes_inference_options():
    server = load_server_module()
    quality_options = {
        "profile": "quality",
        "tile_step_size": 0.5,
        "disable_tta": False,
        "not_on_device": False,
    }
    fast_options = {
        "profile": "fast",
        "tile_step_size": 1.0,
        "disable_tta": True,
        "not_on_device": False,
    }

    quality_key = server.get_persistent_worker_key(Path("runtime/model"), quality_options)
    fast_key = server.get_persistent_worker_key(Path("runtime/model"), fast_options)

    assert quality_key != fast_key
    assert quality_key[-3:] == (0.5, False, False)
    assert fast_key[-3:] == (1.0, True, False)


def test_same_file_content_uses_samefile_fast_path():
    server = load_server_module()
    output_dir = make_test_output_dir("samefile-fast-path")
    path = output_dir / "checkpoint_best.pth"
    path.write_bytes(b"checkpoint")

    with patch.object(server.os.path, "samefile", return_value=True), \
         patch.object(server, "file_sha256", side_effect=AssertionError("same file should not be hashed")):
        assert server.same_file_content(path, path) is True


def test_job_phase_timings_are_recorded():
    server = load_server_module()
    job = server.Job(id="timing0001")

    with patch.object(server.time, "perf_counter", side_effect=[10.0, 12.345, 20.0, 20.5]):
        server.start_job_phase(job, "prepare_runtime_model")
        server.finish_job_phase(job, "prepare_runtime_model")
        server.start_job_phase(job, "nnunet_process")
        server.finish_job_phase(job, "nnunet_process")

    summary = server.build_job_summary(job)
    assert summary["phase_timings"]["prepare_runtime_model"] == 2.345
    assert summary["phase_timings"]["nnunet_process"] == 0.5


def test_project_checkpoint_is_preferred_as_weight_source():
    server = load_server_module()

    base = make_test_output_dir("project-checkpoint-model")
    model_dir = base / "model"
    dataset_json = model_dir / "dataset.json"
    plans_json = model_dir / "plans.json"
    flare_checkpoint = model_dir / "fold_0" / "checkpoint_best.pth"
    project_checkpoint = base / "checkpoint_best.pth"
    runtime_checkpoint = base / "runtime_model" / "fold_0" / "checkpoint_best.pth"
    predict_command = base / "nnUNetv2_predict_from_modelfolder.exe"

    dataset_json.parent.mkdir(parents=True, exist_ok=True)
    flare_checkpoint.parent.mkdir(parents=True, exist_ok=True)
    dataset_json.write_text("{}", encoding="utf-8")
    plans_json.write_text("{}", encoding="utf-8")
    flare_checkpoint.write_bytes(b"model-folder-checkpoint")
    project_checkpoint.write_bytes(b"project-checkpoint")
    predict_command.write_text("placeholder", encoding="utf-8")

    with patch.object(server, "FLARE_MODEL_DIR", model_dir), \
         patch.object(server, "FLARE_DATASET_JSON", dataset_json), \
         patch.object(server, "FLARE_PLANS_JSON", plans_json), \
         patch.object(server, "FLARE_CHECKPOINT", flare_checkpoint), \
         patch.object(server, "PROJECT_CHECKPOINT", project_checkpoint), \
         patch.object(server, "RUNTIME_CHECKPOINT", runtime_checkpoint), \
         patch.object(server, "NNUNET_PYTHON_COMMAND", predict_command, create=True), \
         patch.object(server, "load_checkpoint_init_args", return_value=AMOS_CHECKPOINT_ARGS):
        state = server.get_model_state()

    assert state["checkpoint_source"] == str(project_checkpoint)
    assert state["checkpoint_runtime"] == str(runtime_checkpoint)
    assert state["checkpoint_in_model_folder"] == str(flare_checkpoint)
    assert state["checkpoint_source_matches_model_folder"] is False
    assert state["checkpoint_dataset_name"] == "Dataset001_AMOS22"
    assert state["checkpoint_configuration"] == "3d_fullres"
    assert state["labels_source"] == "checkpoint"
    assert state["predict_device"] in {"cpu", "cuda", "mps"}


def test_dataset_labels_use_frontend_canonical_ids():
    server = load_server_module()

    with patch.object(server, "load_checkpoint_init_args", return_value=AMOS_CHECKPOINT_ARGS):
        labels = server.read_labels()
    by_label = {item["label"]: item for item in labels}

    assert by_label[9]["id"] == "ivc"
    assert by_label[11]["id"] == "right-adrenal-gland"
    assert by_label[12]["id"] == "left-adrenal-gland"
    assert by_label[14]["id"] == "bladder"
    assert by_label[15]["id"] == "prostate-or-uterus"


def test_label_metrics_compare_prediction_with_reference():
    server = load_server_module()

    prediction = [
        [0, 1, 2, 2],
        [0, 1, 0, 2],
    ]
    reference = [
        [0, 1, 1, 2],
        [0, 1, 2, 2],
    ]
    report = server.compute_label_metrics(
        prediction,
        reference,
        [
            {"label": 1, "nameZh": "肝脏"},
            {"label": 2, "nameZh": "右肾"},
        ],
    )

    assert report["status"] == "review"
    assert report["accepted"] is False
    assert report["sample_id"] == "amos_0117"
    assert report["mean_dice"] == 0.733333
    assert report["min_dice"] == 0.666667
    assert report["foreground_dice"] == 0.909091
    assert report["mean_iou"] == 0.583333
    assert report["min_iou"] == 0.5
    assert report["foreground_iou"] == 0.833333
    assert report["labels"][0]["dice"] == 0.8
    assert report["labels"][0]["iou"] == 0.666667
    assert report["labels"][0]["union_voxels"] == 3
    assert report["labels"][1]["dice"] == 0.666667
    assert report["labels"][1]["iou"] == 0.5
    assert report["labels"][1]["union_voxels"] == 4
    assert report["labels"][1]["intersection_voxels"] == 2
    assert report["surface_distance_unit"] == "mm"
    assert report["spacing"] == [1.0, 1.0]
    assert report["pixel_accuracy"] == 0.75
    assert report["mean_pixel_accuracy"] is not None
    assert report["min_pixel_accuracy"] is not None
    assert report["foreground_pixel_accuracy"] is not None
    for label_metric in report["labels"]:
        assert "pixel_accuracy" in label_metric
        assert "asd" in label_metric
        assert "hd" in label_metric
        assert "hd95" in label_metric


def test_label_metrics_surface_distance_handles_empty_masks():
    server = load_server_module()

    prediction = [
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    reference = [
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    report = server.compute_label_metrics(
        prediction,
        reference,
        [
            {"label": 1, "nameZh": "肝脏"},
        ],
        spacing=(1.0, 1.0),
    )

    assert report["status"] == "passed"
    assert report["mean_dice"] is None
    assert report["mean_asd"] is None
    assert report["max_asd"] is None
    assert report["mean_hd"] is None
    assert report["mean_hd95"] is None
    assert report["surface_distance_unit"] == "mm"


def test_label_metrics_hd95_and_asd_decrease_with_better_overlap():
    server = load_server_module()

    reference = [[0, 0, 0, 0, 0, 0, 0, 0]] * 8
    for row_index, row in enumerate(reference):
        reference[row_index] = list(row)
        for column in range(2, 6):
            reference[row_index][column] = 1

    close_prediction = [list(row) for row in reference]
    far_prediction = [[0] * 8 for _ in range(8)]
    for row_index in range(8):
        for column in range(0, 4):
            far_prediction[row_index][column] = 1

    close_report = server.compute_label_metrics(
        close_prediction,
        reference,
        [{"label": 1, "nameZh": "肝脏"}],
        spacing=(1.0, 1.0),
    )
    far_report = server.compute_label_metrics(
        far_prediction,
        reference,
        [{"label": 1, "nameZh": "肝脏"}],
        spacing=(1.0, 1.0),
    )

    close_label = close_report["labels"][0]
    far_label = far_report["labels"][0]
    assert close_label["dice"] == 1.0
    assert close_label["asd"] is not None and close_label["asd"] == 0.0
    assert close_label["hd95"] is not None and close_label["hd95"] == 0.0
    assert far_label["dice"] is not None and far_label["dice"] < close_label["dice"]
    assert far_label["asd"] is not None and far_label["asd"] > close_label["asd"]
    assert far_label["hd95"] is not None and far_label["hd95"] > close_label["hd95"]
    assert close_report["mean_asd"] == 0.0
    assert close_report["max_asd"] == 0.0
    assert close_report["mean_hd95"] == 0.0
    assert close_report["max_hd95"] == 0.0


def test_surface_distances_matches_legacy_individual_functions():
    """Regression guard: the merged surface_distances() must produce values that
    match the three legacy functions (average_surface_distance, hausdorff_95,
    hausdorff_distance_full) to floating-point precision, across diverse mask
    shapes and overlap patterns.
    """
    import numpy as np

    server = load_server_module()
    surface_distances = server.surface_distances
    average_surface_distance = server.average_surface_distance
    hausdorff_95 = server.hausdorff_95
    hausdorff_distance_full = server.hausdorff_distance_full

    rng = np.random.default_rng(20260603)
    shapes = [(6, 6), (8, 8, 4), (12, 10, 8), (4, 4, 4, 3)]
    spacings = [(1.0, 1.0), (1.0, 1.0, 1.0), (0.5, 0.7, 2.5), (1.0, 1.0, 1.0, 1.0)]

    for shape, spacing in zip(shapes, spacings):
        for scenario in range(8):
            pred = (rng.random(shape) < 0.35).astype(bool)
            ref = (rng.random(shape) < 0.35).astype(bool)
            if scenario == 0:
                pred = np.zeros(shape, dtype=bool)
            elif scenario == 1:
                ref = np.zeros(shape, dtype=bool)
            elif scenario == 2:
                pred = np.zeros(shape, dtype=bool)
                ref = np.zeros(shape, dtype=bool)
            elif scenario == 3:
                pred = ref  # perfect overlap, only surface is the outer ring
            elif scenario == 4:
                ref = ~pred & (rng.random(shape) < 0.3)  # disjoint
            elif scenario == 5:
                # one-voxel-thick sheet that should still produce a non-empty surface
                pred = np.zeros(shape, dtype=bool)
                if pred.ndim >= 2:
                    pred[(slice(None),) * 2 + (0,) * (pred.ndim - 2)] = True
                ref = pred.copy()
            elif scenario == 6:
                # single-voxel mask — surface should equal the mask itself
                pred = np.zeros(shape, dtype=bool)
                pred[(0,) * pred.ndim] = True
                ref = np.zeros(shape, dtype=bool)
                ref[(0,) * pred.ndim] = True
            # scenario 7 is the default random case

            merged = surface_distances(pred, ref, spacing)
            legacy_asd = average_surface_distance(pred, ref, spacing)
            legacy_hd = hausdorff_distance_full(pred, ref, spacing)
            legacy_hd95 = hausdorff_95(pred, ref, spacing)

            if merged is None:
                assert legacy_asd is None, f"shape={shape} scenario={scenario}: ASD mismatch (legacy={legacy_asd}, merged=None)"
                assert legacy_hd is None, f"shape={shape} scenario={scenario}: HD mismatch (legacy={legacy_hd}, merged=None)"
                assert legacy_hd95 is None, f"shape={shape} scenario={scenario}: HD95 mismatch (legacy={legacy_hd95}, merged=None)"
            else:
                assert legacy_asd is not None
                assert legacy_hd is not None
                assert legacy_hd95 is not None
                assert abs(merged["asd"] - legacy_asd) < 1e-9, f"shape={shape} scenario={scenario}: ASD {merged['asd']} vs {legacy_asd}"
                assert abs(merged["hd"] - legacy_hd) < 1e-9, f"shape={shape} scenario={scenario}: HD {merged['hd']} vs {legacy_hd}"
                assert abs(merged["hd95"] - legacy_hd95) < 1e-9, f"shape={shape} scenario={scenario}: HD95 {merged['hd95']} vs {legacy_hd95}"


def test_surface_distances_uses_fewer_distance_transforms_than_legacy():
    """Performance guard: surface_distances() must call distance_transform_edt at
    most 2 times per invocation, while the three legacy functions call it 6 times
    combined. Count via patching scipy.ndimage.distance_transform_edt directly
    (surface_distances imports scipy.ndimage locally, so we patch the source).
    """
    import numpy as np
    from unittest.mock import patch
    from scipy import ndimage

    server = load_server_module()
    surface_distances = server.surface_distances
    pred = np.zeros((10, 10, 10), dtype=bool)
    pred[2:5, 2:5, 2:5] = True
    ref = np.zeros((10, 10, 10), dtype=bool)
    ref[3:6, 3:6, 3:6] = True

    call_counter = {"count": 0}
    real_edt = ndimage.distance_transform_edt

    def counting_edt(*args, **kwargs):
        call_counter["count"] += 1
        return real_edt(*args, **kwargs)

    with patch("scipy.ndimage.distance_transform_edt", side_effect=counting_edt):
        result = surface_distances(pred, ref, (1.0, 1.0, 1.0))

    assert result is not None
    assert call_counter["count"] == 2, f"surface_distances should call EDT exactly twice, got {call_counter['count']}"


def test_compute_label_metrics_with_surface_distances_faster_than_legacy():
    """Sanity check that the per-label path through surface_distances() is
    faster than the three legacy functions in series. Not a strict benchmark,
    just a smoke guard against future regressions that re-introduce redundant
    crops/surfaces/EDTs.
    """
    import numpy as np
    import time

    server = load_server_module()
    rng = np.random.default_rng(7)
    shape = (60, 60, 30)
    pred = (rng.random(shape) < 0.25).astype(bool)
    ref = (rng.random(shape) < 0.25).astype(bool)
    spacing = (0.8, 0.8, 2.0)

    t0 = time.perf_counter()
    legacy = [
        server.average_surface_distance(pred, ref, spacing),
        server.hausdorff_95(pred, ref, spacing),
        server.hausdorff_distance_full(pred, ref, spacing),
    ]
    legacy_seconds = time.perf_counter() - t0

    t0 = time.perf_counter()
    merged = server.surface_distances(pred, ref, spacing)
    merged_seconds = time.perf_counter() - t0

    assert merged is not None
    assert all(value is not None for value in legacy)
    assert abs(merged["asd"] - legacy[0]) < 1e-9
    assert abs(merged["hd95"] - legacy[1]) < 1e-9
    assert abs(merged["hd"] - legacy[2]) < 1e-9
    # Merged path does 2 EDTs vs legacy 6 EDTs. Allow 30% margin for tiny shapes
    # where the constant overhead of cropping/surface extraction dominates.
    assert merged_seconds < legacy_seconds * 0.7, (
        f"surface_distances should be at least 30% faster than the 3 legacy "
        f"functions combined; legacy={legacy_seconds:.3f}s merged={merged_seconds:.3f}s"
    )


def test_validation_summary_json_preserves_chinese_without_bom():
    server = load_server_module()
    validation = {
        "status": "review",
        "sample_id": "amos_0117",
        "accepted": False,
        "mean_dice": 0.891327,
        "message": "标准答案验证未达阈值，建议人工复核。",
        "labels": [
            {"label": 1, "name": "脾脏", "dice": 0.979085},
        ],
    }

    summary_path = server.write_validation_summary(make_test_output_dir("validation-summary"), validation)
    raw = summary_path.read_bytes()
    parsed = json.loads(raw.decode("utf-8"))

    assert raw[:3] != b"\xef\xbb\xbf"
    assert parsed["message"] == "标准答案验证未达阈值，建议人工复核。"
    assert parsed["labels"][0]["name"] == "脾脏"


def test_samples_api_exposes_reference_case_metadata():
    temp_root = make_test_output_dir("reference-case-default-metadata")
    debug_original = temp_root / "amos_0117(3).nii.gz"
    debug_label = temp_root / "amos_0117(2).nii.gz"
    debug_original.write_bytes(b"debug-original")
    debug_label.write_bytes(b"debug-label")
    registry = temp_root / "reference_cases.json"
    registry.write_text(json.dumps({
        "samples": [
            {
                "id": "amos_0117",
                "name": "AMOS 0117",
                "dataset": "AMOS22",
                "modality": "CT",
                "role": "built-in-reference",
                "description": "内置参考病例，用于演示、回归和标准答案 Dice 验证。",
                "original": str(debug_original),
                "label": str(debug_label),
                "original_filename": "amos_0117_original.nii.gz",
                "label_filename": "amos_0117_label.nii.gz",
            }
        ]
    }, ensure_ascii=False), encoding="utf-8")

    with patch.dict(os.environ, {"SEGMENTATION_REFERENCE_CASES_JSON": str(registry)}):
        server = load_server_module()
        client = TestClient(server.app)
        response = client.get("/api/samples")
        body = response.json()
        sample = body["samples"][0]

    assert response.status_code == 200
    assert sample["id"] == "amos_0117"
    assert sample["name"] == "AMOS 0117"
    assert sample["dataset"] == "AMOS22"
    assert sample["modality"] == "CT"
    assert sample["role"] == "built-in-reference"
    assert sample["original_url"] == "/api/samples/amos_0117/original"
    assert sample["label_url"] == "/api/samples/amos_0117/label"
    assert sample["original_filename"] == "amos_0117_original.nii.gz"
    assert sample["label_filename"] == "amos_0117_label.nii.gz"
    assert "标准答案" in sample["description"]
    assert isinstance(sample["has_original"], bool)
    assert isinstance(sample["has_label"], bool)
    assert sample["validation_available"] == (sample["has_original"] and sample["has_label"])


def test_local_reference_cases_include_flare22_with_label():
    """Regression: the local reference case file (loaded by the candidates fallback)
    must expose FLARE22 Tr 0009 with its label so the GUI dropdown is selectable.
    """
    local_registry = (PROJECT_ROOT / "nnunetv2_files" / "reference_cases.local.json").resolve()
    if not local_registry.exists():
        print("[skip] local reference_cases.local.json not present in this environment")
        return
    with patch.dict(os.environ, {"SEGMENTATION_REFERENCE_CASES_JSON": str(local_registry)}):
        server = load_server_module()
        client = TestClient(server.app)
        response = client.get("/api/samples")
        body = response.json()

    ids = {sample["id"]: sample for sample in body["samples"]}
    assert "amos_0117" in ids
    assert ids["amos_0117"]["has_original"] is True
    assert ids["amos_0117"]["has_label"] is True
    assert "flare22_tr_0009" in ids
    assert ids["flare22_tr_0009"]["has_original"] is True
    assert ids["flare22_tr_0009"]["has_label"] is True, (
        "FLARE22 Tr 0009 must have a resolvable label file in the local registry"
    )


def test_log_reference_case_warnings_emits_for_missing_files():
    from contextlib import redirect_stdout
    from io import StringIO
    server = load_server_module()
    temp_root = make_test_output_dir("reference-case-warnings")
    present_original = temp_root / "present.nii.gz"
    present_label = temp_root / "present_label.nii.gz"
    present_original.write_bytes(b"present")
    present_label.write_bytes(b"present-label")
    missing_label = temp_root / "missing_label.nii.gz"
    registry = temp_root / "reference_cases.json"
    registry.write_text(json.dumps({
        "samples": [
            {
                "id": "case_present",
                "name": "Case Present",
                "dataset": "FLARE",
                "modality": "CT",
                "role": "built-in-reference",
                "description": "all good",
                "original": str(present_original),
                "label": str(present_label),
            },
            {
                "id": "case_missing_label",
                "name": "Case Missing Label",
                "dataset": "FLARE",
                "modality": "CT",
                "role": "external-reference",
                "description": "label file is missing on disk",
                "original": str(present_original),
                "label": str(missing_label),
            },
            {
                "id": "case_missing_original",
                "name": "Case Missing Original",
                "dataset": "FLARE",
                "modality": "CT",
                "role": "external-reference",
                "description": "original file is missing on disk",
                "original": str(temp_root / "missing_original.nii.gz"),
            },
        ]
    }, ensure_ascii=False), encoding="utf-8")
    with patch.dict(os.environ, {"SEGMENTATION_REFERENCE_CASES_JSON": str(registry)}):
        server2 = load_server_module()
        sink = StringIO()
        with redirect_stdout(sink):
            server2.log_reference_case_warnings()
    captured = sink.getvalue()
    assert "case_present" not in captured
    assert "case_missing_label" in captured
    assert "label missing" in captured
    assert "case_missing_original" in captured
    assert "original missing" in captured


def test_samples_api_reads_configured_reference_cases():
    temp_root = make_test_output_dir("reference-case-registry")
    case_a = temp_root / "case_a.nii.gz"
    label_a = temp_root / "case_a_label.nii.gz"
    case_b = temp_root / "case_b.nii.gz"
    case_a.write_bytes(b"case-a")
    label_a.write_bytes(b"label-a")
    case_b.write_bytes(b"case-b")
    registry = temp_root / "reference_cases.json"
    registry.write_text(json.dumps({
        "samples": [
            {
                "id": "amos_0117",
                "name": "AMOS 0117",
                "dataset": "AMOS22",
                "original": str(case_a),
                "label": str(label_a),
                "description": "AMOS reference",
            },
            {
                "id": "flare_demo",
                "name": "FLARE Demo",
                "dataset": "FLARE",
                "original": "case_b.nii.gz",
                "description": "FLARE reference without label",
            },
        ]
    }, ensure_ascii=False), encoding="utf-8")

    with patch.dict(os.environ, {"SEGMENTATION_REFERENCE_CASES_JSON": str(registry)}):
        server = load_server_module()
        client = TestClient(server.app)
        response = client.get("/api/samples")
        body = response.json()
        original_response = client.get("/api/samples/flare_demo/original")
        label_response = client.get("/api/samples/flare_demo/label")

    assert response.status_code == 200
    assert [sample["id"] for sample in body["samples"]] == ["amos_0117", "flare_demo"]
    assert body["samples"][1]["name"] == "FLARE Demo"
    assert body["samples"][1]["dataset"] == "FLARE"
    assert body["samples"][1]["original"] == str(case_b)
    assert body["samples"][1]["has_original"] is True
    assert body["samples"][1]["has_label"] is False
    assert body["samples"][1]["validation_available"] is False
    assert body["samples"][1]["original_url"] == "/api/samples/flare_demo/original"
    assert body["samples"][1]["label_url"] == "/api/samples/flare_demo/label"
    assert original_response.status_code == 200
    assert original_response.content == b"case-b"
    assert label_response.status_code == 404


def test_job_state_reports_result_readiness_after_completion():
    server = load_server_module()

    job_id = "jobstate0001"
    validation = {
        "status": "passed",
        "sample_id": "amos_0117",
        "mean_dice": 0.91,
        "min_dice": 0.77,
        "foreground_dice": 0.93,
        "accepted": True,
        "message": "达标",
    }
    result_path = PROJECT_ROOT / "package.json"
    with server.jobs_lock:
        server.jobs[job_id] = server.Job(
            id=job_id,
            status="succeeded",
            progress=100,
            stage="mock complete",
            mode="real-nnunetv2",
            result_path=result_path,
            validation=validation,
            started_at=100.0,
            completed_at=103.4567,
        )
    client = TestClient(server.app)
    state_response = client.get(f"/api/segment/jobs/{job_id}")
    state = state_response.json()
    assert state["status"] == "succeeded"
    assert state["result_ready"] is True
    assert state["started_at"] == 100.0
    assert state["completed_at"] == 103.4567
    assert state["duration_seconds"] == 3.457
    assert state["result_size_bytes"] == result_path.stat().st_size
    assert state["validation"] == validation
    assert state["progress"] == 100
    result_response = client.get(f"/api/segment/jobs/{job_id}/result")
    assert result_response.status_code == 200
    assert result_response.content == result_path.read_bytes()


def test_running_job_can_be_cancelled_and_process_is_terminated():
    server = load_server_module()

    class FakeProcess:
        def __init__(self):
            self.terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

    job_id = "cancel0001"
    process = FakeProcess()
    with server.jobs_lock:
        server.jobs[job_id] = server.Job(
            id=job_id,
            status="running",
            progress=42,
            stage="nnUNetv2 命令运行中",
            process=process,
        )

    client = TestClient(server.app)
    response = client.post(f"/api/segment/jobs/{job_id}/cancel")
    state = response.json()

    assert response.status_code == 200
    assert state["status"] == "cancelling"
    assert state["cancel_requested"] is True
    assert state["progress"] == 42
    assert process.terminated is True
    assert server.jobs[job_id].events[-1]["stage"] == "正在取消本地 nnUNetv2 任务"


def test_running_server_job_cancel_terminates_child_processes():
    server = load_server_module()

    class FakeProcess:
        def __init__(self):
            self.terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

    job_id = "servercancel0001"
    child_processes = [FakeProcess(), FakeProcess(), FakeProcess(), FakeProcess(), FakeProcess()]
    with server.jobs_lock:
        server.jobs[job_id] = server.Job(
            id=job_id,
            status="running",
            progress=35,
            stage="5-fold 并行推理中",
            runtime_target="server",
            child_processes=child_processes,
        )

    client = TestClient(server.app)
    response = client.post(f"/api/segment/jobs/{job_id}/cancel")
    state = response.json()

    assert response.status_code == 200
    assert state["status"] == "cancelling"
    assert state["cancel_requested"] is True
    assert all(child.terminated for child in child_processes)
    assert server.jobs[job_id].events[-1]["stage"] == "正在取消服务器 5-fold 推理任务"


def test_prediction_cache_key_changes_with_runtime_target():
    server = load_server_module()
    base_state = {
        "checkpoint_dataset_name": "Dataset001_AMOS22",
        "checkpoint_configuration": "3d_fullres",
        "labels_source": "checkpoint",
        "inference_options": {
            "profile": "quality",
            "tile_step_size": 0.5,
            "disable_tta": False,
            "not_on_device": False,
        },
    }

    with patch.object(server, "get_checkpoint_sha256", return_value="checkpoint-sha"):
        local_key = server.build_prediction_cache_key("input-sha", {**base_state, "runtime_target": "local"})
        server_key = server.build_prediction_cache_key("input-sha", {**base_state, "runtime_target": "server"})

    assert local_key != server_key


def test_server_complete_event_contains_runtime_validation_timings_and_resource():
    server = load_server_module()
    temp_root = make_test_output_dir("server-complete-event-fields")
    job_id = "serverevent0001"
    input_dir = temp_root / job_id / "input"
    output_dir = temp_root / job_id / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    input_path = input_dir / f"{job_id}_0000.nii.gz"
    input_path.write_bytes(b"server-event-input")
    validation = {"status": "passed", "message": "server complete validation"}

    def fake_server_pipeline(job, _input_dir, output_dir_arg, _case_name):
        server.start_job_phase(job, "server_ensemble")
        server.finish_job_phase(job, "server_ensemble")
        result_path = output_dir_arg / f"{job.id}.nii.gz"
        output_dir_arg.mkdir(parents=True, exist_ok=True)
        result_path.write_bytes(b"server-event-result")
        return result_path, validation, [("soft_ensemble", subprocess.CompletedProcess(args=["ensemble"], returncode=0, stdout="ok", stderr=""))]

    with server.jobs_lock:
        server.jobs[job_id] = server.Job(id=job_id, cache_key="server-event-cache", runtime_target="server")

    with patch.object(server, "WORK_DIR", temp_root), \
         patch.object(server, "run_server_job_pipeline", side_effect=fake_server_pipeline):
        server.run_real_job(job_id, input_path)

    complete_event = server.jobs[job_id].events[-1]
    assert complete_event["type"] == "complete"
    assert complete_event["runtime_target"] == "server"
    assert complete_event["validation"] == validation
    assert complete_event["phase_timings"]["server_ensemble"] >= 0
    assert complete_event["inference_options"] is None
    assert complete_event["resource_latest"]["phase"] == "completed"
    assert complete_event["result_size_bytes"] == len(b"server-event-result")


def test_job_summary_json_records_runtime_and_output_size():
    server = load_server_module()
    output_dir = make_test_output_dir("job-summary")
    result_path = output_dir / "case_seg.nii.gz"
    result_path.write_bytes(b"segmentation")
    job = server.Job(
        id="summary0001",
        status="succeeded",
        progress=100,
        stage="complete",
        mode="real-nnunetv2",
        result_path=result_path,
        validation={"status": "review", "message": "建议人工复核。"},
        log_tail="nnUNetv2 finished",
        started_at=10.0,
        completed_at=70.25,
    )

    summary_path = server.write_job_summary(output_dir, job)
    raw = summary_path.read_bytes()
    parsed = json.loads(raw.decode("utf-8"))

    assert raw[:3] != b"\xef\xbb\xbf"
    assert parsed["job_id"] == "summary0001"
    assert parsed["status"] == "succeeded"
    assert parsed["duration_seconds"] == 60.25
    assert parsed["result_size_bytes"] == len(b"segmentation")
    assert parsed["validation"]["message"] == "建议人工复核。"
    assert parsed["log_tail"] == "nnUNetv2 finished"


def test_job_summary_json_records_resource_snapshots():
    server = load_server_module()
    output_dir = make_test_output_dir("job-resource-summary")
    result_path = output_dir / "case_seg.nii.gz"
    result_path.write_bytes(b"segmentation")
    job = server.Job(
        id="resource0001",
        status="succeeded",
        progress=100,
        stage="complete",
        mode="real-nnunetv2",
        result_path=result_path,
        started_at=10.0,
        completed_at=70.25,
    )
    job.resource_snapshots = [
        {"phase": "started", "timestamp": 10.0, "device": "cuda", "process_pid": 111},
        {"phase": "completed", "timestamp": 70.25, "device": "cuda", "disk_free_bytes": 123456},
    ]

    summary_path = server.write_job_summary(output_dir, job)
    parsed = json.loads(summary_path.read_text(encoding="utf-8"))
    resource_log = output_dir / "resource_snapshots.json"

    assert resource_log.exists()
    assert parsed["resource_latest"]["phase"] == "completed"
    assert parsed["resource_latest"]["disk_free_bytes"] == 123456
    assert parsed["resource_log_path"] == str(resource_log)
    assert json.loads(resource_log.read_text(encoding="utf-8"))[-1]["phase"] == "completed"


def test_create_job_reuses_cached_prediction_for_matching_cache_key():
    server = load_server_module()
    temp_root = make_test_output_dir("cached-jobs")
    cached_job_id = "cached0001"
    cached_output = temp_root / cached_job_id / "output"
    cached_output.mkdir(parents=True, exist_ok=True)
    cached_result = cached_output / f"{cached_job_id}.nii.gz"
    cached_result.write_bytes(b"cached-result")
    validation = {"status": "review", "message": "建议人工复核。"}
    (cached_output / "job_summary.json").write_text(json.dumps({
        "job_id": cached_job_id,
        "status": "succeeded",
        "progress": 100,
        "stage": "历史推理结果已生成",
        "mode": "real-nnunetv2",
        "result_ready": True,
        "result_path": str(cached_result),
        "result_size_bytes": cached_result.stat().st_size,
        "cache_key": "cache-key-1",
        "validation": validation,
    }, ensure_ascii=False), encoding="utf-8")

    def fail_if_started(*_args, **_kwargs):
        raise AssertionError("cached jobs must not start a real inference thread")

    with patch.object(server, "WORK_DIR", temp_root), \
         patch.object(server, "get_model_state", return_value={
             "ready": True,
             "status": "ready",
             "mode": "real-nnunetv2",
             "missing": [],
         }), \
         patch.object(server, "build_prediction_cache_key", return_value="cache-key-1"), \
         patch.object(server.threading, "Thread", side_effect=fail_if_started):
        client = TestClient(server.app)
        response = client.post(
            "/api/segment/jobs",
            files={"file": ("case_0000.nii.gz", b"same-input", "application/octet-stream")},
            data={"model_id": "abdomen"},
        )
        body = response.json()
        state = client.get(f"/api/segment/jobs/{body['job_id']}").json()
        result_response = client.get(f"/api/segment/jobs/{body['job_id']}/result")

    assert response.status_code == 200
    assert body["cached_result"] is True
    assert body["cache_source_job_id"] == cached_job_id
    assert body["mode"] == "cached-real-nnunetv2"
    assert state["status"] == "succeeded"
    assert state["cache_key"] == "cache-key-1"
    assert state["cache_source_job_id"] == cached_job_id
    assert state["validation"] is None
    assert server.jobs[body["job_id"]].events[-1]["cached_result"] is True
    assert server.jobs[body["job_id"]].events[-1]["inference_options"]["profile"] == "quality"
    assert "validation" not in server.jobs[body["job_id"]].events[-1]
    assert result_response.status_code == 200
    assert result_response.content == b"cached-result"


def test_cached_prediction_revalidates_against_current_label_file():
    server = load_server_module()
    temp_root = make_test_output_dir("cached-jobs-current-label")
    cached_job_id = "cached0002"
    cached_output = temp_root / cached_job_id / "output"
    cached_output.mkdir(parents=True, exist_ok=True)
    cached_result = cached_output / f"{cached_job_id}.nii.gz"
    cached_result.write_bytes(b"cached-result")
    stale_validation = {"status": "review", "message": "stale validation"}
    current_validation = {"status": "passed", "message": "current label validation"}
    (cached_output / "job_summary.json").write_text(json.dumps({
        "job_id": cached_job_id,
        "status": "succeeded",
        "progress": 100,
        "stage": "历史推理结果已生成",
        "mode": "real-nnunetv2",
        "result_ready": True,
        "result_path": str(cached_result),
        "result_size_bytes": cached_result.stat().st_size,
        "cache_key": "cache-key-2",
        "validation": stale_validation,
    }, ensure_ascii=False), encoding="utf-8")

    def fail_if_started(*_args, **_kwargs):
        raise AssertionError("cached jobs must not start a real inference thread")

    validated_label_paths: list[Path] = []

    def fake_validate(result_path, label_path, labels, label_taxonomy="auto", dataset_hint=None):
        validated_label_paths.append(label_path)
        assert result_path.name.endswith(".nii.gz")
        assert labels == [{"label": 1, "id": "spleen"}]
        assert label_taxonomy == "auto"
        return current_validation

    with patch.object(server, "WORK_DIR", temp_root), \
         patch.object(server, "get_model_state", return_value={
             "ready": True,
             "status": "ready",
             "mode": "real-nnunetv2",
             "missing": [],
         }), \
         patch.object(server, "build_prediction_cache_key", return_value="cache-key-2"), \
         patch.object(server, "read_labels", return_value=[{"label": 1, "id": "spleen"}]), \
         patch.object(server, "validate_against_custom_label", side_effect=fake_validate), \
         patch.object(server.threading, "Thread", side_effect=fail_if_started):
        client = TestClient(server.app)
        response = client.post(
            "/api/segment/jobs",
            files={
                "file": ("case_0000.nii.gz", b"same-input", "application/octet-stream"),
                "label_file": ("case_label.nii.gz", b"current-label", "application/octet-stream"),
            },
            data={"model_id": "abdomen"},
        )
        body = response.json()
        state = client.get(f"/api/segment/jobs/{body['job_id']}").json()

    assert response.status_code == 200
    assert body["cached_result"] is True
    assert state["validation"] == current_validation
    assert state["validation"] != stale_validation
    assert len(validated_label_paths) == 1
    assert validated_label_paths[0].name == f"{body['job_id']}_label.nii.gz"
    assert server.jobs[body["job_id"]].events[-1]["validation"] == current_validation


def test_cached_prediction_falls_back_to_source_validation_summary():
    server = load_server_module()
    temp_root = make_test_output_dir("cached-jobs-historical-summary")
    cached_job_id = "cached0003"
    cached_output = temp_root / cached_job_id / "output"
    cached_output.mkdir(parents=True, exist_ok=True)
    cached_result = cached_output / f"{cached_job_id}.nii.gz"
    cached_result.write_bytes(b"cached-result")
    historical_validation = {
        "status": "review",
        "sample_id": "flare22_tr_0009",
        "mean_dice": 0.89313,
        "min_dice": 0.67377,
        "foreground_dice": 0.949909,
        "remap_applied": True,
        "remap_source": "FLARE22",
        "message": "（历史离线 remap 摘要，未在当前 job 重新验证）",
    }
    (cached_output / "validation_summary.json").write_text(
        json.dumps(historical_validation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (cached_output / "job_summary.json").write_text(json.dumps({
        "job_id": cached_job_id,
        "status": "succeeded",
        "progress": 100,
        "stage": "历史推理结果已生成",
        "mode": "real-nnunetv2",
        "result_ready": True,
        "result_path": str(cached_result),
        "result_size_bytes": cached_result.stat().st_size,
        "cache_key": "cache-key-3",
        "validation": historical_validation,
    }, ensure_ascii=False), encoding="utf-8")

    def fail_if_started(*_args, **_kwargs):
        raise AssertionError("cached jobs must not start a real inference thread")

    with patch.object(server, "WORK_DIR", temp_root), \
         patch.object(server, "get_model_state", return_value={
             "ready": True,
             "status": "ready",
             "mode": "real-nnunetv2",
             "missing": [],
         }), \
         patch.object(server, "build_prediction_cache_key", return_value="cache-key-3"), \
         patch.object(server.threading, "Thread", side_effect=fail_if_started):
        client = TestClient(server.app)
        response = client.post(
            "/api/segment/jobs",
            files={"file": ("case_0000.nii.gz", b"same-input", "application/octet-stream")},
            data={"model_id": "abdomen"},
        )
        body = response.json()
        state = client.get(f"/api/segment/jobs/{body['job_id']}").json()

    current_output = temp_root / body["job_id"] / "output"
    summary_path = current_output / "validation_summary.json"
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))

    assert response.status_code == 200
    assert body["cached_result"] is True
    assert body["cache_source_job_id"] == cached_job_id
    assert state["validation"] is not None
    assert state["validation"]["historical"] is True
    assert state["validation"]["source_job_id"] == cached_job_id
    assert state["validation"]["mean_dice"] == 0.89313
    assert state["validation"]["min_dice"] == 0.67377
    assert state["validation"]["remap_applied"] is True
    assert state["validation"]["remap_source"] == "FLARE22"
    assert summary_payload["historical"] is True
    assert summary_payload["source_job_id"] == cached_job_id
    assert server.jobs[body["job_id"]].events[-1]["validation"]["historical"] is True


def test_historical_fallback_overrides_with_current_request_taxonomy():
    """cache hit 走 historical fallback 时，validation 里的 label_taxonomy /
    dataset_hint 必须来自当前请求，不能从 cache_source 沿用。否则 FLARE22 cache
    hit 显示 historical 摘要时 HTML 报告会渲染成 AMOS 标签。"""
    server = load_server_module()
    temp_root = make_test_output_dir("cached-jobs-historical-current-taxonomy")
    cached_job_id = "cached0003b"
    cached_output = temp_root / cached_job_id / "output"
    cached_output.mkdir(parents=True, exist_ok=True)
    cached_result = cached_output / f"{cached_job_id}.nii.gz"
    cached_result.write_bytes(b"cached-result")
    historical_validation = {
        "status": "review",
        "sample_id": "flare22_tr_0009",
        "mean_dice": 0.89313,
        "min_dice": 0.67377,
        "foreground_dice": 0.949909,
        "label_taxonomy": "auto",
        "dataset_hint": "AMOS22",
        "remap_applied": True,
        "remap_source": "FLARE22",
        "message": "（历史离线 remap 摘要）",
    }
    (cached_output / "validation_summary.json").write_text(
        json.dumps(historical_validation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (cached_output / "job_summary.json").write_text(json.dumps({
        "job_id": cached_job_id,
        "status": "succeeded",
        "progress": 100,
        "stage": "历史推理结果已生成",
        "mode": "real-nnunetv2",
        "result_ready": True,
        "result_path": str(cached_result),
        "result_size_bytes": cached_result.stat().st_size,
        "cache_key": "cache-key-3b",
        "validation": historical_validation,
    }, ensure_ascii=False), encoding="utf-8")

    def fail_if_started(*_args, **_kwargs):
        raise AssertionError("cached jobs must not start a real inference thread")

    with patch.object(server, "WORK_DIR", temp_root), \
         patch.object(server, "get_model_state", return_value={
             "ready": True,
             "status": "ready",
             "mode": "real-nnunetv2",
             "missing": [],
         }), \
         patch.object(server, "build_prediction_cache_key", return_value="cache-key-3b"), \
         patch.object(server.threading, "Thread", side_effect=fail_if_started):
        client = TestClient(server.app)
        response = client.post(
            "/api/segment/jobs",
            files={"file": ("case_0000.nii.gz", b"same-input", "application/octet-stream")},
            data={
                "model_id": "abdomen",
                "label_taxonomy": "FLARE22",
                "dataset_hint": "FLARE22",
            },
        )
        body = response.json()
        state = client.get(f"/api/segment/jobs/{body['job_id']}").json()

    current_output = temp_root / body["job_id"] / "output"
    summary_path = current_output / "validation_summary.json"
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))

    assert response.status_code == 200
    assert body["cached_result"] is True
    assert body["cache_source_job_id"] == cached_job_id
    # historical / source_job_id 标记必须保留
    assert state["validation"]["historical"] is True
    assert state["validation"]["source_job_id"] == cached_job_id
    # 当前请求的 taxonomy / dataset_hint 必须覆盖 cache_source 的
    assert state["validation"]["label_taxonomy"] == "FLARE22"
    assert state["validation"]["dataset_hint"] == "FLARE22"
    assert summary_payload["label_taxonomy"] == "FLARE22"
    assert summary_payload["dataset_hint"] == "FLARE22"
    # 其余字段（mean_dice / remap_applied）应该从 cache_source 沿用
    assert state["validation"]["mean_dice"] == 0.89313
    assert state["validation"]["remap_applied"] is True
    assert server.jobs[body["job_id"]].events[-1]["validation"]["dataset_hint"] == "FLARE22"


def test_cached_prediction_without_historical_validation_summary():
    server = load_server_module()
    temp_root = make_test_output_dir("cached-jobs-no-historical")
    cached_job_id = "cached0004"
    cached_output = temp_root / cached_job_id / "output"
    cached_output.mkdir(parents=True, exist_ok=True)
    cached_result = cached_output / f"{cached_job_id}.nii.gz"
    cached_result.write_bytes(b"cached-result")
    (cached_output / "job_summary.json").write_text(json.dumps({
        "job_id": cached_job_id,
        "status": "succeeded",
        "progress": 100,
        "stage": "历史推理结果已生成",
        "mode": "real-nnunetv2",
        "result_ready": True,
        "result_path": str(cached_result),
        "result_size_bytes": cached_result.stat().st_size,
        "cache_key": "cache-key-4",
    }, ensure_ascii=False), encoding="utf-8")

    def fail_if_started(*_args, **_kwargs):
        raise AssertionError("cached jobs must not start a real inference thread")

    with patch.object(server, "WORK_DIR", temp_root), \
         patch.object(server, "get_model_state", return_value={
             "ready": True,
             "status": "ready",
             "mode": "real-nnunetv2",
             "missing": [],
         }), \
         patch.object(server, "build_prediction_cache_key", return_value="cache-key-4"), \
         patch.object(server.threading, "Thread", side_effect=fail_if_started):
        client = TestClient(server.app)
        response = client.post(
            "/api/segment/jobs",
            files={"file": ("case_0000.nii.gz", b"same-input", "application/octet-stream")},
            data={"model_id": "abdomen"},
        )
        body = response.json()
        state = client.get(f"/api/segment/jobs/{body['job_id']}").json()

    current_output = temp_root / body["job_id"] / "output"

    assert response.status_code == 200
    assert body["cached_result"] is True
    assert state["validation"] is None
    assert not (current_output / "validation_summary.json").exists()
    last_event = server.jobs[body["job_id"]].events[-1]
    assert last_event.get("validation") is None
    assert "validation" not in last_event


def test_find_cached_prediction_warns_when_no_candidate_has_validation_summary():
    import contextlib
    server = load_server_module()
    temp_root = make_test_output_dir("cached-jobs-degenerate-mtime-sort")
    cache_key = "degenerate-key"
    input_path = temp_root / "current" / "input" / "current_0000.nii.gz"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_bytes(b"current-input")

    for offset, cached_job_id in enumerate(["cached0005a", "cached0005b"]):
      cached_output = temp_root / cached_job_id / "output"
      cached_output.mkdir(parents=True, exist_ok=True)
      cached_result = cached_output / f"{cached_job_id}.nii.gz"
      cached_result.write_bytes(f"cached-result-{offset}".encode("utf-8"))
      (cached_output / "job_summary.json").write_text(json.dumps({
          "job_id": cached_job_id,
          "status": "succeeded",
          "progress": 100,
          "stage": "历史推理结果已生成",
          "mode": "real-nnunetv2",
          "result_ready": True,
          "result_path": str(cached_result),
          "result_size_bytes": cached_result.stat().st_size,
          "cache_key": cache_key,
      }, ensure_ascii=False), encoding="utf-8")
      assert not (cached_output / "validation_summary.json").exists()

    stdout_buffer = io.StringIO()
    with contextlib.redirect_stdout(stdout_buffer), \
         patch.object(server, "WORK_DIR", temp_root):
      cache = server.find_cached_prediction(cache_key, input_path, "current_job_id")
    captured = stdout_buffer.getvalue()

    assert cache is not None
    assert "validation_summary.json" in captured
    assert "mtime-only sort" in captured
    assert cache["job_id"] in {"cached0005a", "cached0005b"}


def test_real_job_uses_persistent_worker_when_enabled():
    server = load_server_module()
    temp_root = make_test_output_dir("persistent-worker-job")
    job_id = "worker0001"
    input_dir = temp_root / job_id / "input"
    output_dir = temp_root / job_id / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    input_path = input_dir / f"{job_id}_0000.nii.gz"
    input_path.write_bytes(b"input")

    def fake_worker(job, input_dir_arg, output_dir_arg, model_dir_arg):
        assert input_dir_arg == input_dir
        assert output_dir_arg == output_dir
        assert model_dir_arg == Path("runtime-model")
        (output_dir_arg / f"{job_id}.nii.gz").write_bytes(b"worker-result")
        return subprocess.CompletedProcess(args=["persistent-worker"], returncode=0, stdout="worker complete", stderr="")

    with server.jobs_lock:
        server.jobs[job_id] = server.Job(id=job_id, cache_key="cache-key")
    with patch.object(server, "WORK_DIR", temp_root), \
         patch.object(server, "prepare_runtime_model_dir", return_value=Path("runtime-model")), \
         patch.object(server, "persistent_worker_enabled", return_value=True), \
         patch.object(server, "run_persistent_worker_prediction", side_effect=fake_worker), \
         patch.object(server, "run_process_with_cancel", side_effect=AssertionError("regular subprocess should not run")), \
         patch.object(server, "is_debug_original_upload", return_value=False):
        server.run_real_job(job_id, input_path)

    state = server.build_job_summary(server.jobs[job_id])
    assert state["status"] == "succeeded"
    assert state["result_ready"] is True
    assert state["phase_timings"]["persistent_worker"] >= 0
    assert state["phase_timings"]["collect_result"] >= 0


def test_persistent_worker_stdout_reader_is_reused_across_events():
    server = load_server_module()
    job = server.Job(id="worker-reader", status="running", progress=20, stage="worker")

    class FakeProcess:
        stdout = io.StringIO(
            '{"type":"complete","message":"first"}\n'
            '{"type":"complete","message":"second"}\n'
        )

    process = FakeProcess()
    first = server._read_worker_event_with_heartbeat(job, process)
    second = server._read_worker_event_with_heartbeat(job, process)

    assert first["message"] == "first"
    assert second["message"] == "second"


def test_process_log_is_persisted_as_utf8_and_tail_is_returned():
    server = load_server_module()
    output_dir = make_test_output_dir("process-log")
    process = subprocess.CompletedProcess(
        args=["nnUNetv2"],
        returncode=1,
        stdout="第一行\n推理进度 90%\n",
        stderr="警告：显存不足\n失败：CUDA out of memory\n",
    )

    log_path, log_tail = server.write_process_log(output_dir, process)
    raw = log_path.read_bytes()
    text = raw.decode("utf-8")

    assert raw[:3] != b"\xef\xbb\xbf"
    assert "STDOUT" in text
    assert "第一行" in text
    assert "失败：CUDA out of memory" in text
    assert log_tail.endswith("失败：CUDA out of memory")


def test_job_state_can_read_persisted_summary_after_restart():
    server = load_server_module()
    temp_root = make_test_output_dir("persisted-jobs")
    job_id = "persisted0001"
    output_dir = temp_root / job_id / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / f"{job_id}.nii.gz"
    result_path.write_bytes(b"persisted-result")
    validation = {
        "status": "review",
        "message": "建议人工复核。",
    }
    (output_dir / "validation_summary.json").write_text(json.dumps(validation, ensure_ascii=False), encoding="utf-8")
    (output_dir / "job_summary.json").write_text(json.dumps({
        "job_id": job_id,
        "status": "succeeded",
        "progress": 100,
        "stage": "历史推理结果已生成",
        "mode": "real-nnunetv2",
        "error": None,
        "started_at": 10.0,
        "completed_at": 20.0,
        "duration_seconds": 10.0,
        "result_ready": True,
        "result_path": str(result_path),
        "result_size_bytes": result_path.stat().st_size,
        "validation": validation,
    }, ensure_ascii=False), encoding="utf-8")

    with patch.object(server, "WORK_DIR", temp_root):
        client = TestClient(server.app)
        response = client.get(f"/api/segment/jobs/{job_id}")
        state = response.json()
        result_response = client.get(f"/api/segment/jobs/{job_id}/result")

    assert response.status_code == 200
    assert state["job_id"] == job_id
    assert state["result_ready"] is True
    assert state["duration_seconds"] == 10.0
    assert state["validation"]["message"] == "建议人工复核。"
    assert result_response.status_code == 200
    assert result_response.content == b"persisted-result"


def test_e2e_inference_flow_create_events_result():
    """端到端推理流程：创建 job → 执行推理 → 验证事件序列 → 下载结果"""
    server = load_server_module()
    temp_root = make_test_output_dir("e2e-inference-flow")
    job_id = "e2e0001"
    input_dir = temp_root / job_id / "input"
    output_dir = temp_root / job_id / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    input_path = input_dir / f"{job_id}_0000.nii.gz"
    input_path.write_bytes(b"fake-nifti-input")

    def fake_worker(job, input_dir_arg, output_dir_arg, model_dir_arg):
        (output_dir_arg / f"{job_id}.nii.gz").write_bytes(b"e2e-segmentation-result")
        return subprocess.CompletedProcess(
            args=["persistent-worker"], returncode=0,
            stdout="worker complete", stderr=""
        )

    with server.jobs_lock:
        server.jobs[job_id] = server.Job(id=job_id, cache_key="e2e-cache-key")

    with patch.object(server, "WORK_DIR", temp_root), \
         patch.object(server, "prepare_runtime_model_dir", return_value=Path("runtime-model")), \
         patch.object(server, "persistent_worker_enabled", return_value=True), \
         patch.object(server, "run_persistent_worker_prediction", side_effect=fake_worker), \
         patch.object(server, "is_debug_original_upload", return_value=False):
        server.run_real_job(job_id, input_path)

    job = server.jobs[job_id]
    summary = server.build_job_summary(job)

    assert summary["status"] == "succeeded"
    assert summary["result_ready"] is True
    assert summary["result_size_bytes"] == len(b"e2e-segmentation-result")
    assert summary["duration_seconds"] is not None and summary["duration_seconds"] >= 0
    assert summary["phase_timings"]["persistent_worker"] >= 0
    assert summary["phase_timings"]["collect_result"] >= 0

    event_types = [e["type"] for e in job.events]
    assert event_types[0] == "progress"
    assert event_types[-1] == "complete"
    assert "error" not in event_types

    progress_stages = [e["stage"] for e in job.events if e["type"] == "progress"]
    assert any("nnUNetv2" in s for s in progress_stages)
    assert any("推理" in s for s in progress_stages)

    complete_event = job.events[-1]
    assert complete_event["progress"] == 100
    assert complete_event["duration_seconds"] is not None
    assert complete_event["result_size_bytes"] == len(b"e2e-segmentation-result")
    assert "resource_latest" in complete_event


def test_e2e_inference_flow_via_api_endpoints():
    """通过 TestClient 走完整 API 链路：POST 创建 → GET 状态 → GET 结果"""
    server = load_server_module()
    temp_root = make_test_output_dir("e2e-api-flow")
    cached_job_id = "e2e-api-0001"
    cached_output = temp_root / cached_job_id / "output"
    cached_output.mkdir(parents=True, exist_ok=True)
    cached_result = cached_output / f"{cached_job_id}.nii.gz"
    cached_result.write_bytes(b"e2e-api-result")
    (cached_output / "job_summary.json").write_text(json.dumps({
        "job_id": cached_job_id,
        "status": "succeeded",
        "progress": 100,
        "stage": "历史推理结果已生成",
        "mode": "real-nnunetv2",
        "result_ready": True,
        "result_path": str(cached_result),
        "result_size_bytes": cached_result.stat().st_size,
        "cache_key": "e2e-api-cache-key",
        "validation": {"status": "passed", "message": "达标"},
    }, ensure_ascii=False), encoding="utf-8")

    with patch.object(server, "WORK_DIR", temp_root), \
         patch.object(server, "get_model_state", return_value={
             "ready": True, "status": "ready", "mode": "real-nnunetv2", "missing": [],
         }), \
         patch.object(server, "build_prediction_cache_key", return_value="e2e-api-cache-key"):
        client = TestClient(server.app)
        create_response = client.post(
            "/api/segment/jobs",
            files={"file": ("case_0000.nii.gz", b"e2e-input", "application/octet-stream")},
            data={"model_id": "abdomen"},
        )
        body = create_response.json()
        job_id = body["job_id"]

        state_response = client.get(f"/api/segment/jobs/{job_id}")
        state = state_response.json()

        result_response = client.get(f"/api/segment/jobs/{job_id}/result")

    assert create_response.status_code == 200
    assert body["cached_result"] is True
    assert body["mode"] == "cached-real-nnunetv2"

    assert state_response.status_code == 200
    assert state["status"] == "succeeded"
    assert state["result_ready"] is True
    assert state["validation"] is None

    assert result_response.status_code == 200
    assert result_response.content == b"e2e-api-result"

    job = server.jobs[job_id]
    event_types = [e["type"] for e in job.events]
    assert event_types[-1] == "complete"
    assert job.events[-1]["cached_result"] is True


def test_server_fold_ensemble_and_evaluate_commands_match_5gpu_script():
    server = load_server_module()

    config = server.get_server_inference_config({
        "SEGMENTATION_SERVER_GPUS": "0,1,2,3,4",
        "SEGMENTATION_SERVER_FOLDS": "0,1,2,3,4",
        "SEGMENTATION_SERVER_DATASET_ID": "1",
        "SEGMENTATION_SERVER_CONFIG": "3d_fullres",
        "SEGMENTATION_SERVER_PLANS": "nnUNetResEncUNetXLPlans",
        "SEGMENTATION_SERVER_NNUNET_RAW": "/mnt/data0/LUO_Zheng/nnUNet_raw",
        "SEGMENTATION_SERVER_NNUNET_PREPROCESSED": "/mnt/data0/LUO_Zheng/nnUNet_preprocessed",
        "SEGMENTATION_SERVER_NNUNET_RESULTS": "/mnt/data0/LUO_Zheng/nnUNet_results",
        "SEGMENTATION_SERVER_OUTPUT_ROOT": "/mnt/data0/LUO_Zheng/result/gui_jobs",
        "SEGMENTATION_SERVER_EVALUATE_SCRIPT": "/mnt/data0/LUO_Zheng/evaluate_full.py",
        "SEGMENTATION_SERVER_LABELS_DIR": "/mnt/data0/LUO_Zheng/amos22/amos22/labelsVa",
        "SEGMENTATION_SERVER_DATASET_JSON": "/mnt/data0/LUO_Zheng/nnUNet_results/Dataset001_AMOS22/nnUNetTrainer__nnUNetResEncUNetXLPlans__3d_fullres/dataset.json",
        "SEGMENTATION_SERVER_PREPROCESS_WORKERS": "4",
        "SEGMENTATION_SERVER_ENSEMBLE_PROCESSES": "8",
    })

    input_dir = Path("/mnt/data0/LUO_Zheng/gui_jobs/job001/input")
    output_prefix = Path("/mnt/data0/LUO_Zheng/result/gui_jobs/job001/job001")
    fold_commands = server.build_server_fold_commands(config, input_dir, output_prefix)

    assert [(item.fold, item.gpu) for item in fold_commands] == [
        ("0", "0"),
        ("1", "1"),
        ("2", "2"),
        ("3", "3"),
        ("4", "4"),
    ]
    assert fold_commands[0].command == [
        "nnUNetv2_predict",
        "-d", "1",
        "-c", "3d_fullres",
        "-p", "nnUNetResEncUNetXLPlans",
        "-i", str(input_dir),
        "-o", str(output_prefix) + "_f0",
        "-f", "0",
        "-npp", "4",
        "--save_probabilities",
    ]
    assert fold_commands[0].env["CUDA_VISIBLE_DEVICES"] == "0"
    assert fold_commands[4].env["CUDA_VISIBLE_DEVICES"] == "4"
    assert fold_commands[4].output_dir == Path(str(output_prefix) + "_f4")

    ensemble_dir = Path("/mnt/data0/LUO_Zheng/result/gui_jobs/job001/ensemble")
    ensemble_command = server.build_server_ensemble_command(config, [item.output_dir for item in fold_commands], ensemble_dir)
    assert ensemble_command == [
        "nnUNetv2_ensemble",
        "-i",
        str(output_prefix) + "_f0",
        str(output_prefix) + "_f1",
        str(output_prefix) + "_f2",
        str(output_prefix) + "_f3",
        str(output_prefix) + "_f4",
        "-o", str(ensemble_dir),
        "-np", "8",
    ]

    evaluate_command = server.build_server_evaluate_command(config, ensemble_dir)
    assert evaluate_command == [
        "python",
        "/mnt/data0/LUO_Zheng/evaluate_full.py",
        str(ensemble_dir),
        "/mnt/data0/LUO_Zheng/amos22/amos22/labelsVa",
        "--dataset_json",
        "/mnt/data0/LUO_Zheng/nnUNet_results/Dataset001_AMOS22/nnUNetTrainer__nnUNetResEncUNetXLPlans__3d_fullres/dataset.json",
        "--np", "8",
    ]


def test_server_runtime_job_uses_server_pipeline_and_records_complete_event():
    server = load_server_module()
    temp_root = make_test_output_dir("server-runtime-job")
    job_id = "serverjob0001"
    input_dir = temp_root / job_id / "input"
    output_dir = temp_root / job_id / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    input_path = input_dir / f"{job_id}_0000.nii.gz"
    input_path.write_bytes(b"server-input")
    server_result = output_dir / f"{job_id}.nii.gz"
    validation = {"status": "passed", "message": "server validation"}

    def fake_server_pipeline(job, input_dir_arg, output_dir_arg, case_name_arg):
        assert job.runtime_target == "server"
        assert input_dir_arg == input_dir
        assert output_dir_arg == output_dir
        assert case_name_arg == job_id
        output_dir_arg.mkdir(parents=True, exist_ok=True)
        server_result.write_bytes(b"server-result")
        server.start_job_phase(job, "server_fold_predict")
        server.finish_job_phase(job, "server_fold_predict")
        return server_result, validation, [
            ("fold_0_gpu_0", subprocess.CompletedProcess(args=["fold0"], returncode=0, stdout="fold done", stderr="")),
            ("soft_ensemble", subprocess.CompletedProcess(args=["ensemble"], returncode=0, stdout="ensemble done", stderr="")),
        ]

    with server.jobs_lock:
        server.jobs[job_id] = server.Job(id=job_id, cache_key="server-cache", runtime_target="server")

    with patch.object(server, "WORK_DIR", temp_root), \
         patch.object(server, "run_server_job_pipeline", side_effect=fake_server_pipeline), \
         patch.object(server, "run_local_job_pipeline", side_effect=AssertionError("server runtime must not use local pipeline")):
        server.run_real_job(job_id, input_path)

    job = server.jobs[job_id]
    summary = server.build_job_summary(job)
    complete_event = job.events[-1]

    assert summary["status"] == "succeeded"
    assert summary["runtime_target"] == "server"
    assert summary["result_ready"] is True
    assert summary["validation"] == validation
    assert summary["phase_timings"]["server_fold_predict"] >= 0
    assert complete_event["type"] == "complete"
    assert complete_event["stage"] == "服务器 5-fold soft ensemble 推理结果已生成"
    assert complete_event["runtime_target"] == "server"
    assert complete_event["validation"] == validation
    assert complete_event["result_size_bytes"] == len(b"server-result")


def test_create_server_runtime_job_via_api_records_runtime_and_result():
    server = load_server_module()
    temp_root = make_test_output_dir("server-runtime-api-job")
    validation = {"status": "passed", "message": "server api validation"}

    class ImmediateThread:
        def __init__(self, target, args=(), kwargs=None, **_unused):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}

        def start(self):
            self.target(*self.args, **self.kwargs)

    def fake_server_pipeline(job, input_dir_arg, output_dir_arg, case_name_arg):
        assert job.runtime_target == "server"
        result_path = output_dir_arg / f"{job.id}.nii.gz"
        output_dir_arg.mkdir(parents=True, exist_ok=True)
        result_path.write_bytes(b"server-api-result")
        return result_path, validation, [
            ("fold_0_gpu_0", subprocess.CompletedProcess(args=["fold0"], returncode=0, stdout="fold done", stderr="")),
            ("soft_ensemble", subprocess.CompletedProcess(args=["ensemble"], returncode=0, stdout="ensemble done", stderr="")),
        ]

    model_state = {
        "ready": True,
        "status": "ready",
        "mode": "real-nnunetv2",
        "runtime_target": "server",
        "missing": [],
        "model_file_ending": ".nii.gz",
        "confidence_threshold_effective": False,
        "checkpoint_dataset_name": "Dataset001_AMOS22",
        "checkpoint_configuration": "3d_fullres",
        "labels_source": "checkpoint",
        "inference_options": {"profile": "quality", "tile_step_size": 0.5, "disable_tta": False, "not_on_device": False},
        "server_inference": {},
    }

    with patch.object(server, "WORK_DIR", temp_root), \
         patch.object(server, "get_model_state", return_value=model_state), \
         patch.object(server, "get_checkpoint_sha256", return_value="checkpoint-sha"), \
         patch.object(server, "find_cached_prediction", return_value=None), \
         patch.object(server, "run_server_job_pipeline", side_effect=fake_server_pipeline), \
         patch.object(server, "run_local_job_pipeline", side_effect=AssertionError("server runtime must not use local pipeline")), \
         patch.object(server.threading, "Thread", ImmediateThread):
        client = TestClient(server.app)
        create_response = client.post(
            "/api/segment/jobs",
            files={"file": ("case_0000.nii.gz", b"server-api-input", "application/octet-stream")},
            data={"model_id": "abdomen", "runtime_target": "server", "inference_profile": "quality"},
        )
        body = create_response.json()
        state = client.get(f"/api/segment/jobs/{body['job_id']}").json()
        result_response = client.get(f"/api/segment/jobs/{body['job_id']}/result")

    assert create_response.status_code == 200
    assert body["runtime_target"] == "server"
    assert body["cached_result"] is False
    assert state["status"] == "succeeded"
    assert state["runtime_target"] == "server"
    assert state["validation"] == validation
    assert result_response.status_code == 200
    assert result_response.content == b"server-api-result"


def test_e2e_inference_failure_flow():
    """端到端失败流程：推理抛异常 → job 状态变为 failed → 错误事件记录"""
    server = load_server_module()
    temp_root = make_test_output_dir("e2e-failure-flow")
    job_id = "e2e-fail-0001"
    input_dir = temp_root / job_id / "input"
    output_dir = temp_root / job_id / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    input_path = input_dir / f"{job_id}_0000.nii.gz"
    input_path.write_bytes(b"fake-input")

    def failing_worker(job, input_dir_arg, output_dir_arg, model_dir_arg):
        raise RuntimeError("CUDA out of memory")

    with server.jobs_lock:
        server.jobs[job_id] = server.Job(id=job_id, cache_key="fail-cache")

    with patch.object(server, "WORK_DIR", temp_root), \
         patch.object(server, "prepare_runtime_model_dir", return_value=Path("runtime-model")), \
         patch.object(server, "persistent_worker_enabled", return_value=True), \
         patch.object(server, "run_persistent_worker_prediction", side_effect=failing_worker), \
         patch.object(server, "is_debug_original_upload", return_value=False):
        server.run_real_job(job_id, input_path)

    job = server.jobs[job_id]
    assert job.status == "failed"
    assert "CUDA out of memory" in job.error

    event_types = [e["type"] for e in job.events]
    assert event_types[0] == "progress"
    assert event_types[-1] == "error"

    error_event = job.events[-1]
    assert "CUDA out of memory" in error_event["message"]


def test_push_heartbeat_emits_progress_event_with_heartbeat_flag():
    server = load_server_module()

    job = server.Job(id="heartbeat0001", status="running", progress=20, stage="常驻 nnUNetv2 worker 推理中")
    job.started_at = server.time.time() - 30.0

    server.push_heartbeat(job, "test_phase")

    assert len(job.events) == 1
    event = job.events[0]
    assert event["type"] == "progress"
    assert event["progress"] == 20
    assert event["stage"] == "常驻 nnUNetv2 worker 推理中"
    assert event["heartbeat"] is True
    assert isinstance(event["elapsed_seconds"], (int, float))
    assert 25.0 <= event["elapsed_seconds"] <= 35.0
    assert "resource_latest" in event


def test_push_heartbeat_failure_does_not_raise():
    server = load_server_module()

    job = server.Job(id="heartbeat0002", status="running", progress=20, stage="test")
    job.started_at = None

    server.push_heartbeat(job, "test_phase")
    assert len(job.events) == 1
    assert job.events[0]["heartbeat"] is True
    assert job.events[0]["elapsed_seconds"] is None


def test_job_state_can_reconstruct_legacy_output_without_summary():
    server = load_server_module()
    temp_root = make_test_output_dir("legacy-jobs")
    job_id = "legacy0001"
    input_dir = temp_root / job_id / "input"
    output_dir = temp_root / job_id / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    input_path = input_dir / f"{job_id}_0000.nii.gz"
    result_path = output_dir / f"{job_id}.nii.gz"
    input_path.write_bytes(b"legacy-input")
    result_path.write_bytes(b"legacy-result")
    validation = {"status": "review", "message": "建议人工复核。"}
    (output_dir / "validation_summary.json").write_text(json.dumps(validation, ensure_ascii=False), encoding="utf-8")

    with patch.object(server, "WORK_DIR", temp_root):
        client = TestClient(server.app)
        response = client.get(f"/api/segment/jobs/{job_id}")
        state = response.json()
        result_response = client.get(f"/api/segment/jobs/{job_id}/result")

    assert response.status_code == 200
    assert state["job_id"] == job_id
    assert state["status"] == "succeeded"
    assert state["result_ready"] is True
    assert state["result_size_bytes"] == len(b"legacy-result")
    assert state["validation"]["message"] == "建议人工复核。"
    assert result_response.status_code == 200
    assert result_response.content == b"legacy-result"


def test_validate_against_custom_label_respects_explicit_taxonomy_hints():
    server = load_server_module()
    import nibabel as nib
    import numpy as np

    temp_root = make_test_output_dir("explicit-taxonomy-validation")
    prediction_path = temp_root / "prediction.nii.gz"
    reference_path = temp_root / "reference.nii.gz"
    prediction = np.array([[0, 1], [0, 2]], dtype=np.int16)
    reference = np.array([[0, 1], [0, 2]], dtype=np.int16)
    affine = np.eye(4)
    nib.save(nib.Nifti1Image(prediction, affine), prediction_path)
    nib.save(nib.Nifti1Image(reference, affine), reference_path)
    labels = [
        {"label": 1, "id": "spleen", "nameEn": "spleen"},
        {"label": 2, "id": "right_kidney", "nameEn": "right_kidney"},
        {"label": 6, "id": "liver", "nameEn": "liver"},
    ]

    amos_validation = server.validate_against_custom_label(prediction_path, reference_path, labels, label_taxonomy="AMOS22")
    flare_validation = server.validate_against_custom_label(prediction_path, reference_path, labels, label_taxonomy="FLARE22")

    assert amos_validation["label_taxonomy"] == "AMOS22"
    assert amos_validation["remap_applied"] is False
    assert amos_validation["taxonomy_match"] is True
    assert flare_validation["label_taxonomy"] == "FLARE22"
    assert flare_validation["remap_applied"] is True
    assert flare_validation["remap_source"] == "FLARE22"


def test_taxonomy_detects_flare22_and_remaps_label_ids():
    """taxonomy 模块能检测 FLARE22 标签并生成正确的 ID 重映射"""
    import sys
    taxonomy_path = PROJECT_ROOT / "server" / "taxonomy.py"
    spec = importlib.util.spec_from_file_location("taxonomy", taxonomy_path)
    taxonomy = importlib.util.module_from_spec(spec)
    sys.modules["taxonomy"] = taxonomy
    spec.loader.exec_module(taxonomy)

    # AMOS22 checkpoint labels (from dataset.json)
    amos_labels = [
        {"label": 1, "id": "spleen", "nameEn": "spleen", "nameZh": "脾脏"},
        {"label": 2, "id": "right-kidney", "nameEn": "right_kidney", "nameZh": "右肾"},
        {"label": 3, "id": "left-kidney", "nameEn": "left_kidney", "nameZh": "左肾"},
        {"label": 4, "id": "gallbladder", "nameEn": "gall_bladder", "nameZh": "胆囊"},
        {"label": 5, "id": "esophagus", "nameEn": "esophagus", "nameZh": "食管"},
        {"label": 6, "id": "liver", "nameEn": "liver", "nameZh": "肝脏"},
        {"label": 7, "id": "stomach", "nameEn": "stomach", "nameZh": "胃"},
        {"label": 8, "id": "aorta", "nameEn": "aorta", "nameZh": "主动脉"},
        {"label": 9, "id": "ivc", "nameEn": "postcava", "nameZh": "下腔静脉"},
        {"label": 10, "id": "pancreas", "nameEn": "pancreas", "nameZh": "胰腺"},
        {"label": 11, "id": "right-adrenal-gland", "nameEn": "right_adrenal_gland", "nameZh": "右肾上腺"},
        {"label": 12, "id": "left-adrenal-gland", "nameEn": "left_adrenal_gland", "nameZh": "左肾上腺"},
        {"label": 13, "id": "duodenum", "nameEn": "duodenum", "nameZh": "十二指肠"},
        {"label": 14, "id": "bladder", "nameEn": "bladder", "nameZh": "膀胱"},
        {"label": 15, "id": "prostate-or-uterus", "nameEn": "prostate_or_uterus", "nameZh": "前列腺/子宫"},
    ]

    # FLARE22 reference has IDs {1..13}, all of which fall inside the AMOS
    # checkpoint's {1..15}. With the new coverage guard, auto-detect returns
    # None because the reference covers 13/15 of the checkpoint labels. The
    # frontend is expected to set the taxonomy explicitly when a reference
    # case declares its dataset.
    flare22_ids = set(range(1, 14))

    detected = taxonomy.detect_dataset(flare22_ids, amos_labels)
    assert detected is None, f"Expected auto-detect to be conservative, got {detected}"

    # Explicit FLARE22 selection should work
    mapping = taxonomy.build_remap_mapping(amos_labels, "FLARE22")
    # FLARE22 ID 1 (liver) → AMOS22 ID 6 (liver)
    assert mapping[1] == 6, f"FLARE22 liver(1) should map to AMOS22 liver(6), got {mapping.get(1)}"
    # FLARE22 ID 3 (spleen) → AMOS22 ID 1 (spleen)
    assert mapping[3] == 1, f"FLARE22 spleen(3) should map to AMOS22 spleen(1), got {mapping.get(3)}"
    # FLARE22 ID 2 (right_kidney) → same ID, should NOT be in mapping
    assert 2 not in mapping, "right_kidney has same ID in both datasets, should not be remapped"

    # Should apply remap correctly
    import numpy as np
    reference = np.array([0, 1, 2, 3, 13], dtype=np.int32)
    remapped = taxonomy.apply_remap(reference, mapping)
    assert remapped[1] == 6, f"Label 1 should become 6 (liver), got {remapped[1]}"
    assert remapped[2] == 2, f"Label 2 should stay 2 (right_kidney), got {remapped[2]}"
    assert remapped[3] == 1, f"Label 3 should become 1 (spleen), got {remapped[3]}"
    assert remapped[4] == 3, f"Label 13 should become 3 (left_kidney), got {remapped[4]}"


def test_taxonomy_detects_partial_flare22_labels_when_ids_are_mismatched():
    """共享 ID 不足时不做自动检测，需显式选择数据集。"""
    import sys
    taxonomy_path = PROJECT_ROOT / "server" / "taxonomy.py"
    spec = importlib.util.spec_from_file_location("taxonomy", taxonomy_path)
    taxonomy = importlib.util.module_from_spec(spec)
    sys.modules["taxonomy"] = taxonomy
    spec.loader.exec_module(taxonomy)

    amos_labels = [
        {"label": 1, "id": "spleen", "nameEn": "spleen", "nameZh": "脾脏"},
        {"label": 3, "id": "left-kidney", "nameEn": "left_kidney", "nameZh": "左肾"},
        {"label": 6, "id": "liver", "nameEn": "liver", "nameZh": "肝脏"},
    ]

    # 共享 ID 只有 2 个，未达到最低 3 个的证据门槛，避免把偶然重叠误判为 FLARE22
    detected = taxonomy.detect_dataset({1, 3}, amos_labels)
    assert detected is None, f"Expected None when shared IDs < 3, got {detected}"

    # Explicit FLARE22 selection should work
    mapping = taxonomy.build_remap_mapping(amos_labels, "FLARE22")
    assert mapping[1] == 6
    assert mapping[3] == 1


def test_taxonomy_returns_none_for_amos_native_labels():
    """当 reference 标签与 checkpoint 相同时，不做 remap"""
    import sys
    taxonomy_path = PROJECT_ROOT / "server" / "taxonomy.py"
    spec = importlib.util.spec_from_file_location("taxonomy", taxonomy_path)
    taxonomy = importlib.util.module_from_spec(spec)
    sys.modules["taxonomy"] = taxonomy
    spec.loader.exec_module(taxonomy)

    amos_labels = [
        {"label": 1, "id": "spleen", "nameEn": "spleen", "nameZh": "脾脏"},
        {"label": 2, "id": "right-kidney", "nameEn": "right_kidney", "nameZh": "右肾"},
    ]

    # AMOS native reference has same IDs
    amos_ids = {1, 2}
    detected = taxonomy.detect_dataset(amos_ids, amos_labels)
    assert detected is None, f"Should not detect any dataset for AMOS-native labels, got {detected}"


def test_taxonomy_returns_none_when_amos_reference_matches_full_amos_checkpoint():
    """AMOS 1-15 对 AMOS ckpt 1-15：共享 ID 全 match，绝不能被错判成 FLARE22。"""
    import sys
    taxonomy_path = PROJECT_ROOT / "server" / "taxonomy.py"
    spec = importlib.util.spec_from_file_location("taxonomy", taxonomy_path)
    taxonomy = importlib.util.module_from_spec(spec)
    sys.modules["taxonomy"] = taxonomy
    spec.loader.exec_module(taxonomy)

    amos_labels = [
        {"label": 1, "id": "spleen", "nameEn": "spleen", "nameZh": "脾脏"},
        {"label": 2, "id": "right-kidney", "nameEn": "right_kidney", "nameZh": "右肾"},
        {"label": 3, "id": "left-kidney", "nameEn": "left_kidney", "nameZh": "左肾"},
        {"label": 4, "id": "gallbladder", "nameEn": "gall_bladder", "nameZh": "胆囊"},
        {"label": 5, "id": "esophagus", "nameEn": "esophagus", "nameZh": "食管"},
        {"label": 6, "id": "liver", "nameEn": "liver", "nameZh": "肝脏"},
        {"label": 7, "id": "stomach", "nameEn": "stomach", "nameZh": "胃"},
        {"label": 8, "id": "aorta", "nameEn": "aorta", "nameZh": "主动脉"},
        {"label": 9, "id": "ivc", "nameEn": "postcava", "nameZh": "下腔静脉"},
        {"label": 10, "id": "pancreas", "nameEn": "pancreas", "nameZh": "胰腺"},
        {"label": 11, "id": "right-adrenal-gland", "nameEn": "right_adrenal_gland", "nameZh": "右肾上腺"},
        {"label": 12, "id": "left-adrenal-gland", "nameEn": "left_adrenal_gland", "nameZh": "左肾上腺"},
        {"label": 13, "id": "duodenum", "nameEn": "duodenum", "nameZh": "十二指肠"},
        {"label": 14, "id": "bladder", "nameEn": "bladder", "nameZh": "膀胱"},
        {"label": 15, "id": "prostate-or-uterus", "nameEn": "prostate_or_uterus", "nameZh": "前列腺/子宫"},
    ]
    detected = taxonomy.detect_dataset(set(range(1, 16)), amos_labels)
    assert detected is None, f"AMOS-vs-AMOS should not be detected, got {detected}"


def test_taxonomy_returns_none_for_realistic_amos_1_to_13_reference():
    """真实 AMOS label 只有 1-13（无 bladder/prostate）vs ckpt 1-15：
    不能因为 FLARE22 表错位而被错判 FLARE22。
    """
    import sys
    taxonomy_path = PROJECT_ROOT / "server" / "taxonomy.py"
    spec = importlib.util.spec_from_file_location("taxonomy", taxonomy_path)
    taxonomy = importlib.util.module_from_spec(spec)
    sys.modules["taxonomy"] = taxonomy
    spec.loader.exec_module(taxonomy)

    amos_labels = [
        {"label": i, "id": f"organ_{i}", "nameEn": f"organ_{i}", "nameZh": f"器官{i}"}
        for i in range(1, 16)
    ]
    detected = taxonomy.detect_dataset(set(range(1, 14)), amos_labels)
    assert detected is None, f"Realistic AMOS 1-13 should not be detected, got {detected}"


def test_validate_against_custom_label_uses_dataset_hint_when_taxonomy_is_auto():
    """auto + dataset_hint=FLARE22 应触发 remap（即使 detect_dataset 返回 None）"""
    import sys
    import nibabel as nib
    import numpy as np
    from pathlib import Path
    import tempfile

    server = load_server_module()
    tmp = Path(tempfile.mkdtemp(prefix="seg-dataset-hint-"))
    try:
        # 1-13 范围内的 FLARE22 风格标签，1=liver, 3=spleen
        flare_label = np.zeros((4, 4, 4), dtype=np.int16)
        flare_label[0:1, 0:2, 0:2] = 1  # FLARE22 liver
        flare_label[1:2, 0:2, 0:2] = 3  # FLARE22 spleen
        # AMOS22 ckpt 视角下：ID 1=spleen, ID 6=liver, ID 3=left_kidney
        # 不 remap 时 FLARE22 liver(1) 撞 ckpt spleen(1) → 错配
        # remap 后 FLARE22 liver(1) → AMOS22 liver(6) → 与 prediction[6] 对比
        amos_labels = [
            {"label": 1, "id": "spleen", "nameEn": "spleen", "nameZh": "脾脏"},
            {"label": 2, "id": "right_kidney", "nameEn": "right_kidney", "nameZh": "右肾"},
            {"label": 3, "id": "left_kidney", "nameEn": "left_kidney", "nameZh": "左肾"},
            {"label": 6, "id": "liver", "nameEn": "liver", "nameZh": "肝脏"},
        ]
        # prediction: AMOS 视角下，spleen 在 1，liver 在 6
        prediction = np.zeros((4, 4, 4), dtype=np.int16)
        prediction[0:1, 0:2, 0:2] = 6  # ckpt 把这里预测为 liver
        prediction[1:2, 0:2, 0:2] = 1  # ckpt 把这里预测为 spleen
        label_path = tmp / "label.nii.gz"
        pred_path = tmp / "pred.nii.gz"
        nib.save(nib.Nifti1Image(flare_label, np.eye(4)), str(label_path))
        nib.save(nib.Nifti1Image(prediction, np.eye(4)), str(pred_path))

        # auto + dataset_hint=FLARE22 → 应 remap
        result = server.validate_against_custom_label(
            pred_path, label_path, amos_labels, label_taxonomy="auto", dataset_hint="FLARE22"
        )
        assert result.get("remap_applied") is True, f"Expected remap with FLARE22 hint, got {result}"
        assert result.get("remap_source") == "FLARE22"
        assert "已按参考病例" in (result.get("message") or "")
        # remap 后 dice 应该高（liver 通道对 liver 通道、spleen 通道对 spleen 通道）
        assert result.get("mean_dice", 0) > 0.5, f"Expected high dice after remap, got {result.get('mean_dice')}"

        # auto + dataset_hint=AMOS22 → 不 remap，dice 应该低（错位）
        result = server.validate_against_custom_label(
            pred_path, label_path, amos_labels, label_taxonomy="auto", dataset_hint="AMOS22"
        )
        assert result.get("remap_applied") is not True, f"AMOS22 hint should not remap, got {result}"
        # 不 remap 时 FLARE22 liver(1) vs AMOS prediction[1]=spleen → dice=0
        assert result.get("mean_dice", 1) < 0.5, f"Expected low dice without remap, got {result.get('mean_dice')}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_validate_against_debug_label_propagates_taxonomy_hint():
    """validate_against_debug_label 必须接受 label_taxonomy / dataset_hint 并写
    taxonomy_match / label_taxonomy / remap_applied 字段，否则 cache demo Phase A
    走 debug label 路径时 HTML 报告 banner 缺失。"""
    import nibabel as nib
    import numpy as np
    import tempfile

    server = load_server_module()
    tmp = Path(tempfile.mkdtemp(prefix="seg-debug-taxonomy-"))
    try:
        amos_labels = [
            {"label": 1, "id": "spleen", "nameEn": "spleen", "nameZh": "脾脏"},
            {"label": 2, "id": "right_kidney", "nameEn": "right_kidney", "nameZh": "右肾"},
            {"label": 3, "id": "left_kidney", "nameEn": "left_kidney", "nameZh": "左肾"},
            {"label": 6, "id": "liver", "nameEn": "liver", "nameZh": "肝脏"},
        ]
        # FLARE22 视角下的 reference：1=liver, 3=spleen
        flare_label = np.zeros((4, 4, 4), dtype=np.int16)
        flare_label[0:1, 0:2, 0:2] = 1
        flare_label[1:2, 0:2, 0:2] = 3
        # AMOS 视角下的 prediction：6=liver, 1=spleen
        prediction = np.zeros((4, 4, 4), dtype=np.int16)
        prediction[0:1, 0:2, 0:2] = 6
        prediction[1:2, 0:2, 0:2] = 1

        label_path = tmp / "debug_label.nii.gz"
        pred_path = tmp / "pred.nii.gz"
        nib.save(nib.Nifti1Image(flare_label, np.eye(4)), str(label_path))
        nib.save(nib.Nifti1Image(prediction, np.eye(4)), str(pred_path))

        with patch.object(server, "DEBUG_LABEL", label_path), \
             patch.object(server, "read_labels", return_value=amos_labels), \
             patch.object(server, "FALLBACK_LABEL", label_path):
            # 1) label_taxonomy=FLARE22 必须触发 remap
            result_flare = server.validate_against_debug_label(
                pred_path, label_taxonomy="FLARE22"
            )
            assert result_flare.get("remap_applied") is True, \
                f"Expected remap when taxonomy=FLARE22, got {result_flare}"
            assert result_flare.get("remap_source") == "FLARE22"
            assert result_flare.get("label_taxonomy") == "FLARE22"
            assert result_flare.get("taxonomy_match") is True
            assert "已按用户选择" in (result_flare.get("message") or "")

            # 2) label_taxonomy=AMOS22 + AMOS-style reference 不 remap
            amos_label = np.zeros((4, 4, 4), dtype=np.int16)
            amos_label[0:1, 0:2, 0:2] = 6
            amos_label[1:2, 0:2, 0:2] = 1
            amos_label_path = tmp / "debug_label_amos.nii.gz"
            nib.save(nib.Nifti1Image(amos_label, np.eye(4)), str(amos_label_path))
            with patch.object(server, "DEBUG_LABEL", amos_label_path):
                result_amos = server.validate_against_debug_label(
                    pred_path, label_taxonomy="AMOS22"
                )
            assert result_amos.get("remap_applied") is False, \
                f"AMOS22 hint on AMOS-style label should not remap, got {result_amos}"
            assert result_amos.get("label_taxonomy") == "AMOS22"
            assert result_amos.get("taxonomy_match") is True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_taxonomy_detects_flare22_and_remaps_label_ids()
    test_taxonomy_detects_partial_flare22_labels_when_ids_are_mismatched()
    test_taxonomy_returns_none_for_amos_native_labels()
    test_taxonomy_returns_none_when_amos_reference_matches_full_amos_checkpoint()
    test_taxonomy_returns_none_for_realistic_amos_1_to_13_reference()
    test_validate_against_custom_label_uses_dataset_hint_when_taxonomy_is_auto()
    test_validate_against_debug_label_propagates_taxonomy_hint()
    test_validate_against_custom_label_respects_explicit_taxonomy_hints()
    test_model_state_reports_missing_required_files()
    test_server_runtime_ready_does_not_require_local_model_files()
    test_server_runtime_reports_missing_server_paths()
    test_local_runtime_does_not_check_server_paths()
    test_create_job_rejects_when_model_is_not_ready()
    test_server_source_does_not_log_uploaded_filenames()
    test_predict_command_uses_model_folder_and_job_io()
    test_predict_worker_counts_have_safe_defaults_and_clamps()
    test_fast_inference_profile_controls_nnunet_prediction_flags()
    test_create_job_uses_requested_inference_profile_for_options_and_cache_key()
    test_create_job_normalizes_nii_upload_to_model_file_ending()
    test_prediction_cache_key_changes_with_inference_options()
    test_legacy_reference_cache_requires_matching_summary_cache_key()
    test_persistent_worker_key_includes_inference_options()
    test_same_file_content_uses_samefile_fast_path()
    test_job_phase_timings_are_recorded()
    test_project_checkpoint_is_preferred_as_weight_source()
    test_dataset_labels_use_frontend_canonical_ids()
    test_label_metrics_compare_prediction_with_reference()
    test_validation_summary_json_preserves_chinese_without_bom()
    test_samples_api_exposes_reference_case_metadata()
    test_samples_api_reads_configured_reference_cases()
    test_local_reference_cases_include_flare22_with_label()
    test_log_reference_case_warnings_emits_for_missing_files()
    test_job_state_reports_result_readiness_after_completion()
    test_running_job_can_be_cancelled_and_process_is_terminated()
    test_job_summary_json_records_runtime_and_output_size()
    test_job_summary_json_records_resource_snapshots()
    test_create_job_reuses_cached_prediction_for_matching_cache_key()
    test_cached_prediction_revalidates_against_current_label_file()
    test_cached_prediction_falls_back_to_source_validation_summary()
    test_historical_fallback_overrides_with_current_request_taxonomy()
    test_cached_prediction_without_historical_validation_summary()
    test_find_cached_prediction_warns_when_no_candidate_has_validation_summary()
    test_real_job_uses_persistent_worker_when_enabled()
    test_persistent_worker_stdout_reader_is_reused_across_events()
    test_process_log_is_persisted_as_utf8_and_tail_is_returned()
    test_job_state_can_read_persisted_summary_after_restart()
    test_job_state_can_reconstruct_legacy_output_without_summary()
    test_e2e_inference_flow_create_events_result()
    test_e2e_inference_flow_via_api_endpoints()
    test_e2e_inference_failure_flow()
    test_push_heartbeat_emits_progress_event_with_heartbeat_flag()
    test_push_heartbeat_failure_does_not_raise()
