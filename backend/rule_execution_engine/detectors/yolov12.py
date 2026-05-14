"""YOLOv12 detector implementation (requires ultralytics)."""

from __future__ import annotations

from typing import Any, List

import numpy as np

from rule_execution_engine.detectors.base import BaseDetector
from rule_execution_engine.detectors.registry import DetectorRegistry
from rule_execution_engine.spatial.geometry import Object


@DetectorRegistry.register("yolov12")
class YOLOv12Detector(BaseDetector):
    """Runs YOLOv12 inference via the ultralytics package.

    Install: pip install ultralytics
    """

    def _load_model(self) -> Any:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ImportError(
                "ultralytics is required for YOLOv12 inference. "
                "Install with: pip install ultralytics"
            ) from exc
        return YOLO(self._model_path)

    def _run_inference(
        self,
        images: List[np.ndarray],
        confidence_threshold: float,
        nms_threshold: float,
    ) -> List[List[Object]]:
        results = self._model(
            images,
            conf=confidence_threshold,
            iou=nms_threshold,
            device=self._device,
            verbose=False,
        )
        all_results: List[List[Object]] = []
        for result in results:
            objects: List[Object] = []
            boxes = result.boxes
            if boxes is not None and len(boxes):
                for xyxy, conf, cls_idx in zip(
                    boxes.xyxy.tolist(),
                    boxes.conf.tolist(),
                    boxes.cls.tolist(),
                ):
                    x1, y1, x2, y2 = xyxy
                    objects.append(
                        Object(
                            x=x1,
                            y=y1,
                            w=x2 - x1,
                            h=y2 - y1,
                            confidence=float(conf),
                            class_name=result.names[int(cls_idx)],
                        )
                    )
            all_results.append(objects)
        return all_results
