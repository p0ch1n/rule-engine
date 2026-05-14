"""Tests for Scheduler, Interpreter, and Pipeline integration."""

import json
import pytest

from rule_execution_engine.engine.interpreter import ExecutionResult, Interpreter, Pipeline
from rule_execution_engine.nodes import NodeRegistry
from rule_execution_engine.schema.models import NodeConfig, PipelineConfig
from rule_execution_engine.schema.validator import ValidationError, validate_pipeline
from rule_execution_engine.spatial.geometry import Object


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #


SIMPLE_PIPELINE = {
    "version": "1.0",
    "metadata": {
        "tool_id": "cam-test",
        "class_list": ["person", "car"],
    },
    "nodes": [
        {
            "id": "filter-1",
            "type": "filter",
            "position": {"x": 100, "y": 100},
            "config": {
                "conditions": [
                    {"class_name": "person", "field": "confidence", "operator": "gt", "threshold": 0.5}
                ],
                "logic": "AND",
            },
        }
    ],
    "edges": [],
}

MERGE_PIPELINE = {
    "version": "1.0",
    "metadata": {
        "tool_id": "cam-merge",
        "class_list": ["person", "car"],
    },
    "nodes": [
        {
            "id": "filter-p",
            "type": "filter",
            "position": {"x": 0, "y": 0},
            "config": {
                "conditions": [
                    {"class_name": "person", "field": "confidence", "operator": "gt", "threshold": 0.5}
                ],
                "logic": "AND",
            },
        },
        {
            "id": "filter-c",
            "type": "filter",
            "position": {"x": 0, "y": 200},
            "config": {
                "conditions": [
                    {"class_name": "car", "field": "confidence", "operator": "gt", "threshold": 0.5}
                ],
                "logic": "AND",
            },
        },
        {
            "id": "merge-1",
            "type": "merge",
            "position": {"x": 300, "y": 100},
            "config": {"top_k": 1000},
        },
        {
            "id": "logic-1",
            "type": "logic",
            "position": {"x": 500, "y": 100},
            "config": {
                "operation": "AND",
                "conditions": [
                    {"class_name": "person", "min_count": 1},
                    {"class_name": "car", "min_count": 1},
                ],
                "trigger_label": "person-car-alert",
            },
        },
    ],
    "edges": [
        {
            "id": "e1",
            "source": "filter-p",
            "source_port": "output",
            "target": "merge-1",
            "target_port": "input_0",
        },
        {
            "id": "e2",
            "source": "filter-c",
            "source_port": "output",
            "target": "merge-1",
            "target_port": "input_1",
        },
        {
            "id": "e3",
            "source": "merge-1",
            "source_port": "output",
            "target": "logic-1",
            "target_port": "input",
        },
    ],
}


def make_frame_objects():
    return [
        Object(x=10, y=10, w=20, h=30, confidence=0.9, class_name="person"),
        Object(x=50, y=50, w=30, h=20, confidence=0.8, class_name="car"),
        Object(x=100, y=100, w=10, h=10, confidence=0.2, class_name="person"),  # below threshold
    ]


# ------------------------------------------------------------------ #
# Interpreter
# ------------------------------------------------------------------ #


class TestInterpreter:
    def test_from_dict_simple(self):
        pipeline = Interpreter.from_dict(SIMPLE_PIPELINE)
        assert isinstance(pipeline, Pipeline)

    def test_from_json_string(self):
        pipeline = Interpreter.from_json(json.dumps(SIMPLE_PIPELINE))
        assert isinstance(pipeline, Pipeline)

    def test_metadata_accessible(self):
        pipeline = Interpreter.from_dict(SIMPLE_PIPELINE)
        assert pipeline.metadata["tool_id"] == "cam-test"

    def test_invalid_json_raises(self):
        with pytest.raises(Exception):
            Interpreter.from_json("not-valid-json")

    def test_unknown_node_type_raises(self):
        bad = {**SIMPLE_PIPELINE}
        bad["nodes"] = [
            {**SIMPLE_PIPELINE["nodes"][0], "type": "nonexistent"}
        ]
        with pytest.raises(Exception):
            Interpreter.from_dict(bad)


