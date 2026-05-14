"""DetectionNode — source node that runs a detection model on input images."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from rule_execution_engine.detectors.base import BaseDetector
from rule_execution_engine.detectors.catalog import ModelCatalog
from rule_execution_engine.detectors.registry import DetectorRegistry
from rule_execution_engine.nodes.base import BaseNode, PortDefinition, PortType
from rule_execution_engine.nodes.registry import NodeRegistry
from rule_execution_engine.spatial.annotated import AnnotatedFrame


# ------------------------------------------------------------------ #
# Config schema
# ------------------------------------------------------------------ #


class DetectionConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    architecture: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    nms_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    device: Literal["cpu", "cuda"] = "cpu"


@NodeRegistry.register("detection", config_class=DetectionConfig)
class DetectionNode(BaseNode):
    """Source node: runs an object detection model on input images.

    Input:  ImageStream      — List[np.ndarray] (one array per frame)
    Output `output`    (ObjectStream)      — all detected Objects, flattened across frames
    Output `annotated` (AnnotatedStream) — List[AnnotatedFrame], image + per-frame Objects

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
            PortDefinition("output", PortType.ObjectStream, "Detected Objects (flattened)"),
            PortDefinition(
                "annotated", PortType.AnnotatedStream,
                "Image + per-frame Object pairs (connect to ImageAnalysisNode)",
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

        all_objects = [obj for frame_objects in per_frame for obj in frame_objects]
        annotated = [
            AnnotatedFrame(image=img, objects=objects)
            for img, objects in zip(images, per_frame)
        ]
        return {"output": all_objects, "annotated": annotated}

    def _get_detector(self, cfg: DetectionConfig) -> BaseDetector:
        if self._detector is None:
            model_path = ModelCatalog.get_model_path(cfg.architecture, cfg.model_name)
            self._detector = DetectorRegistry.create(
                cfg.architecture, model_path, cfg.device
            )
        return self._detector
