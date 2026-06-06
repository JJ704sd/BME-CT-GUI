"""Dry-run coverage for tools/start_local_demo.py.

Verifies env-var propagation, reference-cases JSON validation, --dry-run
does not spawn processes, and resolve_device honors torch auto-detect.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "tools" / "start_local_demo.py"


def load_script_module():
  spec = importlib.util.spec_from_file_location("start_local_demo", SCRIPT_PATH)
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


def _make_args(**overrides) -> Namespace:
  base = dict(
    reference_cases_json=str(PROJECT_ROOT / "examples" / "reference_cases.json"),
    no_persistent_worker=False,
    device="auto",
    backend_port=8000,
    frontend_port=5173,
    dry_run=True,
  )
  base.update(overrides)
  return Namespace(**base)


def _make_tmp_dir() -> Path:
  path = Path(tempfile.mkdtemp(prefix="start-local-demo-"))
  return path


def test_default_args_propagate_all_required_env_vars():
  script = load_script_module()
  cases_path = PROJECT_ROOT / "examples" / "reference_cases.json"
  args = _make_args()
  env = script.build_env(args, cases_path)

  assert env["SEGMENTATION_REFERENCE_CASES_JSON"] == str(cases_path)
  assert env["SEGMENTATION_PERSISTENT_WORKER"] == "1"
  assert env["SEGMENTATION_DEVICE"] in {"cuda", "cpu"}
  assert env["VITE_API_ENDPOINT"] == "http://127.0.0.1:8000"
  assert env["PATH"], "must inherit the parent PATH so npm/python resolve"


def test_no_persistent_worker_does_not_set_env_var():
  script = load_script_module()
  cases_path = PROJECT_ROOT / "examples" / "reference_cases.json"
  args = _make_args(no_persistent_worker=True)
  env = script.build_env(args, cases_path)
  assert "SEGMENTATION_PERSISTENT_WORKER" not in env


def test_explicit_device_overrides_auto_detect():
  script = load_script_module()
  cases_path = PROJECT_ROOT / "examples" / "reference_cases.json"
  args = _make_args(device="cpu")
  env = script.build_env(args, cases_path)
  assert env["SEGMENTATION_DEVICE"] == "cpu"

  args = _make_args(device="cuda")
  env = script.build_env(args, cases_path)
  assert env["SEGMENTATION_DEVICE"] == "cuda"


def test_resolve_device_uses_torch_when_auto():
  """resolve_device('auto') must consult torch.cuda.is_available; fall back to cpu on ImportError."""
  script = load_script_module()
  with patch.dict(sys.modules, {"torch": None}):
    assert script.resolve_device("auto") == "cpu"
  fake_torch = type("M", (), {"cuda": type("C", (), {"is_available": staticmethod(lambda: True)})()})
  with patch.dict(sys.modules, {"torch": fake_torch}):
    assert script.resolve_device("auto") == "cuda"


def test_dry_run_does_not_spawn_subprocess():
  script = load_script_module()
  args = _make_args()
  with patch.object(subprocess, "Popen") as popen:
    rc = script.run(args)
  assert rc == 0
  popen.assert_not_called()


def test_run_rejects_missing_reference_cases_json():
  script = load_script_module()
  tmp = _make_tmp_dir()
  try:
    args = _make_args(reference_cases_json=str(tmp / "absent.json"))
    with patch.object(subprocess, "Popen") as popen:
      rc = script.run(args)
  finally:
    shutil.rmtree(tmp, ignore_errors=True)
  assert rc == 2
  popen.assert_not_called()


def test_run_rejects_unparseable_reference_cases_json():
  script = load_script_module()
  tmp = _make_tmp_dir()
  try:
    bad_path = tmp / "bad.json"
    bad_path.write_text("{not json", encoding="utf-8")
    args = _make_args(reference_cases_json=str(bad_path))
    with patch.object(subprocess, "Popen") as popen:
      rc = script.run(args)
  finally:
    shutil.rmtree(tmp, ignore_errors=True)
  assert rc == 2
  popen.assert_not_called()


def test_run_rejects_reference_cases_without_samples_list():
  script = load_script_module()
  tmp = _make_tmp_dir()
  try:
    no_samples = tmp / "no_samples.json"
    no_samples.write_text(json.dumps({"other": []}), encoding="utf-8")
    args = _make_args(reference_cases_json=str(no_samples))
    with patch.object(subprocess, "Popen") as popen:
      rc = script.run(args)
  finally:
    shutil.rmtree(tmp, ignore_errors=True)
  assert rc == 2
  popen.assert_not_called()


def test_run_rejects_empty_samples_list():
  script = load_script_module()
  tmp = _make_tmp_dir()
  try:
    empty = tmp / "empty.json"
    empty.write_text(json.dumps({"samples": []}), encoding="utf-8")
    args = _make_args(reference_cases_json=str(empty))
    with patch.object(subprocess, "Popen") as popen:
      rc = script.run(args)
  finally:
    shutil.rmtree(tmp, ignore_errors=True)
  assert rc == 2
  popen.assert_not_called()


def test_run_warns_when_samples_below_four():
  """Fewer than 4 cases is unusual but not fatal — must emit a warning to stderr."""
  script = load_script_module()
  tmp = _make_tmp_dir()
  try:
    few = tmp / "few.json"
    few.write_text(json.dumps({"samples": [{"id": "a"}, {"id": "b"}]}), encoding="utf-8")
    args = _make_args(reference_cases_json=str(few))
    captured_stderr: list[str] = []
    with patch("sys.stderr.write", side_effect=lambda s: captured_stderr.append(s)):
      with patch.object(subprocess, "Popen") as popen:
        rc = script.run(args)
  finally:
    shutil.rmtree(tmp, ignore_errors=True)
  assert rc == 0
  popen.assert_not_called()
  assert any("only 2 case" in line for line in captured_stderr)


def test_default_reference_cases_json_has_four_samples():
  """examples/reference_cases.json must keep the 4-case shape so the runbook
  and start_local_demo.py's '4 cases' warning stay aligned."""
  cases_path = PROJECT_ROOT / "examples" / "reference_cases.json"
  assert cases_path.exists(), f"reference cases JSON missing: {cases_path}"
  cases = json.loads(cases_path.read_text(encoding="utf-8"))
  assert isinstance(cases.get("samples"), list)
  assert len(cases["samples"]) == 4
  ids = {sample.get("id") for sample in cases["samples"]}
  assert "amos_0117" in ids
  assert "flare22_tr_0009" in ids


