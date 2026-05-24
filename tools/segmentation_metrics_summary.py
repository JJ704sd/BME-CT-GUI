from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROUND_DIGITS = 6


def round_metric(value: float | None) -> float | None:
    if value is None:
        return None
    if not math.isfinite(float(value)):
        return None
    return round(float(value), ROUND_DIGITS)


def safe_divide(numerator: int | float, denominator: int | float) -> float | None:
    if denominator == 0:
        return None
    return float(numerator) / float(denominator)


def dice_from_counts(intersection: int, prediction_count: int, reference_count: int) -> float | None:
    return safe_divide(2 * intersection, prediction_count + reference_count)


def iou_from_counts(intersection: int, union_count: int) -> float | None:
    return safe_divide(intersection, union_count)


def normalize_label_array(array: Any) -> np.ndarray:
    values = np.asarray(array)
    if np.issubdtype(values.dtype, np.floating):
        values = np.rint(values)
    return values.astype(np.int32, copy=False)


def crop_to_union(mask_a: np.ndarray, mask_b: np.ndarray, margin: int = 1) -> tuple[np.ndarray, np.ndarray]:
    coords = np.argwhere(mask_a | mask_b)
    if coords.size == 0:
        return mask_a, mask_b
    starts = np.maximum(coords.min(axis=0) - margin, 0)
    stops = np.minimum(coords.max(axis=0) + margin + 1, mask_a.shape)
    slices = tuple(slice(int(start), int(stop)) for start, stop in zip(starts, stops))
    return mask_a[slices], mask_b[slices]


def surface_mask(mask: np.ndarray) -> np.ndarray:
    if not bool(mask.any()):
        return mask
    try:
        from scipy import ndimage
    except Exception:
        return mask

    structure = ndimage.generate_binary_structure(mask.ndim, 1)
    eroded = ndimage.binary_erosion(mask, structure=structure, border_value=0)
    return mask & ~eroded


def directed_surface_distance(source: np.ndarray, target: np.ndarray, spacing: tuple[float, ...]) -> float:
    from scipy import ndimage

    distances = ndimage.distance_transform_edt(~target, sampling=spacing)
    return float(distances[source].max()) if bool(source.any()) else 0.0


def hausdorff_distance(
    prediction_mask: np.ndarray,
    reference_mask: np.ndarray,
    spacing: Iterable[float] | None = None,
) -> float | None:
    if not bool(prediction_mask.any()) and not bool(reference_mask.any()):
        return None
    if not bool(prediction_mask.any()) or not bool(reference_mask.any()):
        return None

    spacing_tuple = tuple(float(item) for item in (spacing or (1.0,) * prediction_mask.ndim))
    cropped_prediction, cropped_reference = crop_to_union(prediction_mask, reference_mask)
    prediction_surface = surface_mask(cropped_prediction)
    reference_surface = surface_mask(cropped_reference)
    if not bool(prediction_surface.any()) or not bool(reference_surface.any()):
        return None

    forward = directed_surface_distance(prediction_surface, reference_surface, spacing_tuple)
    backward = directed_surface_distance(reference_surface, prediction_surface, spacing_tuple)
    return max(forward, backward)


def make_label(label_value: int, name: str | None = None) -> dict[str, Any]:
    return {"label": int(label_value), "name": name or f"Label {int(label_value)}"}


def labels_from_dataset_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    labels = []
    for name, value in data.get("labels", {}).items():
        if isinstance(value, (list, tuple)):
            continue
        label_value = int(value)
        if label_value == 0:
            continue
        labels.append(make_label(label_value, str(name)))
    return sorted(labels, key=lambda item: item["label"])


def labels_from_summary_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_labels = data.get("labels", [])
    labels = []
    for item in raw_labels:
        if not isinstance(item, dict) or "label" not in item:
            continue
        labels.append(make_label(int(item["label"]), str(item.get("name") or f"Label {item['label']}")))
    return sorted(labels, key=lambda item: item["label"])


