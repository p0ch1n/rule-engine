"""Abstract base class for all object detectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional

import numpy as np

from bbox_proc.spatial.geometry import BBox


class BaseDetector(ABC):
    """Lazy-loading detector base.

    Subclasses implement `_load_model` and `_run_inference`.
    The model is loaded on the first `detect()` call and reused thereafter.
    """

    def __init__(self, model_path: str, device: str) -> None:
        self._model_path = model_path
        self._device = device
        self._model: Optional[Any] = None

    def _ensure_loaded(self) -> None:
        if self._model is None:
            self._model = self._load_model()

    @abstractmethod
    def _load_model(self) -> Any:
        """Load and return the model object."""
        ...

    @abstractmethod
    def _run_inference(
        self,
        images: List[np.ndarray],
        confidence_threshold: float,
        nms_threshold: float,
    ) -> List[List[BBox]]:
        """Run inference on a batch. Returns one List[BBox] per image."""
        ...

    def detect(
        self,
        images: List[np.ndarray],
        confidence_threshold: float = 0.5,
        nms_threshold: float = 0.45,
    ) -> List[List[BBox]]:
        """Detect objects in a batch of images."""
        self._ensure_loaded()
        return self._run_inference(images, confidence_threshold, nms_threshold)
