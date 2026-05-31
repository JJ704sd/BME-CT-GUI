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
    evaluate_script.write_text("ok", encoding="utf-8")
    server_dataset.write_text("ok", encoding="utf-8")

    with patch.dict(os.environ, {
        "SEGMENTATION_RUNTIME_TARGET": "server",
        "SEGMENTATION_SERVER_EVALUATE_SCRIPT": str(evaluate_script),
        "SEGMENTATION_SERVER_DATASET_JSON": str(server_dataset),
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
    assert report["labels"][0]["dice"] == 0.8
    assert report["labels"][1]["intersection_voxels"] == 2


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

    def fake_validate(result_path, label_path, labels, label_taxonomy="auto"):
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
    ]

    # FLARE22 reference has IDs {1..13}
    flare22_ids = set(range(1, 14))

    # Should detect FLARE22
    detected = taxonomy.detect_dataset(flare22_ids, amos_labels)
    assert detected == "FLARE22", f"Expected FLARE22, got {detected}"

    # Should build correct mapping
    mapping = taxonomy.build_remap_mapping(amos_labels, detected)
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
    """少量 FLARE22 标签只要有明确错位，也应触发自动 remap。"""
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

    detected = taxonomy.detect_dataset({1, 3}, amos_labels)
    mapping = taxonomy.build_remap_mapping(amos_labels, detected) if detected else {}

    assert detected == "FLARE22"
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


if __name__ == "__main__":
    test_taxonomy_detects_flare22_and_remaps_label_ids()
    test_taxonomy_detects_partial_flare22_labels_when_ids_are_mismatched()
    test_taxonomy_returns_none_for_amos_native_labels()
    test_validate_against_custom_label_respects_explicit_taxonomy_hints()
    test_model_state_reports_missing_required_files()
    test_server_runtime_ready_does_not_require_local_model_files()
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
    test_job_state_reports_result_readiness_after_completion()
    test_running_job_can_be_cancelled_and_process_is_terminated()
    test_job_summary_json_records_runtime_and_output_size()
    test_job_summary_json_records_resource_snapshots()
    test_create_job_reuses_cached_prediction_for_matching_cache_key()
    test_cached_prediction_revalidates_against_current_label_file()
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