def infer_labels(prediction: np.ndarray, reference: np.ndarray) -> list[dict[str, Any]]:
    values = np.union1d(np.unique(prediction), np.unique(reference))
    return [make_label(int(value)) for value in values if int(value) != 0]


def load_labels(
    prediction: np.ndarray,
    reference: np.ndarray,
    dataset_json: Path | None = None,
    labels_json: Path | None = None,
) -> tuple[list[dict[str, Any]], str]:
    if labels_json and labels_json.exists():
        return labels_from_summary_json(labels_json), str(labels_json)
    if dataset_json and dataset_json.exists():
        return labels_from_dataset_json(dataset_json), str(dataset_json)
    return infer_labels(prediction, reference), "inferred-from-prediction-and-reference"


def finite_mean(values: list[float | None]) -> float | None:
    finite_values = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not finite_values:
        return None
    return sum(finite_values) / len(finite_values)


def finite_min(values: list[float | None]) -> float | None:
    finite_values = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return min(finite_values) if finite_values else None


def finite_max(values: list[float | None]) -> float | None:
    finite_values = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return max(finite_values) if finite_values else None


def path_text(path: Path | None) -> str | None:
    return str(path) if path is not None else None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checkpoint_metadata(path: Path | None, hash_checkpoint: bool = True) -> dict[str, Any] | None:
    if path is None:
        return None
    metadata: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
    }
    if not path.exists():
        return metadata
    stat = path.stat()
    metadata.update(
        {
            "size_bytes": stat.st_size,
            "modified_time": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        }
    )
    if hash_checkpoint:
        metadata["sha256"] = file_sha256(path)
    return metadata


