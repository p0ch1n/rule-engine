"""RF-DETR detector implementation (requires rfdetr + supervision)."""

from __future__ import annotations

from typing import Any, List

import numpy as np

from rule_execution_engine.detectors.base import BaseDetector
from rule_execution_engine.detectors.registry import DetectorRegistry
from rule_execution_engine.spatial.geometry import Object


@DetectorRegistry.register("rf_detr")
class RFDETRDetector(BaseDetector):
    """Runs RF-DETR inference via the rfdetr package (Roboflow).

    Install: pip install rfdetr supervision

    Note: RF-DETR is a transformer-based detector and does not use NMS.
    The nms_threshold parameter is accepted for API parity but has no effect.
    """

    def _load_model(self) -> Any:
        try:
            from rfdetr import RFDETRBase
        except ImportError as exc:
            raise ImportError(
                "rfdetr is required for RF-DETR inference. "
                "Install with: pip install rfdetr supervision"
            ) from exc
        model = RFDETRBase(pretrain_weights=self._model_path)
        if self._device == "cuda":
            try:
                import torch

                model = model.to(torch.device("cuda"))
            except ImportError as exc:
                raise ImportError(
                    "torch is required for CUDA inference. "
                    "Install with: pip install torch --index-url https://download.pytorch.org/whl/cu121"
                ) from exc
        return model

    def _run_inference(
        self,
        images: List[np.ndarray],
        confidence_threshold: float,
        nms_threshold: float,  # not used by transformer models
    ) -> List[List[Object]]:
        all_results: List[List[Object]] = []
        for image in images:
            detections = self._model.predict(image, threshold=confidence_threshold)
            objects: List[Object] = []
            if detections is not None and len(detections):
                class_names = detections.data.get("class_name", [])
                for i in range(len(detections)):
                    x1, y1, x2, y2 = detections.xyxy[i].tolist()
                    if i < len(class_names):
                        class_name = str(class_names[i])
                    else:
                        class_name = str(int(detections.class_id[i]))
                    objects.append(
                        Object(
                            x=x1,
                            y=y1,
                            w=x2 - x1,
                            h=y2 - y1,
                            confidence=float(detections.confidence[i]),
                            class_name=class_name,
                        )
                    )
            all_results.append(objects)
        return all_results
