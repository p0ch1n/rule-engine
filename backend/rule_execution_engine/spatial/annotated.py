"""AnnotatedFrame — an image paired with its detected bounding boxes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np

from rule_execution_engine.spatial.geometry import Object


@dataclass
class AnnotatedFrame:
    """An image frame paired with its associated bounding boxes.

    Passed through the pipeline on AnnotatedStream ports so that
    downstream nodes (e.g. ImageAnalysisNode) can inspect pixel values
    inside each Object ROI.

    Channel order follows the convention used by the caller:
    typically BGR for OpenCV pipelines. ImageAnalysisNode assumes BGR
    (index 0 = Blue, 1 = Green, 2 = Red).

    The image is never copied when creating derived frames — callers share
    the same array reference to avoid large memory allocations.
    """

    image: np.ndarray
    objects: List[Object] = field(default_factory=list)

    def with_objects(self, objects: List[Object]) -> "AnnotatedFrame":
        """Return a new AnnotatedFrame with the same image but a new obj list."""
        return AnnotatedFrame(image=self.image, objects=list(objects))

    def __repr__(self) -> str:
        h, w = self.image.shape[:2] if self.image.ndim >= 2 else (0, 0)
        return f"AnnotatedFrame(size={w}x{h}, objects={len(self.objects)})"