def test_wait_for_samples_parses_first_valid_response():
  """wait_for_samples must keep polling until /api/samples returns a dict
  with a 'samples' list — and return that list, not the raw dict."""
  import io

  script = load_script_module()
  fake_response = io.BytesIO(json.dumps({"samples": [{"id": "a"}, {"id": "b"}]}).encode("utf-8"))
  fake_response.__enter__ = lambda self: self
  fake_response.__exit__ = lambda self, *a: None
  with patch.object(script.urllib.request, "urlopen", return_value=fake_response):
    result = script.wait_for_samples(8000, timeout_seconds=2.0)
  assert result == [{"id": "a"}, {"id": "b"}]


if __name__ == "__main__":
  test_default_args_propagate_all_required_env_vars()
  test_no_persistent_worker_does_not_set_env_var()
  test_explicit_device_overrides_auto_detect()
  test_resolve_device_uses_torch_when_auto()
  test_dry_run_does_not_spawn_subprocess()
  test_run_rejects_missing_reference_cases_json
  test_run_rejects_unparseable_reference_cases_json
  test_run_rejects_reference_cases_without_samples_list
  test_run_rejects_empty_samples_list()
  test_run_warns_when_samples_below_four()
  test_default_reference_cases_json_has_four_samples()
  test_wait_for_samples_parses_first_valid_response()
  print("startLocalDemo tests PASSED")
