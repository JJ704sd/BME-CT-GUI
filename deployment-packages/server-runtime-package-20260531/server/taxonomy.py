"""Taxonomy detection and remap for cross-dataset label validation.

When the user uploads a label file from a different dataset (e.g. FLARE22)
but the checkpoint is trained on another (e.g. AMOS22), label IDs have
different semantic meanings. This module detects the mismatch and remaps
reference label IDs to match the checkpoint's ID scheme.
"""

from __future__ import annotations

import numpy as np
from typing import Any

# FLARE22 label definitions (user-provided)
# Names are already in canonical form after alias resolution
FLARE22_LABELS: dict[int, str] = {
    1: "liver",
    2: "right_kidney",
    3: "spleen",
    4: "pancreas",
    5: "aorta",
    6: "ivc",
    7: "right_adrenal_gland",
    8: "left_adrenal_gland",
    9: "gallbladder",
    10: "esophagus",
    11: "stomach",
    12: "duodenum",
    13: "left_kidney",
}

# Known dataset label tables
KNOWN_DATASETS: dict[str, dict[int, str]] = {
    "FLARE22": FLARE22_LABELS,
}

SUPPORTED_TAXONOMY_HINTS = {"auto", "AMOS22", "FLARE22"}


def normalize_taxonomy_hint(value: str | None) -> str:
    normalized = str(value or "auto").strip().upper()
    if normalized in {"AMOS22", "FLARE22"}:
        return normalized
    return "auto"


# Canonical name aliases — different datasets use different names for the same organ
_NAME_ALIASES: dict[str, str] = {
    "postcava": "ivc",
    "inferior_vena_cava": "ivc",
    "gall_bladder": "gallbladder",
    "right_adrenal": "right_adrenal_gland",
    "left_adrenal": "left_adrenal_gland",
}


def _normalize_organ_name(name: str) -> str:
    """Normalize organ name to a canonical lowercase form."""
    normalized = str(name).strip().lower().replace(" ", "_").replace("-", "_")
    return _NAME_ALIASES.get(normalized, normalized)


def _build_checkpoint_name_map(checkpoint_labels: list[dict[str, Any]]) -> dict[int, str]:
    """Build {label_id: normalized_organ_name} from checkpoint label list."""
    result = {}
    for item in checkpoint_labels:
        label_id = int(item["label"])
        if label_id == 0:
            continue
        # Prefer nameEn, then id, then nameZh
        name = item.get("nameEn") or item.get("id") or item.get("nameZh") or ""
        result[label_id] = _normalize_organ_name(name)
    return result


def _build_reverse_map(name_to_id: dict[int, str]) -> dict[str, int]:
    """Build {organ_name: label_id} from {label_id: organ_name}."""
    return {name: lid for lid, name in name_to_id.items()}


def detect_dataset(
    reference_ids: set[int],
    checkpoint_labels: list[dict[str, Any]],
) -> str | None:
    """Detect which known dataset the reference labels belong to.

    Strategy: compare the reference label IDs with the checkpoint label IDs.
    If the reference IDs are a subset of the checkpoint IDs, the reference
    is likely from the same dataset (no remap needed).

    Only detect a different dataset if:
    1. The reference has IDs NOT in the checkpoint (strong evidence of different dataset)
    2. OR the user explicitly selects a different dataset via label_taxonomy hint

    Returns the detected dataset name, or None if no match.
    """
    if not reference_ids:
        return None

    ckpt_map = _build_checkpoint_name_map(checkpoint_labels)
    if not ckpt_map:
        return None

    ckpt_ids = set(ckpt_map.keys())

    # If reference IDs are a subset of checkpoint IDs, assume same dataset
    # This prevents AMOS labels from being detected as FLARE22
    if reference_ids.issubset(ckpt_ids):
        return None

    # Only try to detect if reference has IDs NOT in checkpoint
    # This is strong evidence of a different dataset
    best_match: str | None = None
    best_score = 0

    for dataset_name, dataset_labels in KNOWN_DATASETS.items():
        # Only consider datasets whose IDs overlap with reference
        dataset_ids = set(dataset_labels.keys())
        if not reference_ids.intersection(dataset_ids):
            continue

        # Check if the reference has IDs that match this dataset but not checkpoint
        # This is stronger evidence than just comparing label tables
        ref_only_ids = reference_ids - ckpt_ids
        if not ref_only_ids.intersection(dataset_ids):
            continue

        # Compare organ names at shared IDs
        shared_ids = reference_ids.intersection(dataset_ids).intersection(ckpt_ids)
        if not shared_ids:
            continue

        match_count = sum(
            1 for lid in shared_ids
            if dataset_labels[lid] == ckpt_map[lid]
        )
        mismatch_count = len(shared_ids) - match_count

        # Require very strong mismatch evidence (most IDs differ)
        # AND reference has IDs not in checkpoint
        strong_mismatch = (
            mismatch_count > match_count and
            mismatch_count >= 5  # Require at least 5 mismatches
        )
        if strong_mismatch:
            score = mismatch_count
            if score > best_score:
                best_score = score
                best_match = dataset_name

    return best_match


def build_remap_mapping(
    checkpoint_labels: list[dict[str, Any]],
    source_dataset: str,
) -> dict[int, int]:
    """Build {source_id: checkpoint_id} mapping by matching organ names.

    For each organ in the source dataset, find the checkpoint ID that has
    the same organ name.
    """
    ckpt_map = _build_checkpoint_name_map(checkpoint_labels)
    ckpt_reverse = _build_reverse_map(ckpt_map)

    source_labels = KNOWN_DATASETS[source_dataset]
    mapping: dict[int, int] = {}

    for src_id, src_name in source_labels.items():
        ckpt_id = ckpt_reverse.get(src_name)
        if ckpt_id is not None and ckpt_id != src_id:
            mapping[src_id] = ckpt_id
        elif ckpt_id is not None:
            # Same ID and same name, no remap needed
            pass
        # If organ not found in checkpoint, skip (unknown label)

    return mapping


def apply_remap(reference_array: Any, mapping: dict[int, int]) -> Any:
    """Remap reference label IDs according to the mapping.

    Returns a new array with IDs remapped. IDs not in the mapping are kept as-is.
    Uses a lookup table to avoid overwrite issues when IDs are swapped.
    """
    arr = np.asarray(reference_array, dtype=np.int32)
    max_id = int(arr.max())
    # Build lookup table: identity by default
    lut = np.arange(max_id + 1, dtype=np.int32)
    for src_id, dst_id in mapping.items():
        if src_id <= max_id:
            lut[src_id] = dst_id
    return lut[arr]
