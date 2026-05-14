"""Tests for FilterNode — single and multi-condition."""

import pytest

from rule_execution_engine.nodes import FilterNode
from rule_execution_engine.schema.models import NodeConfig
from rule_execution_engine.spatial.geometry import Object


def make_node_config(config: dict) -> NodeConfig:
    return NodeConfig(
        id="filter-test",
        type="filter",
        position={"x": 0, "y": 0},
        config=config,
    )


def single_cond(class_name="person", field="confidence", operator="gt", threshold=0.5):
    """Helper: build a FilterConfig with a single condition."""
    return {
        "conditions": [
            {"class_name": class_name, "field": field, "operator": operator, "threshold": threshold}
        ],
        "logic": "AND",
    }


def make_obj(cls="person", conf=0.8, w=50.0, h=100.0):
    return Object(x=0, y=0, w=w, h=h, confidence=conf, class_name=cls)


# ------------------------------------------------------------------ #
# Single-condition behaviour (backward-compatible)
# ------------------------------------------------------------------ #

class TestFilterNodeSingleCondition:
    def test_pass_high_confidence(self):
        node = FilterNode(make_node_config(single_cond(operator="gt", threshold=0.5)))
        box = make_obj(cls="person", conf=0.9)
        result = node.execute({"input": [box]})
        assert box in result["output"]
        assert box not in result["rejected"]

    def test_reject_low_confidence(self):
        node = FilterNode(make_node_config(single_cond(operator="gt", threshold=0.5)))
        box = make_obj(cls="person", conf=0.3)
        result = node.execute({"input": [box]})
        assert box not in result["output"]
        assert box in result["rejected"]

    def test_different_class_passes_through(self):
        node = FilterNode(make_node_config(single_cond(class_name="person")))
        car = make_obj(cls="car", conf=0.1)
        result = node.execute({"input": [car]})
        assert car in result["output"]

    def test_width_filter(self):
        node = FilterNode(make_node_config(single_cond(field="width", operator="gte", threshold=50)))
        wide = make_obj(cls="person", w=60)
        narrow = make_obj(cls="person", w=30)
        result = node.execute({"input": [wide, narrow]})
        assert wide in result["output"]
        assert narrow in result["rejected"]

    def test_area_filter(self):
        node = FilterNode(make_node_config(
            {"conditions": [{"class_name": "car", "field": "area", "operator": "gt", "threshold": 1000}], "logic": "AND"}
        ))
        big   = Object(x=0, y=0, w=50, h=50, confidence=0.9, class_name="car")   # area=2500
        small = Object(x=0, y=0, w=10, h=10, confidence=0.9, class_name="car")   # area=100
        result = node.execute({"input": [big, small]})
        assert big in result["output"]
        assert small in result["rejected"]

    def test_empty_input(self):
        node = FilterNode(make_node_config(single_cond()))
        result = node.execute({"input": []})
        assert result["output"] == []
        assert result["rejected"] == []

    def test_eq_operator(self):
        node = FilterNode(make_node_config(single_cond(operator="eq", threshold=0.8)))
        exact = make_obj(conf=0.8)
        other = make_obj(conf=0.7)
        result = node.execute({"input": [exact, other]})
        assert exact in result["output"]
        assert other in result["rejected"]

    def test_port_definitions(self):
        node = FilterNode(make_node_config(single_cond()))
        assert len(node.input_ports) == 1
        assert len(node.output_ports) == 2


# ------------------------------------------------------------------ #
# Multi-condition AND logic
# ------------------------------------------------------------------ #

class TestFilterNodeAndLogic:
    def test_and_both_conditions_must_pass(self):
        """Person must have conf > 0.5 AND height > 80."""
        node = FilterNode(make_node_config({
            "conditions": [
                {"class_name": "person", "field": "confidence", "operator": "gt", "threshold": 0.5},
                {"class_name": "person", "field": "height",     "operator": "gt", "threshold": 80},
            ],
            "logic": "AND",
        }))
        passes  = Object(x=0, y=0, w=20, h=100, confidence=0.9, class_name="person")
        low_h   = Object(x=0, y=0, w=20, h=50,  confidence=0.9, class_name="person")
        low_c   = Object(x=0, y=0, w=20, h=100, confidence=0.3, class_name="person")
        both_no = Object(x=0, y=0, w=20, h=50,  confidence=0.3, class_name="person")

        result = node.execute({"input": [passes, low_h, low_c, both_no]})
        assert passes  in result["output"]
        assert low_h   in result["rejected"]
        assert low_c   in result["rejected"]
        assert both_no in result["rejected"]

    def test_and_different_classes_independent(self):
        """Conditions for different classes are evaluated independently."""
        node = FilterNode(make_node_config({
            "conditions": [
                {"class_name": "person", "field": "confidence", "operator": "gt", "threshold": 0.7},
                {"class_name": "car",    "field": "confidence", "operator": "gt", "threshold": 0.6},
            ],
            "logic": "AND",
        }))
        good_person = make_obj(cls="person", conf=0.9)
        bad_person  = make_obj(cls="person", conf=0.5)
        good_car    = make_obj(cls="car",    conf=0.8)
        bad_car     = make_obj(cls="car",    conf=0.4)
        truck       = make_obj(cls="truck",  conf=0.1)  # no condition → pass through

        result = node.execute({"input": [good_person, bad_person, good_car, bad_car, truck]})
        assert good_person in result["output"]
        assert bad_person  in result["rejected"]
        assert good_car    in result["output"]
        assert bad_car     in result["rejected"]
        assert truck       in result["output"]  # pass through


# ------------------------------------------------------------------ #
# Multi-condition OR logic
# ------------------------------------------------------------------ #

class TestFilterNodeOrLogic:
    def test_or_any_condition_passes(self):
        """Person passes if conf > 0.7 OR height > 80."""
        node = FilterNode(make_node_config({
            "conditions": [
                {"class_name": "person", "field": "confidence", "operator": "gt", "threshold": 0.7},
                {"class_name": "person", "field": "height",     "operator": "gt", "threshold": 80},
            ],
            "logic": "OR",
        }))
        high_conf_only = Object(x=0, y=0, w=20, h=50,  confidence=0.9, class_name="person")
        tall_only      = Object(x=0, y=0, w=20, h=100, confidence=0.3, class_name="person")
        both_pass      = Object(x=0, y=0, w=20, h=100, confidence=0.9, class_name="person")
        neither        = Object(x=0, y=0, w=20, h=50,  confidence=0.3, class_name="person")

        result = node.execute({"input": [high_conf_only, tall_only, both_pass, neither]})
        assert high_conf_only in result["output"]
        assert tall_only      in result["output"]
        assert both_pass      in result["output"]
        assert neither        in result["rejected"]

    def test_or_all_fail_goes_to_rejected(self):
        node = FilterNode(make_node_config({
            "conditions": [
                {"class_name": "car", "field": "confidence", "operator": "gt", "threshold": 0.9},
                {"class_name": "car", "field": "width",      "operator": "gt", "threshold": 100},
            ],
            "logic": "OR",
        }))
        tiny_low = Object(x=0, y=0, w=10, h=10, confidence=0.5, class_name="car")
        result   = node.execute({"input": [tiny_low]})
        assert tiny_low in result["rejected"]