def compute_segmentation_metrics(
    prediction: Any,
    reference: Any,
    labels: list[dict[str, Any]],
    spacing: Iterable[float] | None = None,
    sample_id: str = "unknown",
    prediction_path: Path | None = None,
    reference_path: Path | None = None,
    checkpoint_path: Path | None = None,
    labels_source: str | None = None,
    hash_checkpoint: bool = False,
) -> dict[str, Any]:
    prediction_array = normalize_label_array(prediction)
    reference_array = normalize_label_array(reference)
    if prediction_array.shape != reference_array.shape:
        raise ValueError(
            f"prediction shape {prediction_array.shape} does not match reference shape {reference_array.shape}"
        )

    spacing_tuple = tuple(float(item) for item in (spacing or (1.0,) * prediction_array.ndim))
    total_voxels = int(prediction_array.size)
    correct_voxels = int((prediction_array == reference_array).sum())
    voxel_accuracy = safe_divide(correct_voxels, total_voxels)

    label_reports: list[dict[str, Any]] = []
    dice_values: list[float | None] = []
    iou_values: list[float | None] = []
    label_accuracy_values: list[float | None] = []
    hausdorff_values: list[float | None] = []

    for item in sorted(labels, key=lambda label: int(label["label"])):
        label_value = int(item["label"])
        prediction_mask = prediction_array == label_value
        reference_mask = reference_array == label_value
        prediction_count = int(prediction_mask.sum())
        reference_count = int(reference_mask.sum())
        intersection = int((prediction_mask & reference_mask).sum())
        union = int((prediction_mask | reference_mask).sum())
        label_correct = int((prediction_mask == reference_mask).sum())
        dice = dice_from_counts(intersection, prediction_count, reference_count)
        iou = iou_from_counts(intersection, union)
        label_accuracy = safe_divide(label_correct, total_voxels)
        hausdorff = hausdorff_distance(prediction_mask, reference_mask, spacing_tuple)

        dice_values.append(dice)
        iou_values.append(iou)
        label_accuracy_values.append(label_accuracy)
        hausdorff_values.append(hausdorff)
        label_reports.append(
            {
                "label": label_value,
                "name": item.get("name") or item.get("nameZh") or item.get("nameEn") or f"Label {label_value}",
                "dice": round_metric(dice),
                "iou": round_metric(iou),
                "voxel_accuracy": round_metric(label_accuracy),
                "pixel_accuracy": round_metric(label_accuracy),
                "hausdorff_distance": round_metric(hausdorff),
                "hausdorff_unit": "mm",
                "prediction_voxels": prediction_count,
                "reference_voxels": reference_count,
                "intersection_voxels": intersection,
                "union_voxels": union,
                "false_positive_voxels": int((prediction_mask & ~reference_mask).sum()),
                "false_negative_voxels": int((~prediction_mask & reference_mask).sum()),
            }
        )

    foreground_prediction = prediction_array > 0
    foreground_reference = reference_array > 0
    foreground_intersection = int((foreground_prediction & foreground_reference).sum())
    foreground_union = int((foreground_prediction | foreground_reference).sum())
    foreground_dice = dice_from_counts(
        foreground_intersection,
        int(foreground_prediction.sum()),
        int(foreground_reference.sum()),
    )
    foreground_iou = iou_from_counts(foreground_intersection, foreground_union)

    return {
        "summary_type": "segmentation_metrics",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_id": sample_id,
        "paths": {
            "prediction": path_text(prediction_path),
            "reference": path_text(reference_path),
            "checkpoint": path_text(checkpoint_path),
        },
        "checkpoint": checkpoint_metadata(checkpoint_path, hash_checkpoint=hash_checkpoint),
        "labels_source": labels_source,
        "shape": list(prediction_array.shape),
        "spacing": list(spacing_tuple),
        "spacing_unit": "mm",
        "total_voxels": total_voxels,
        "correct_voxels": correct_voxels,
        "voxel_accuracy": round_metric(voxel_accuracy),
        "pixel_accuracy": round_metric(voxel_accuracy),
        "mean_label_voxel_accuracy": round_metric(finite_mean(label_accuracy_values)),
        "mean_label_pixel_accuracy": round_metric(finite_mean(label_accuracy_values)),
        "mean_dice": round_metric(finite_mean(dice_values)),
        "min_dice": round_metric(finite_min(dice_values)),
        "foreground_dice": round_metric(foreground_dice),
        "mean_iou": round_metric(finite_mean(iou_values)),
        "min_iou": round_metric(finite_min(iou_values)),
        "foreground_iou": round_metric(foreground_iou),
        "mean_hausdorff_distance": round_metric(finite_mean(hausdorff_values)),
        "max_hausdorff_distance": round_metric(finite_max(hausdorff_values)),
        "hausdorff_unit": "mm",
        "hausdorff_definition": "symmetric surface Hausdorff distance on non-empty label masks",
        "labels": label_reports,
    }


