"""Vectorised IoU and spatial-relation utilities backed by NumPy."""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from bbox_proc.spatial.geometry import BBox


def _to_arrays(boxes: List[BBox]) -> np.ndarray:
    """Convert list of BBox to NumPy array of shape (N, 4) in xyxy format."""
    if not boxes:
        return np.empty((0, 4), dtype=np.float64)
    return np.array(
        [[b.x, b.y, b.x2, b.y2] for b in boxes], dtype=np.float64
    )


def iou_matrix(boxes_a: List[BBox], boxes_b: List[BBox]) -> np.ndarray:
    """Compute pairwise IoU matrix of shape (M, N).

    boxes_a: M bounding boxes
    boxes_b: N bounding boxes
    Returns matrix[i, j] = IoU(boxes_a[i], boxes_b[j]).
    """
    arr_a = _to_arrays(boxes_a)  # (M, 4)
    arr_b = _to_arrays(boxes_b)  # (N, 4)

    if arr_a.shape[0] == 0 or arr_b.shape[0] == 0:
        return np.zeros((len(boxes_a), len(boxes_b)), dtype=np.float64)

    # Broadcast intersection
    x1 = np.maximum(arr_a[:, 0:1], arr_b[:, 0])  # (M, N)
    y1 = np.maximum(arr_a[:, 1:2], arr_b[:, 1])
    x2 = np.minimum(arr_a[:, 2:3], arr_b[:, 2])
    y2 = np.minimum(arr_a[:, 3:4], arr_b[:, 3])

    inter_w = np.maximum(0.0, x2 - x1)
    inter_h = np.maximum(0.0, y2 - y1)
    inter = inter_w * inter_h  # (M, N)

    area_a = (arr_a[:, 2] - arr_a[:, 0]) * (arr_a[:, 3] - arr_a[:, 1])  # (M,)
    area_b = (arr_b[:, 2] - arr_b[:, 0]) * (arr_b[:, 3] - arr_b[:, 1])  # (N,)

    union = area_a[:, None] + area_b[None, :] - inter
    union = np.maximum(union, 1e-9)  # avoid division by zero

    return inter / union


def iou_single(box_a: BBox, box_b: BBox) -> float:
    """Compute IoU between two individual bounding boxes."""
    return float(iou_matrix([box_a], [box_b])[0, 0])


def centroid_distance_matrix(
    boxes_a: List[BBox], boxes_b: List[BBox]
) -> np.ndarray:
    """Euclidean distance between centroids, shape (M, N)."""
    if not boxes_a or not boxes_b:
        return np.zeros((len(boxes_a), len(boxes_b)), dtype=np.float64)

    cx_a = np.array([b.cx for b in boxes_a], dtype=np.float64)
    cy_a = np.array([b.cy for b in boxes_a], dtype=np.float64)
    cx_b = np.array([b.cx for b in boxes_b], dtype=np.float64)
    cy_b = np.array([b.cy for b in boxes_b], dtype=np.float64)

    dx = cx_a[:, None] - cx_b[None, :]  # (M, N)
    dy = cy_a[:, None] - cy_b[None, :]
    return np.sqrt(dx**2 + dy**2)


def pairs_exceeding_iou(
    boxes_a: List[BBox],
    boxes_b: List[BBox],
    threshold: float,
) -> List[Tuple[int, int]]:
    """Return index pairs (i, j) where IoU(boxes_a[i], boxes_b[j]) >= threshold."""
    matrix = iou_matrix(boxes_a, boxes_b)
    indices = np.argwhere(matrix >= threshold)
    return [(int(i), int(j)) for i, j in indices]


def pairs_within_distance(
    boxes_a: List[BBox],
    boxes_b: List[BBox],
    threshold: float,
) -> List[Tuple[int, int]]:
    """Return index pairs (i, j) where centroid distance <= threshold."""
    matrix = centroid_distance_matrix(boxes_a, boxes_b)
    indices = np.argwhere(matrix <= threshold)
    return [(int(i), int(j)) for i, j in indices]
