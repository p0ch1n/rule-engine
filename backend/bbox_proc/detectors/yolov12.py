"""YOLOv12 detector implementation (requires ultralytics)."""

from __future__ import annotations

from typing import Any, List

import numpy as np

from bbox_proc.detectors.base import BaseDetector
from bbox_proc.detectors.registry import DetectorRegistry
from bbox_proc.spatial.geometry import BBox


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
    ) -> List[List[BBox]]:
        results = self._model(
            images,
            conf=confidence_threshold,
            iou=nms_threshold,
            device=self._device,
            verbose=False,
        )
        all_results: List[List[BBox]] = []
        for result in results:
            bboxes: List[BBox] = []
            boxes = result.boxes
            if boxes is not None and len(boxes):
                for xyxy, conf, cls_idx in zip(
                    boxes.xyxy.tolist(),
                    boxes.conf.tolist(),
                    boxes.cls.tolist(),
                ):
                    x1, y1, x2, y2 = xyxy
                    bboxes.append(
                        BBox(
                            x=x1,
                            y=y1,
                            w=x2 - x1,
                            h=y2 - y1,
                            confidence=float(conf),
                            class_name=result.names[int(cls_idx)],
                        )
                    )
            all_results.append(bboxes)
        return all_results
