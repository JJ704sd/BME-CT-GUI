"""Start the local demo: backend + frontend + reference-cases env vars.

Wraps the manual commands from docs/local-cache-demo-runbook.md so the
operator does not have to remember SEGMENTATION_REFERENCE_CASES_JSON,
SEGMENTATION_PERSISTENT_WORKER, SEGMENTATION_DEVICE, or VITE_API_ENDPOINT
on demo day.

Usage:
    python tools/start_local_demo.py
    python tools/start_local_demo.py --no-persistent-worker
    python tools/start_local_demo.py --device cpu --reference-cases-json /abs/cases.json
    python tools/start_local_demo.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Sequence

PROTOTYPE = Path(__file__).resolve().parent.parent
DEFAULT_REFERENCE_CASES_JSON = PROTOTYPE / "examples" / "reference_cases.json"
BACKEND_PORT = 8000
FRONTEND_PORT = 5173


def resolve_device(requested: str) -> str:
  if requested != "auto":
    return requested
  try:
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"
  except ImportError:
    return "cpu"


def build_env(args: argparse.Namespace, reference_cases_path: Path) -> dict[str, str]:
  env = os.environ.copy()
  env["SEGMENTATION_REFERENCE_CASES_JSON"] = str(reference_cases_path)
  if not args.no_persistent_worker:
    env["SEGMENTATION_PERSISTENT_WORKER"] = "1"
  env["SEGMENTATION_DEVICE"] = resolve_device(args.device)
  env["VITE_API_ENDPOINT"] = f"http://127.0.0.1:{args.backend_port}"
  return env


def print_plan(env: dict[str, str], args: argparse.Namespace) -> None:
  print("[env vars that will be set for backend + frontend]")
  for key in (
    "SEGMENTATION_REFERENCE_CASES_JSON",
    "SEGMENTATION_PERSISTENT_WORKER",
    "SEGMENTATION_DEVICE",
    "VITE_API_ENDPOINT",
  ):
    if key in env:
      print(f"  {key}={env[key]}")
  print()
  print("[commands]")
  print(f"  backend:  python -m uvicorn server.main:app --host 127.0.0.1 --port {args.backend_port}")
  print(f"  frontend: npm run dev -- --port {args.frontend_port}")
  print()


def _find_executable(name: str) -> str:
  path = shutil.which(name)
  if path:
    return path
  raise FileNotFoundError(
    f"Could not find executable '{name}' on PATH. Install Node.js (for {name}) and retry."
  )


def wait_for_samples(backend_port: int, timeout_seconds: float = 15.0) -> list | None:
  url = f"http://127.0.0.1:{backend_port}/api/samples"
  deadline = time.time() + timeout_seconds
  while time.time() < deadline:
    try:
      with urllib.request.urlopen(url, timeout=1.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, dict) and isinstance(data.get("samples"), list):
          return data["samples"]
    except Exception:
      time.sleep(0.5)
  return None


def shutdown(procs: list[subprocess.Popen]) -> None:
  for proc in procs:
    if proc.poll() is None:
      try:
        proc.terminate()
      except ProcessLookupError:
        pass
  for proc in procs:
    try:
      proc.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
      proc.kill()


def run(args: argparse.Namespace) -> int:
  reference_cases_path = Path(args.reference_cases_json).resolve()
  if not reference_cases_path.exists():
    print(f"ERROR: reference cases JSON not found: {reference_cases_path}", file=sys.stderr)
    return 2
  try:
    cases = json.loads(reference_cases_path.read_text(encoding="utf-8"))
  except json.JSONDecodeError as exc:
    print(f"ERROR: failed to parse {reference_cases_path}: {exc}", file=sys.stderr)
    return 2
  samples_field = cases.get("samples") if isinstance(cases, dict) else None
  if not isinstance(samples_field, list):
    print(f"ERROR: {reference_cases_path} must contain a 'samples' list", file=sys.stderr)
    return 2
  if not samples_field:
    print(f"ERROR: {reference_cases_path} has zero samples; demo cannot proceed", file=sys.stderr)
    return 2
  if len(samples_field) < 4:
    print(
      f"WARNING: {reference_cases_path} exposes only {len(samples_field)} case(s); "
      "demo runbook expects 4 (AMOS_0117, FLARE22_Tr_0009, WORD, AbdomenCT-1K).",
      file=sys.stderr,
    )

  env = build_env(args, reference_cases_path)
  print_plan(env, args)

  if args.dry_run:
    return 0

  npm_executable = _find_executable("npm")
  backend_cmd = [
    sys.executable, "-m", "uvicorn", "server.main:app",
    "--host", "127.0.0.1", "--port", str(args.backend_port),
  ]
  frontend_cmd = [
    npm_executable, "run", "dev", "--", "--port", str(args.frontend_port),
  ]

  procs: list[subprocess.Popen] = []
  signal.signal(signal.SIGINT, signal.default_int_handler)
  try:
    procs.append(subprocess.Popen(backend_cmd, cwd=str(PROTOTYPE), env=env))
    procs.append(subprocess.Popen(frontend_cmd, cwd=str(PROTOTYPE), env=env))
    print(f"Backend PID:  {procs[0].pid}")
    print(f"Frontend PID: {procs[1].pid}")
    print()

    samples = wait_for_samples(args.backend_port, timeout_seconds=15.0)
    if samples is None:
      print(
        "WARNING: backend did not respond at /api/samples within 15s.",
        file=sys.stderr,
      )
      print(
        "  Check the backend log above; demo will not have reference cases loaded.",
        file=sys.stderr,
      )
    else:
      print(f"Backend ready: {len(samples)} reference case(s) exposed at /api/samples:")
      for sample in samples:
        sid = sample.get("id") or "?"
        sname = sample.get("name") or ""
        sds = sample.get("dataset") or "?"
        print(f"  - {sid} ({sname}) [{sds}]")
      print()
      print("Verify with:")
      print(f"  curl http://127.0.0.1:{args.backend_port}/api/samples")
      print()
      print(f"Open the GUI at: http://127.0.0.1:{args.frontend_port}/")
      print("Press Ctrl+C to stop both processes.")
    print()

    while True:
      time.sleep(1.0)
      for proc in procs:
        if proc.poll() is not None:
          return proc.returncode or 0
  except KeyboardInterrupt:
    print("Stopping ...")
    return 0
  finally:
    shutdown(procs)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Start the local demo (backend + frontend).")
  parser.add_argument(
    "--reference-cases-json",
    default=str(DEFAULT_REFERENCE_CASES_JSON),
    help=f"Reference cases JSON (default: {DEFAULT_REFERENCE_CASES_JSON})",
  )
  parser.add_argument(
    "--no-persistent-worker",
    action="store_true",
    help="Disable the persistent nnUNetv2 worker (default: enabled via SEGMENTATION_PERSISTENT_WORKER=1).",
  )
  parser.add_argument(
    "--device",
    choices=("auto", "cuda", "cpu"),
    default="auto",
    help="Inference device (default: auto-detect via torch.cuda.is_available).",
  )
  parser.add_argument("--backend-port", type=int, default=BACKEND_PORT, help=f"Backend port (default: {BACKEND_PORT})")
  parser.add_argument("--frontend-port", type=int, default=FRONTEND_PORT, help=f"Frontend port (default: {FRONTEND_PORT})")
  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Print env vars and commands without spawning processes.",
  )
  return parser.parse_args(argv)


if __name__ == "__main__":
  sys.exit(run(parse_args(sys.argv[1:])))