# ------------------------------------------------------------------ #
# Execution
# ------------------------------------------------------------------ #


class TestPipelineExecution:
    def test_simple_filter_execution(self):
        pipeline = Interpreter.from_dict(SIMPLE_PIPELINE)
        objects = make_frame_objects()
        result = pipeline.execute_frame(objects)
        assert isinstance(result, ExecutionResult)

        # filter-1 should pass person with conf=0.9, reject person with conf=0.2
        output = result.get_node_output("filter-1", "output")
        assert output is not None
        confs = [b.confidence for b in output if b.class_name == "person"]
        assert all(c > 0.5 for c in confs)

    def test_merge_logic_pipeline(self):
        pipeline = Interpreter.from_dict(MERGE_PIPELINE)
        objects = make_frame_objects()
        result = pipeline.execute_frame(objects)

        # Logic node should fire (person AND car both present)
        signals = result.signals()
        assert "logic-1" in signals
        assert signals["logic-1"]["triggered"] is True
        assert signals["logic-1"]["label"] == "person-car-alert"

    def test_no_trigger_when_class_absent(self):
        pipeline = Interpreter.from_dict(MERGE_PIPELINE)
        # Only persons — no car
        objects = [
            Object(x=0, y=0, w=10, h=10, confidence=0.9, class_name="person"),
        ]
        result = pipeline.execute_frame(objects)
        signals = result.signals()
        assert signals["logic-1"]["triggered"] is False

    def test_all_outputs_returned(self):
        pipeline = Interpreter.from_dict(SIMPLE_PIPELINE)
        result = pipeline.execute_frame(make_frame_objects())
        outputs = result.all_outputs()
        assert "filter-1" in outputs


# ------------------------------------------------------------------ #
# DAG Validator
# ------------------------------------------------------------------ #


class TestDagValidator:
    def test_valid_pipeline_no_error(self):
        config = PipelineConfig.model_validate(SIMPLE_PIPELINE)
        validate_pipeline(config)  # should not raise

    def test_missing_source_node(self):
        bad = {
            **SIMPLE_PIPELINE,
            "edges": [
                {
                    "id": "e1",
                    "source": "nonexistent",
                    "source_port": "output",
                    "target": "filter-1",
                    "target_port": "input",
                }
            ],
        }
        config = PipelineConfig.model_validate(bad)
        with pytest.raises(ValidationError):
            validate_pipeline(config)

    def test_cyclic_pipeline_raises(self):
        cyclic = {
            "version": "1.0",
            "metadata": {"tool_id": "cam", "class_list": ["person"]},
            "nodes": [
                {
                    "id": "a",
                    "type": "filter",
                    "position": {"x": 0, "y": 0},
                    "config": {
                        "conditions": [{"class_name": "x", "field": "confidence", "operator": "gt", "threshold": 0}],
                        "logic": "AND",
                    },
                },
                {
                    "id": "b",
                    "type": "filter",
                    "position": {"x": 0, "y": 0},
                    "config": {
                        "conditions": [{"class_name": "x", "field": "confidence", "operator": "gt", "threshold": 0}],
                        "logic": "AND",
                    },
                },
            ],
            "edges": [
                {"id": "e1", "source": "a", "source_port": "output", "target": "b", "target_port": "input"},
                {"id": "e2", "source": "b", "source_port": "output", "target": "a", "target_port": "input"},
            ],
        }
        config = PipelineConfig.model_validate(cyclic)
        with pytest.raises(ValidationError):
            validate_pipeline(config)

    def test_duplicate_edge_ids_raise(self):
        dup_edges = {
            **MERGE_PIPELINE,
            "edges": [
                {
                    "id": "same-id",
                    "source": "filter-p",
                    "source_port": "output",
                    "target": "merge-1",
                    "target_port": "input_0",
                },
                {
                    "id": "same-id",  # duplicate!
                    "source": "filter-c",
                    "source_port": "output",
                    "target": "merge-1",
                    "target_port": "input_1",
                },
            ],
        }
        config = PipelineConfig.model_validate(dup_edges)
        with pytest.raises(ValidationError):
            validate_pipeline(config)
