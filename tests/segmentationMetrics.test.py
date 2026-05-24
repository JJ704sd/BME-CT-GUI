from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "segmentation_metrics_summary.py"


def load_metrics_tool():
    spec = importlib.util.spec_from_file_location("segmentation_metrics_summary", TOOL_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_test_output_dir(name: str) -> Path:
    output_dir = (ROOT / ".test-output" / name).resolve()
    test_root = (ROOT / ".test-output").resolve()
    assert test_root in output_dir.parents
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def test_compute_segmentation_metrics_reports_requested_metrics():
    tool = load_metrics_tool()
    prediction = np.array(
        [
            [0, 1, 2, 2],
            [0, 1, 0, 2],
        ]
    )
    reference = np.array(
        [
            [0, 1, 1, 2],
            [0, 1, 2, 2],
        ]
    )

    report = tool.compute_segmentation_metrics(
        prediction,
        reference,
        labels=[
            {"label": 1, "name": "liver"},
            {"label": 2, "name": "right kidney"},
            {"label": 3, "name": "empty"},
        ],
        spacing=(1.0, 1.0),
        sample_id="synthetic",
    )

    by_label = {item["label"]: item for item in report["labels"]}
    assert report["sample_id"] == "synthetic"
    assert report["voxel_accuracy"] == 0.75
    assert report["mean_dice"] == 0.733333
    assert report["mean_iou"] == 0.583333
    assert report["foreground_dice"] == 0.909091
    assert report["foreground_iou"] == 0.833333
    assert by_label[1]["dice"] == 0.8
    assert by_label[1]["iou"] == 0.666667
    assert by_label[1]["hausdorff_distance"] == 1.0
    assert by_label[2]["dice"] == 0.666667
    assert by_label[2]["iou"] == 0.5
    assert by_label[2]["hausdorff_distance"] == 1.0
    assert by_label[3]["dice"] is None
    assert by_label[3]["iou"] is None
    assert by_label[3]["hausdorff_distance"] is None


def test_summary_writes_json_and_markdown_for_future_training_runs(tmp_path):
    tool = load_metrics_tool()
    report = tool.compute_segmentation_metrics(
        np.array([[0, 1], [0, 1]]),
        np.array([[0, 1], [1, 1]]),
        labels=[{"label": 1, "name": "liver"}],
        spacing=(2.0, 3.0),
        sample_id="future_case",
        prediction_path=Path("pred.nii.gz"),
        reference_path=Path("ref.nii.gz"),
        checkpoint_path=Path("checkpoint_best.pth"),
    )

    written = tool.write_summary_files(report, tmp_path, stem="metrics-summary")
    parsed = json.loads(written["json"].read_text(encoding="utf-8"))
    markdown = written["markdown"].read_text(encoding="utf-8")

    assert parsed["sample_id"] == "future_case"
    assert parsed["paths"]["prediction"] == "pred.nii.gz"
    assert parsed["paths"]["reference"] == "ref.nii.gz"
    assert parsed["paths"]["checkpoint"] == "checkpoint_best.pth"
    assert parsed["spacing"] == [2.0, 3.0]
    assert "Dice" in markdown
    assert "IoU" in markdown
    assert "Voxel Accuracy" in markdown
    assert "Hausdorff Distance" in markdown
    assert "future_case" in markdown


if __name__ == "__main__":
    test_compute_segmentation_metrics_reports_requested_metrics()
    test_summary_writes_json_and_markdown_for_future_training_runs(make_test_output_dir("segmentation-metrics-test"))
