from __future__ import annotations

import importlib.util
import json
import os
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


def test_predict_command_uses_model_folder_and_job_io():
    server = load_server_module()

    with patch.dict(os.environ, {
        "SEGMENTATION_PREPROCESS_WORKERS": "3",
        "SEGMENTATION_EXPORT_WORKERS": "2",
    }):
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
    assert state["validation"] == validation
    assert server.jobs[body["job_id"]].events[-1]["cached_result"] is True
    assert result_response.status_code == 200
    assert result_response.content == b"cached-result"


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


if __name__ == "__main__":
    test_model_state_reports_missing_required_files()
    test_create_job_rejects_when_model_is_not_ready()
    test_predict_command_uses_model_folder_and_job_io()
    test_predict_worker_counts_have_safe_defaults_and_clamps()
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
    test_real_job_uses_persistent_worker_when_enabled()
    test_process_log_is_persisted_as_utf8_and_tail_is_returned()
    test_job_state_can_read_persisted_summary_after_restart()
    test_job_state_can_reconstruct_legacy_output_without_summary()
