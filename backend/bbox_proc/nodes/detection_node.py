"""DetectionNode — source node that runs a detection model on input images."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from bbox_proc.detectors.base import BaseDetector
from bbox_proc.detectors.catalog import ModelCatalog
from bbox_proc.detectors.registry import DetectorRegistry
from bbox_proc.nodes.base import BaseNode, PortDefinition, PortType
from bbox_proc.nodes.registry import NodeRegistry
from bbox_proc.schema.models import DetectionConfig
from bbox_proc.spatial.annotated import AnnotatedFrame


@NodeRegistry.register("detection")
class DetectionNode(BaseNode):
    """Source node: runs an object detection model on input images.

    Input:  ImageStream      — List[np.ndarray] (one array per frame)
    Output `output`    (BoxStream)      — all detected BBoxes, flattened across frames
    Output `annotated` (AnnotatedStream) — List[AnnotatedFrame], image + per-frame BBoxes

    The detector is loaded lazily on the first execute() call and reused
    for subsequent frames. Use `annotated` to connect to ImageAnalysisNode;
    use `output` to connect directly to FilterNode, MergeNode, etc.
    """

    def __init__(self, config: Any) -> None:
        super().__init__(config)
        self._detector: Optional[BaseDetector] = None

    @property
    def input_ports(self) -> List[PortDefinition]:
        return [PortDefinition("input", PortType.ImageStream, "Input image frames")]

    @property
    def output_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition("output", PortType.BoxStream, "Detected BBoxes (flattened)"),
            PortDefinition(
                "annotated", PortType.AnnotatedStream,
                "Image + per-frame BBox pairs (connect to ImageAnalysisNode)",
                optional=True,
            ),
        ]

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        images: List[np.ndarray] = inputs.get("input", [])
        if not images:
            return {"output": [], "annotated": []}

        cfg: DetectionConfig = self._parsed_config  # type: ignore[assignment]
        detector = self._get_detector(cfg)
        per_frame = detector.detect(images, cfg.confidence_threshold, cfg.nms_threshold)

        all_bboxes = [bbox for frame_bboxes in per_frame for bbox in frame_bboxes]
        annotated = [
            AnnotatedFrame(image=img, bboxes=bboxes)
            for img, bboxes in zip(images, per_frame)
        ]
        return {"output": all_bboxes, "annotated": annotated}

    def _get_detector(self, cfg: DetectionConfig) -> BaseDetector:
        if self._detector is None:
            model_path = ModelCatalog.get_model_path(cfg.architecture, cfg.model_name)
            self._detector = DetectorRegistry.create(
                cfg.architecture, model_path, cfg.device
            )
        return self._detector
