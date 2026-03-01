"""Core geometry primitives for bounding box processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class BBox:
    """Immutable bounding box in (x, y, w, h) absolute-pixel format.

    x, y — top-left corner coordinates.
    w, h — width and height.
    confidence — detector confidence score [0, 1].
    class_name — object class label.
    metadata — arbitrary key/value pairs preserved through the pipeline
               (e.g. source node_id for lineage tracking).
    """

    x: float
    y: float
    w: float
    h: float
    confidence: float
    class_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Derived geometric properties
    # ------------------------------------------------------------------ #

    @property
    def x2(self) -> float:
        """Right edge coordinate."""
        return self.x + self.w

    @property
    def y2(self) -> float:
        """Bottom edge coordinate."""
        return self.y + self.h

    @property
    def area(self) -> float:
        """Bounding box area in pixels²."""
        return self.w * self.h

    @property
    def cx(self) -> float:
        """Centroid x coordinate."""
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        """Centroid y coordinate."""
        return self.y + self.h / 2

    # ------------------------------------------------------------------ #
    # Transformation helpers (return new instances — immutable pattern)
    # ------------------------------------------------------------------ #

    def with_offset(
        self,
        dx: float = 0.0,
        dy: float = 0.0,
        dw: float = 0.0,
        dh: float = 0.0,
    ) -> "BBox":
        """Return a new BBox with additive offsets applied."""
        return BBox(
            x=self.x + dx,
            y=self.y + dy,
            w=max(0.0, self.w + dw),
            h=max(0.0, self.h + dh),
            confidence=self.confidence,
            class_name=self.class_name,
            metadata=self.metadata,
        )

    def with_scale(
        self,
        sx: float = 1.0,
        sy: float = 1.0,
        sw: float = 1.0,
        sh: float = 1.0,
    ) -> "BBox":
        """Return a new BBox with multiplicative scale applied to each dimension.

        Scaling is centroid-preserving for sx/sy (position scale),
        and independent for sw/sh (size scale).
        """
        new_w = max(0.0, self.w * sw)
        new_h = max(0.0, self.h * sh)
        new_x = self.cx * sx - new_w / 2
        new_y = self.cy * sy - new_h / 2
        return BBox(
            x=new_x,
            y=new_y,
            w=new_w,
            h=new_h,
            confidence=self.confidence,
            class_name=self.class_name,
            metadata=self.metadata,
        )

    def with_metadata(self, **kwargs: Any) -> "BBox":
        """Return a new BBox with additional metadata merged in."""
        return BBox(
            x=self.x,
            y=self.y,
            w=self.w,
            h=self.h,
            confidence=self.confidence,
            class_name=self.class_name,
            metadata={**self.metadata, **kwargs},
        )

    def with_class(self, class_name: str) -> "BBox":
        """Return a new BBox with a different class label."""
        return BBox(
            x=self.x,
            y=self.y,
            w=self.w,
            h=self.h,
            confidence=self.confidence,
            class_name=class_name,
            metadata=self.metadata,
        )

    def union_bbox(self, other: "BBox") -> "BBox":
        """Return the axis-aligned bounding box that encloses both boxes."""
        x1 = min(self.x, other.x)
        y1 = min(self.y, other.y)
        x2 = max(self.x2, other.x2)
        y2 = max(self.y2, other.y2)
        confidence = max(self.confidence, other.confidence)
        return BBox(
            x=x1,
            y=y1,
            w=x2 - x1,
            h=y2 - y1,
            confidence=confidence,
            class_name=f"{self.class_name}+{other.class_name}",
            metadata={},
        )

    def __repr__(self) -> str:
        return (
            f"BBox(cls={self.class_name!r}, "
            f"x={self.x:.1f}, y={self.y:.1f}, "
            f"w={self.w:.1f}, h={self.h:.1f}, "
            f"conf={self.confidence:.3f})"
        )
