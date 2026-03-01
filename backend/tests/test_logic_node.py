"""Tests for LogicNode."""

import pytest

from bbox_proc.nodes import LogicNode
from bbox_proc.schema.models import NodeConfig
from bbox_proc.spatial.geometry import BBox


def make_logic_config(operation="AND", conditions=None, trigger_label="alert"):
    if conditions is None:
        conditions = [{"class_name": "person", "min_count": 1}]
    return NodeConfig(
        id="logic-test",
        type="logic",
        position={"x": 0, "y": 0},
        config={
            "operation": operation,
            "conditions": conditions,
            "trigger_label": trigger_label,
        },
    )


def make_bbox(cls="person", conf=0.9):
    return BBox(x=0, y=0, w=10, h=10, confidence=conf, class_name=cls)


class TestLogicNode:
    def test_and_both_present_triggers(self):
        node = LogicNode(
            make_logic_config(
                operation="AND",
                conditions=[
                    {"class_name": "person", "min_count": 1},
                    {"class_name": "car", "min_count": 1},
                ],
            )
        )
        boxes = [make_bbox("person"), make_bbox("car")]
        result = node.execute({"input": boxes})
        signal = result["signal"]
        assert signal["triggered"] is True
        assert "person" in signal["matched_classes"]
        assert "car" in signal["matched_classes"]

    def test_and_one_missing_does_not_trigger(self):
        node = LogicNode(
            make_logic_config(
                operation="AND",
                conditions=[
                    {"class_name": "person", "min_count": 1},
                    {"class_name": "car", "min_count": 1},
                ],
            )
        )
        boxes = [make_bbox("person")]
        result = node.execute({"input": boxes})
        assert result["signal"]["triggered"] is False

    def test_or_one_present_triggers(self):
        node = LogicNode(
            make_logic_config(
                operation="OR",
                conditions=[
                    {"class_name": "person", "min_count": 1},
                    {"class_name": "car", "min_count": 1},
                ],
            )
        )
        boxes = [make_bbox("truck")]  # neither person nor car
        result = node.execute({"input": boxes})
        assert result["signal"]["triggered"] is False

        boxes2 = [make_bbox("person")]
        result2 = node.execute({"input": boxes2})
        assert result2["signal"]["triggered"] is True

    def test_min_count_respected(self):
        node = LogicNode(
            make_logic_config(
                operation="AND",
                conditions=[{"class_name": "person", "min_count": 3}],
            )
        )
        result = node.execute({"input": [make_bbox("person"), make_bbox("person")]})
        assert result["signal"]["triggered"] is False

        result2 = node.execute(
            {"input": [make_bbox("person"), make_bbox("person"), make_bbox("person")]}
        )
        assert result2["signal"]["triggered"] is True

    def test_trigger_label_in_signal(self):
        node = LogicNode(make_logic_config(trigger_label="zone-alert"))
        result = node.execute({"input": [make_bbox("person")]})
        assert result["signal"]["label"] == "zone-alert"

    def test_empty_input_does_not_trigger(self):
        node = LogicNode(make_logic_config())
        result = node.execute({"input": []})
        assert result["signal"]["triggered"] is False

    def test_total_count_in_signal(self):
        node = LogicNode(make_logic_config())
        boxes = [make_bbox("person")] * 5
        result = node.execute({"input": boxes})
        assert result["signal"]["total_count"] == 5

    def test_port_definitions(self):
        node = LogicNode(make_logic_config())
        assert any(p.name == "input" for p in node.input_ports)
        assert any(p.name == "signal" for p in node.output_ports)
