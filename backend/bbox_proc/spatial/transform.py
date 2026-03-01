"""Geometric transformation utilities for BBox objects."""

from __future__ import annotations

from typing import Dict, List, Optional

from bbox_proc.spatial.geometry import BBox


def apply_offset(
    bbox: BBox,
    dx: float = 0.0,
    dy: float = 0.0,
    dw: float = 0.0,
    dh: float = 0.0,
) -> BBox:
    """Apply additive offset to a single BBox. Returns new BBox."""
    return bbox.with_offset(dx=dx, dy=dy, dw=dw, dh=dh)


def apply_scale(
    bbox: BBox,
    sx: float = 1.0,
    sy: float = 1.0,
    sw: float = 1.0,
    sh: float = 1.0,
) -> BBox:
    """Apply multiplicative scale to a single BBox. Returns new BBox."""
    return bbox.with_scale(sx=sx, sy=sy, sw=sw, sh=sh)


def expand_by_ratio(bbox: BBox, ratio: float) -> BBox:
    """Expand BBox dimensions symmetrically by `ratio` factor (centroid-preserving).

    ratio=1.1 → 10% larger in all dimensions.
    """
    new_w = bbox.w * ratio
    new_h = bbox.h * ratio
    new_x = bbox.cx - new_w / 2
    new_y = bbox.cy - new_h / 2
    return BBox(
        x=new_x,
        y=new_y,
        w=new_w,
        h=new_h,
        confidence=bbox.confidence,
        class_name=bbox.class_name,
        metadata=bbox.metadata,
    )


def clip_to_frame(bbox: BBox, frame_w: float, frame_h: float) -> BBox:
    """Clip BBox coordinates to frame boundaries. Returns new BBox."""
    x = max(0.0, min(bbox.x, frame_w))
    y = max(0.0, min(bbox.y, frame_h))
    x2 = max(0.0, min(bbox.x2, frame_w))
    y2 = max(0.0, min(bbox.y2, frame_h))
    return BBox(
        x=x,
        y=y,
        w=x2 - x,
        h=y2 - y,
        confidence=bbox.confidence,
        class_name=bbox.class_name,
        metadata=bbox.metadata,
    )


def top_k_by_confidence(boxes: List[BBox], k: int) -> List[BBox]:
    """Return up to k BBoxes sorted by confidence descending."""
    sorted_boxes = sorted(boxes, key=lambda b: b.confidence, reverse=True)
    return sorted_boxes[:k]


def apply_offset_config(bbox: BBox, offset_cfg: Optional[Dict]) -> BBox:
    """Apply offset from a config dict {'dx':0,'dy':0,'dw':0,'dh':0}."""
    if offset_cfg is None:
        return bbox
    return bbox.with_offset(
        dx=offset_cfg.get("dx", 0.0),
        dy=offset_cfg.get("dy", 0.0),
        dw=offset_cfg.get("dw", 0.0),
        dh=offset_cfg.get("dh", 0.0),
    )


def apply_scale_config(bbox: BBox, scale_cfg: Optional[Dict]) -> BBox:
    """Apply scale from a config dict {'sx':1,'sy':1,'sw':1,'sh':1}."""
    if scale_cfg is None:
        return bbox
    return bbox.with_scale(
        sx=scale_cfg.get("sx", 1.0),
        sy=scale_cfg.get("sy", 1.0),
        sw=scale_cfg.get("sw", 1.0),
        sh=scale_cfg.get("sh", 1.0),
    )