def format_value(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def render_markdown(report: dict[str, Any]) -> str:
    checkpoint = report.get("checkpoint") or {}
    checkpoint_sha = checkpoint.get("sha256")
    lines = [
        "# Segmentation Metrics Summary",
        "",
        "This file records segmentation metrics for one prediction/reference pair and can be reused for future trained weights.",
        "",
        "## Run",
        "",
        f"- Generated: {report.get('generated_at')}",
        f"- Sample ID: {report.get('sample_id')}",
        f"- Prediction: {report.get('paths', {}).get('prediction')}",
        f"- Reference: {report.get('paths', {}).get('reference')}",
        f"- Checkpoint: {report.get('paths', {}).get('checkpoint')}",
        f"- Checkpoint SHA256: {checkpoint_sha or 'N/A'}",
        f"- Labels Source: {report.get('labels_source')}",
        f"- Shape: {report.get('shape')}",
        f"- Spacing: {report.get('spacing')} {report.get('spacing_unit')}",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Dice Mean | {format_value(report.get('mean_dice'))} |",
        f"| Dice Min | {format_value(report.get('min_dice'))} |",
        f"| Foreground Dice | {format_value(report.get('foreground_dice'))} |",
        f"| IoU Mean | {format_value(report.get('mean_iou'))} |",
        f"| IoU Min | {format_value(report.get('min_iou'))} |",
        f"| Foreground IoU | {format_value(report.get('foreground_iou'))} |",
        f"| Voxel Accuracy | {format_value(report.get('voxel_accuracy'))} |",
        f"| Pixel Accuracy | {format_value(report.get('pixel_accuracy'))} |",
        f"| Mean Hausdorff Distance ({report.get('hausdorff_unit')}) | {format_value(report.get('mean_hausdorff_distance'))} |",
        f"| Max Hausdorff Distance ({report.get('hausdorff_unit')}) | {format_value(report.get('max_hausdorff_distance'))} |",
        "",
        "## Per-label Metrics",
        "",
        "| Label | Name | Dice | IoU | Voxel Accuracy | Pixel Accuracy | Hausdorff Distance (mm) | Pred Voxels | Ref Voxels |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in report.get("labels", []):
        lines.append(
            "| "
            f"{item.get('label')} | "
            f"{item.get('name')} | "
            f"{format_value(item.get('dice'))} | "
            f"{format_value(item.get('iou'))} | "
            f"{format_value(item.get('voxel_accuracy'))} | "
            f"{format_value(item.get('pixel_accuracy'))} | "
            f"{format_value(item.get('hausdorff_distance'))} | "
            f"{item.get('prediction_voxels')} | "
            f"{item.get('reference_voxels')} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Dice and IoU are computed per label, excluding label 0 from label aggregates.",
            "- Pixel Accuracy is the same exact-match value as Voxel Accuracy for 3D NIfTI volumes.",
            "- Hausdorff Distance is reported in physical spacing units from the NIfTI header. It is N/A when both masks are empty or one side is empty.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_summary_files(report: dict[str, Any], output_dir: Path, stem: str = "segmentation-metrics-summary") -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def load_nifti(path: Path) -> tuple[np.ndarray, tuple[float, ...]]:
    import nibabel as nib

    image = nib.load(str(path))
    data = normalize_label_array(np.asanyarray(image.dataobj))
    spacing = tuple(float(item) for item in image.header.get_zooms()[: data.ndim])
    return data, spacing


def default_dataset_json() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root.parent / "nnUNet_results" / "Dataset001_FLARE" / "nnUNetTrainer__nnUNetPlans__2d" / "dataset.json"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute segmentation metrics and write JSON/Markdown summaries.")
    parser.add_argument("--prediction", type=Path, required=True, help="Prediction NIfTI path.")
    parser.add_argument("--reference", type=Path, required=True, help="Reference label NIfTI path.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for summary outputs.")
    parser.add_argument("--sample-id", default="unknown", help="Sample/case identifier.")
    parser.add_argument("--checkpoint", type=Path, default=None, help="Training checkpoint path to record.")
    parser.add_argument("--dataset-json", type=Path, default=default_dataset_json(), help="nnUNet dataset.json labels file.")
    parser.add_argument("--labels-json", type=Path, default=None, help="Existing summary JSON with a labels array.")
    parser.add_argument("--stem", default="segmentation-metrics-summary", help="Output filename stem.")
    parser.add_argument("--skip-checkpoint-hash", action="store_true", help="Record checkpoint metadata without SHA256.")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs without writing summaries.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    prediction, prediction_spacing = load_nifti(args.prediction)
    reference, reference_spacing = load_nifti(args.reference)
    labels, labels_source = load_labels(prediction, reference, args.dataset_json, args.labels_json)
    report = compute_segmentation_metrics(
        prediction,
        reference,
        labels=labels,
        spacing=prediction_spacing,
        sample_id=args.sample_id,
        prediction_path=args.prediction,
        reference_path=args.reference,
        checkpoint_path=args.checkpoint,
        labels_source=labels_source,
        hash_checkpoint=not args.skip_checkpoint_hash,
    )
    report["reference_spacing"] = list(reference_spacing)
    report["spacing_warning"] = None if tuple(prediction_spacing) == tuple(reference_spacing) else "prediction and reference spacing differ"

    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    written = write_summary_files(report, args.output_dir, stem=args.stem)
    print(json.dumps({key: str(value) for key, value in written.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
