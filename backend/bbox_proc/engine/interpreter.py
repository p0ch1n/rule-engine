"""Interpreter — loads a pipeline JSON and produces a runnable Pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from bbox_proc.nodes import NodeRegistry  # triggers all @register decorators
from bbox_proc.nodes.base import BaseNode
from bbox_proc.schema.models import EdgeConfig, PipelineConfig
from bbox_proc.schema.validator import validate_pipeline


class Pipeline:
    """Runnable pipeline built from a PipelineConfig.

    The pipeline is a pure library — it performs single-frame processing
    and returns an ExecutionResult. The caller decides how to act on it
    (alert, store, print, etc.).
    """

    def __init__(
        self,
        config: PipelineConfig,
        nodes: Dict[str, BaseNode],
        edges: List[EdgeConfig],
    ) -> None:
        self.config = config
        self._nodes = nodes
        self._edges = edges

    def execute_frame(
        self,
        input_bboxes: Optional[List[Any]] = None,
        images: Optional[List[np.ndarray]] = None,
    ) -> "ExecutionResult":
        """Process a single frame through the pipeline.

        Args:
            input_bboxes: Pre-detected BBox list for bbox-only pipelines.
            images:       Raw image frames for pipelines containing DetectionNodes.

        Returns:
            ExecutionResult with per-node outputs and aggregated signals.
        """
        from bbox_proc.engine.scheduler import Scheduler

        scheduler = Scheduler(self._nodes, self._edges)
        return scheduler.run(input_bboxes=input_bboxes, images=images)

    @property
    def metadata(self) -> Dict[str, Any]:
        return self.config.metadata.model_dump()


class ExecutionResult:
    """Container for the outputs of a single-frame pipeline execution."""

    def __init__(self, node_outputs: Dict[str, Dict[str, Any]]) -> None:
        self._outputs = node_outputs

    def get_node_output(self, node_id: str, port: str = "output") -> Any:
        """Retrieve a specific node's output for a given port."""
        return self._outputs.get(node_id, {}).get(port)

    def all_outputs(self) -> Dict[str, Dict[str, Any]]:
        """Return the full mapping of {node_id: {port: value}}."""
        return dict(self._outputs)

    def signals(self) -> Dict[str, Any]:
        """Return outputs from all LogicNode signal ports."""
        result = {}
        for node_id, ports in self._outputs.items():
            if "signal" in ports:
                result[node_id] = ports["signal"]
        return result

    def __repr__(self) -> str:
        node_count = len(self._outputs)
        signal_count = len(self.signals())
        return f"ExecutionResult(nodes={node_count}, signals={signal_count})"


class Interpreter:
    """Static factory for building Pipeline objects from JSON sources."""

    @staticmethod
    def load(path: Union[str, Path]) -> Pipeline:
        """Load a pipeline from a JSON file path."""
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return Interpreter.from_dict(data)

    @staticmethod
    def from_json(json_str: str) -> Pipeline:
        """Load a pipeline from a JSON string."""
        data = json.loads(json_str)
        return Interpreter.from_dict(data)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Pipeline:
        """Build a Pipeline from a raw dict (must conform to PipelineConfig schema)."""
        config = PipelineConfig.model_validate(data)
        validate_pipeline(config)

        nodes: Dict[str, BaseNode] = {}
        for node_config in config.nodes:
            node = NodeRegistry.create(node_config)
            nodes[node_config.id] = node

        return Pipeline(config, nodes, config.edges)
