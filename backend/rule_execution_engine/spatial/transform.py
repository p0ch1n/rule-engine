"""Geometric transformation utilities for Object objects."""

from __future__ import annotations

from typing import Dict, List, Optional

from rule_execution_engine.spatial.geometry import Object


def apply_offset(
    obj: Object,
    dx: float = 0.0,
    dy: float = 0.0,
    dw: float = 0.0,
    dh: float = 0.0,
) -> Object:
    """Apply additive offset to a single Object. Returns new Object."""
    return obj.with_offset(dx=dx, dy=dy, dw=dw, dh=dh)


def apply_scale(
    obj: Object,
    sx: float = 1.0,
    sy: float = 1.0,
    sw: float = 1.0,
    sh: float = 1.0,
) -> Object:
    """Apply multiplicative scale to a single Object. Returns new Object."""
    return obj.with_scale(sx=sx, sy=sy, sw=sw, sh=sh)


def expand_by_ratio(obj: Object, ratio: float) -> Object:
    """Expand Object dimensions symmetrically by `ratio` factor (centroid-preserving).

    ratio=1.1 → 10% larger in all dimensions.
    """
    new_w = obj.w * ratio
    new_h = obj.h * ratio
    new_x = obj.cx - new_w / 2
    new_y = obj.cy - new_h / 2
    return Object(
        x=new_x,
        y=new_y,
        w=new_w,
        h=new_h,
        confidence=obj.confidence,
        class_name=obj.class_name,
        metadata=obj.metadata,
    )


def clip_to_frame(obj: Object, frame_w: float, frame_h: float) -> Object:
    """Clip Object coordinates to frame boundaries. Returns new Object."""
    x = max(0.0, min(obj.x, frame_w))
    y = max(0.0, min(obj.y, frame_h))
    x2 = max(0.0, min(obj.x2, frame_w))
    y2 = max(0.0, min(obj.y2, frame_h))
    return Object(
        x=x,
        y=y,
        w=x2 - x,
        h=y2 - y,
        confidence=obj.confidence,
        class_name=obj.class_name,
        metadata=obj.metadata,
    )


def top_k_by_confidence(boxes: List[Object], k: int) -> List[Object]:
    """Return up to k Objects sorted by confidence descending."""
    sorted_boxes = sorted(boxes, key=lambda b: b.confidence, reverse=True)
    return sorted_boxes[:k]


def apply_offset_config(obj: Object, offset_cfg: Optional[Dict]) -> Object:
    """Apply offset from a config dict {'dx':0,'dy':0,'dw':0,'dh':0}."""
    if offset_cfg is None:
        return obj
    return obj.with_offset(
        dx=offset_cfg.get("dx", 0.0),
        dy=offset_cfg.get("dy", 0.0),
        dw=offset_cfg.get("dw", 0.0),
        dh=offset_cfg.get("dh", 0.0),
    )


def apply_scale_config(obj: Object, scale_cfg: Optional[Dict]) -> Object:
    """Apply scale from a config dict {'sx':1,'sy':1,'sw':1,'sh':1}."""
    if scale_cfg is None:
        return obj
    return obj.with_scale(
        sx=scale_cfg.get("sx", 1.0),
        sy=scale_cfg.get("sy", 1.0),
        sw=scale_cfg.get("sw", 1.0),
        sh=scale_cfg.get("sh", 1.0),
    )
