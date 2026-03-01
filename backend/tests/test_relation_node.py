"""Tests for RelationNode."""

import pytest

from bbox_proc.nodes import RelationNode
from bbox_proc.schema.models import NodeConfig
from bbox_proc.spatial.geometry import BBox


def make_relation_config(
    mode="self_join",
    relation_type="iou",
    threshold=0.3,
    offset=None,
    scale=None,
):
    cfg = {
        "mode": mode,
        "relation_type": relation_type,
        "threshold": threshold,
    }
    if offset:
        cfg["offset"] = offset
    if scale:
        cfg["scale"] = scale
    return NodeConfig(
        id="relation-test",
        type="relation",
        position={"x": 0, "y": 0},
        config=cfg,
    )


def make_bbox(x=0, y=0, w=10, h=10, conf=0.9, cls="person"):
    return BBox(x=x, y=y, w=w, h=h, confidence=conf, class_name=cls)


class TestRelationNode:
    def test_self_join_overlapping(self):
        """Two overlapping boxes in self-join → one relation bbox."""
        node = RelationNode(make_relation_config(mode="self_join", threshold=0.1))
        b1 = make_bbox(x=0, y=0, w=10, h=10)
        b2 = make_bbox(x=5, y=0, w=10, h=10)
        result = node.execute({"input": [b1, b2]})
        assert len(result["output"]) == 1

    def test_self_join_non_overlapping(self):
        """Two non-overlapping boxes → no relation bbox."""
        node = RelationNode(make_relation_config(mode="self_join", threshold=0.1))
        b1 = make_bbox(x=0, y=0, w=5, h=5)
        b2 = make_bbox(x=100, y=100, w=5, h=5)
        result = node.execute({"input": [b1, b2]})
        assert len(result["output"]) == 0

    def test_self_join_no_self_pairs(self):
        """Single box in self-join → no relation (can't pair with itself)."""
        node = RelationNode(make_relation_config(mode="self_join", threshold=0.0))
        b = make_bbox(x=0, y=0, w=10, h=10)
        result = node.execute({"input": [b]})
        assert len(result["output"]) == 0

    def test_cross_join(self):
        node = RelationNode(make_relation_config(mode="cross_join", threshold=0.1))
        b1 = make_bbox(x=0, y=0, w=10, h=10, cls="person")
        b2 = make_bbox(x=5, y=0, w=10, h=10, cls="car")
        result = node.execute({"input": [b1], "input_b": [b2]})
        assert len(result["output"]) == 1
        rel = result["output"][0]
        assert rel.metadata["source_a_class"] == "person"
        assert rel.metadata["source_b_class"] == "car"

    def test_relation_metadata(self):
        node = RelationNode(make_relation_config(mode="self_join", threshold=0.1))
        b1 = make_bbox(x=0, y=0, w=10, h=10)
        b2 = make_bbox(x=5, y=0, w=10, h=10)
        result = node.execute({"input": [b1, b2]})
        rel = result["output"][0]
        assert "relation_type" in rel.metadata
        assert "relation_node" in rel.metadata

    def test_offset_applied(self):
        """Offset should shift the output relation bbox."""
        node = RelationNode(
            make_relation_config(
                mode="self_join",
                threshold=0.1,
                offset={"dx": 10, "dy": 0, "dw": 0, "dh": 0},
            )
        )
        b1 = make_bbox(x=0, y=0, w=10, h=10)
        b2 = make_bbox(x=5, y=0, w=10, h=10)
        result = node.execute({"input": [b1, b2]})
        rel = result["output"][0]
        # Union bbox x=0, after dx=10 → x=10
        assert rel.x == pytest.approx(10)

    def test_distance_mode(self):
        node = RelationNode(
            make_relation_config(
                mode="cross_join", relation_type="centroid_distance", threshold=50
            )
        )
        b1 = make_bbox(x=0, y=0, w=0, h=0)
        b2 = make_bbox(x=3, y=4, w=0, h=0)  # dist = 5
        b3 = make_bbox(x=100, y=100, w=0, h=0)  # dist ≈ 141
        result = node.execute({"input": [b1], "input_b": [b2, b3]})
        # Only b1-b2 qualifies
        assert len(result["output"]) == 1

    def test_empty_inputs(self):
        node = RelationNode(make_relation_config())
        result = node.execute({"input": []})
        assert result["output"] == []
