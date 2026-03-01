"""Tests for spatial geometry, IoU, and transform modules."""

import math

import pytest

from bbox_proc.spatial.geometry import BBox
from bbox_proc.spatial.iou import (
    centroid_distance_matrix,
    iou_matrix,
    iou_single,
    pairs_exceeding_iou,
    pairs_within_distance,
)
from bbox_proc.spatial.transform import (
    apply_offset,
    apply_scale,
    clip_to_frame,
    expand_by_ratio,
    top_k_by_confidence,
)


# ------------------------------------------------------------------ #
# BBox geometry
# ------------------------------------------------------------------ #


def make_box(x=0, y=0, w=10, h=10, conf=0.9, cls="person"):
    return BBox(x=x, y=y, w=w, h=h, confidence=conf, class_name=cls)


class TestBBox:
    def test_derived_properties(self):
        b = make_box(x=5, y=10, w=20, h=30)
        assert b.x2 == 25
        assert b.y2 == 40
        assert b.area == 600
        assert b.cx == 15
        assert b.cy == 25

    def test_with_offset_returns_new(self):
        b = make_box(x=0, y=0, w=10, h=10)
        b2 = b.with_offset(dx=5, dy=5, dw=2, dh=2)
        assert b.x == 0  # original unchanged
        assert b2.x == 5
        assert b2.w == 12

    def test_with_offset_clamps_width_height(self):
        b = make_box(w=5, h=5)
        b2 = b.with_offset(dw=-100, dh=-100)
        assert b2.w == 0
        assert b2.h == 0

    def test_with_scale(self):
        b = make_box(x=40, y=40, w=20, h=20)  # cx=50, cy=50
        b2 = b.with_scale(sw=2.0, sh=2.0)
        assert b2.w == pytest.approx(40)
        assert b2.h == pytest.approx(40)
        # centroid should stay same
        assert b2.cx == pytest.approx(50)
        assert b2.cy == pytest.approx(50)

    def test_with_metadata_immutable(self):
        b = make_box()
        b2 = b.with_metadata(source="test")
        assert "source" not in b.metadata
        assert b2.metadata["source"] == "test"

    def test_union_bbox(self):
        b1 = make_box(x=0, y=0, w=10, h=10)
        b2 = make_box(x=5, y=5, w=10, h=10)
        union = b1.union_bbox(b2)
        assert union.x == 0
        assert union.y == 0
        assert union.x2 == 15
        assert union.y2 == 15

    def test_frozen_raises_on_mutation(self):
        b = make_box()
        with pytest.raises((AttributeError, TypeError)):
            b.x = 99  # type: ignore


# ------------------------------------------------------------------ #
# IoU computation
# ------------------------------------------------------------------ #


class TestIoU:
    def test_full_overlap(self):
        b = make_box(x=0, y=0, w=10, h=10)
        assert iou_single(b, b) == pytest.approx(1.0)

    def test_no_overlap(self):
        b1 = make_box(x=0, y=0, w=5, h=5)
        b2 = make_box(x=10, y=10, w=5, h=5)
        assert iou_single(b1, b2) == pytest.approx(0.0)

    def test_partial_overlap(self):
        # Two 10x10 boxes overlapping 5x10 = 50 / (100+100-50) = 50/150 ≈ 0.333
        b1 = make_box(x=0, y=0, w=10, h=10)
        b2 = make_box(x=5, y=0, w=10, h=10)
        result = iou_single(b1, b2)
        assert result == pytest.approx(50 / 150, rel=1e-5)

    def test_matrix_shape(self):
        boxes_a = [make_box() for _ in range(3)]
        boxes_b = [make_box() for _ in range(5)]
        m = iou_matrix(boxes_a, boxes_b)
        assert m.shape == (3, 5)

    def test_matrix_empty(self):
        m = iou_matrix([], [])
        assert m.shape == (0, 0)

    def test_pairs_exceeding_iou(self):
        b1 = make_box(x=0, y=0, w=10, h=10)
        b2 = make_box(x=5, y=0, w=10, h=10)
        b3 = make_box(x=100, y=100, w=10, h=10)
        pairs = pairs_exceeding_iou([b1], [b2, b3], threshold=0.1)
        # b1 vs b2 qualifies; b1 vs b3 does not
        assert (0, 0) in pairs
        assert (0, 1) not in pairs


# ------------------------------------------------------------------ #
# Centroid distance
# ------------------------------------------------------------------ #


class TestCentroidDistance:
    def test_same_box(self):
        b = make_box(x=0, y=0, w=10, h=10)  # cx=5, cy=5
        m = centroid_distance_matrix([b], [b])
        assert m[0, 0] == pytest.approx(0.0)

    def test_known_distance(self):
        b1 = make_box(x=0, y=0, w=0, h=0)  # cx=0
        b2 = make_box(x=3, y=4, w=0, h=0)  # cx=3, cy=4 → dist=5
        m = centroid_distance_matrix([b1], [b2])
        assert m[0, 0] == pytest.approx(5.0)

    def test_pairs_within_distance(self):
        b1 = make_box(x=0, y=0, w=0, h=0)
        b2 = make_box(x=3, y=4, w=0, h=0)  # dist=5
        b3 = make_box(x=100, y=0, w=0, h=0)  # dist=100
        pairs = pairs_within_distance([b1], [b2, b3], threshold=10)
        assert (0, 0) in pairs
        assert (0, 1) not in pairs


# ------------------------------------------------------------------ #
# Transforms
# ------------------------------------------------------------------ #


class TestTransforms:
    def test_apply_offset(self):
        b = make_box(x=10, y=10, w=20, h=20)
        b2 = apply_offset(b, dx=-5, dy=5)
        assert b2.x == 5
        assert b2.y == 15
        assert b2.w == 20

    def test_apply_scale(self):
        b = make_box(x=40, y=40, w=20, h=20)
        b2 = apply_scale(b, sw=1.1, sh=1.1)
        assert b2.w == pytest.approx(22)
        assert b2.h == pytest.approx(22)

    def test_expand_by_ratio(self):
        b = make_box(x=45, y=45, w=10, h=10)  # cx=50, cy=50
        b2 = expand_by_ratio(b, 1.1)
        assert b2.w == pytest.approx(11)
        assert b2.cx == pytest.approx(50)

    def test_clip_to_frame(self):
        b = make_box(x=-10, y=-10, w=200, h=200)
        b2 = clip_to_frame(b, frame_w=100, frame_h=100)
        assert b2.x == 0
        assert b2.y == 0
        assert b2.x2 == 100
        assert b2.y2 == 100

    def test_top_k_by_confidence(self):
        boxes = [make_box(conf=float(i) / 10) for i in range(10)]
        result = top_k_by_confidence(boxes, k=3)
        assert len(result) == 3
        # Should be highest confidence first
        assert result[0].confidence >= result[1].confidence >= result[2].confidence

    def test_top_k_larger_than_list(self):
        boxes = [make_box() for _ in range(3)]
        result = top_k_by_confidence(boxes, k=100)
        assert len(result) == 3
