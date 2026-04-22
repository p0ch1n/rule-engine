"""ImageAnalysisNode — filter AnnotatedFrames by pixel measurements within BBox ROIs."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from bbox_proc.nodes.base import BaseNode, PortDefinition, PortType
from bbox_proc.nodes.registry import NodeRegistry
from bbox_proc.schema.models import ImageAnalysisCondition, ImageAnalysisConfig
from bbox_proc.spatial.annotated import AnnotatedFrame
from bbox_proc.spatial.geometry import BBox


# ------------------------------------------------------------------ #
# ROI measurement helpers
# ------------------------------------------------------------------ #


def _extract_roi(image: np.ndarray, bbox: BBox) -> np.ndarray:
    """Clip bbox coordinates to image bounds and return the cropped ROI."""
    h, w = image.shape[:2]
    x1 = int(max(0, round(bbox.x)))
    y1 = int(max(0, round(bbox.y)))
    x2 = int(min(w, round(bbox.x + bbox.w)))
    y2 = int(min(h, round(bbox.y + bbox.h)))
    return image[y1:y2, x1:x2]


def measure_roi(image: np.ndarray, bbox: BBox, field: str) -> float:
    """Compute the mean of a measurement field over the BBox ROI.

    Assumes BGR channel order (OpenCV convention):
      index 0 = Blue, 1 = Green, 2 = Red

    Measurement ranges:
      intensity   0–255   (ITU-R BT.601 luminance)
      red/green/blue  0–255
      hue         0–360  (degrees)
      saturation  0–100
      value       0–100
    """
    roi = _extract_roi(image, bbox)
    if roi.size == 0:
        return 0.0

    f = roi.astype(np.float64)

    if field == "intensity":
        # ITU-R BT.601 luminance — BGR order
        return float((0.114 * f[:, :, 0] + 0.587 * f[:, :, 1] + 0.299 * f[:, :, 2]).mean())

    if field == "blue":
        return float(f[:, :, 0].mean())

    if field == "green":
        return float(f[:, :, 1].mean())

    if field == "red":
        return float(f[:, :, 2].mean())

    # HSV — pure NumPy, no OpenCV dependency
    r = f[:, :, 2] / 255.0
    g = f[:, :, 1] / 255.0
    b = f[:, :, 0] / 255.0
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin
    eps = 1e-9

    if field == "value":
        return float(cmax.mean() * 100.0)

    if field == "saturation":
        s = np.where(cmax > eps, delta / cmax, 0.0)
        return float(s.mean() * 100.0)

    if field == "hue":
        h = np.zeros_like(r)
        mask = delta > eps
        m_r = mask & (cmax == r)
        m_g = mask & (cmax == g)
        m_b = mask & (cmax == b)
        h[m_r] = (60.0 * ((g[m_r] - b[m_r]) / delta[m_r])) % 360.0
        h[m_g] = 60.0 * ((b[m_g] - r[m_g]) / delta[m_g] + 2.0)
        h[m_b] = 60.0 * ((r[m_b] - g[m_b]) / delta[m_b] + 4.0)
        return float(h.mean())

    raise ValueError(f"Unknown measurement field: {field!r}")


def _compare(measured: float, operator: str, threshold: float) -> bool:
    if operator == "gt":
        return measured > threshold
    if operator == "gte":
        return measured >= threshold
    if operator == "lt":
        return measured < threshold
    if operator == "lte":
        return measured <= threshold
    if operator == "eq":
        return abs(measured - threshold) < 1e-9
    raise ValueError(f"Unknown operator: {operator!r}")


def _bbox_passes(
    bbox: BBox,
    image: np.ndarray,
    conditions: List[ImageAnalysisCondition],
    logic: str,
) -> bool:
    """Return True if bbox passes all (AND) or any (OR) applicable conditions.

    Conditions with class_name="" apply to every bbox.
    Conditions with a non-empty class_name apply only when it matches bbox.class_name.
    If no conditions are applicable to this bbox's class, the bbox passes through.
    """
    applicable = [
        c for c in conditions
        if c.class_name == "" or c.class_name == bbox.class_name
    ]
    if not applicable:
        return True  # no conditions target this class — pass through

    results = [
        _compare(
            measure_roi(image, bbox, c.field.value),
            c.operator.value,
            c.threshold,
        )
        for c in applicable
    ]

    return all(results) if logic == "AND" else any(results)


# ------------------------------------------------------------------ #
# Node
# ------------------------------------------------------------------ #


@NodeRegistry.register("image_analysis")
class ImageAnalysisNode(BaseNode):
    """Filters AnnotatedFrames by measuring pixel statistics inside BBox ROIs.

    For each frame, each BBox is measured on the configured field (intensity,
    RGB channel, or HSV channel) and compared against the threshold. BBoxes
    that fail are dropped; frames where all BBoxes are dropped are excluded
    from the output AnnotatedStream.

    Input:
        input  (AnnotatedStream) — frames to analyse

    Outputs:
        output (AnnotatedStream) — frames that have ≥1 surviving BBox
        bboxes (BoxStream)       — surviving BBoxes, flattened (optional;
                                   use to connect downstream to Filter/Logic nodes)
    """

    @property
    def input_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition("input", PortType.AnnotatedStream, "Annotated image frames")
        ]

    @property
    def output_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition(
                "output", PortType.AnnotatedStream, "Frames with surviving BBoxes"
            ),
            PortDefinition(
                "bboxes", PortType.BoxStream,
                "Surviving BBoxes, flattened (connects to Filter/Merge/Logic nodes)",
                optional=True,
            ),
        ]

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        frames: List[AnnotatedFrame] = inputs.get("input", [])
        if not frames:
            return {"output": [], "bboxes": []}

        cfg: ImageAnalysisConfig = self._parsed_config  # type: ignore[assignment]
        logic = cfg.logic.value  # "AND" or "OR"

        out_frames: List[AnnotatedFrame] = []
        out_bboxes: List[BBox] = []

        for frame in frames:
            survivors = [
                bbox
                for bbox in frame.bboxes
                if _bbox_passes(bbox, frame.image, cfg.conditions, logic)
            ]
            if survivors:
                out_frames.append(frame.with_bboxes(survivors))
                out_bboxes.extend(survivors)

        return {"output": out_frames, "bboxes": out_bboxes}
