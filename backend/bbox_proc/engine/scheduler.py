"""Scheduler — topological sort + per-frame execution loop."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, List

from bbox_proc.nodes.base import BaseNode
from bbox_proc.schema.models import EdgeConfig
from bbox_proc.spatial.geometry import BBox


class Scheduler:
    """Executes pipeline nodes in topologically sorted order.

    Uses Kahn's algorithm for the sort, then propagates outputs through
    the edge graph. Input source nodes (in-degree 0) receive the raw
    frame bboxes as their 'input' port.

    This class is stateless — create a new instance per execute_frame call
    (or reuse; it never holds frame state).
    """

    def __init__(
        self,
        nodes: Dict[str, BaseNode],
        edges: List[EdgeConfig],
    ) -> None:
        self._nodes = nodes
        self._edges = edges

        # Build adjacency structures
        self._successors: Dict[str, List[EdgeConfig]] = defaultdict(list)
        self._in_degree: Dict[str, int] = {nid: 0 for nid in nodes}

        for edge in edges:
            self._successors[edge.source].append(edge)
            self._in_degree[edge.target] += 1

        self._topo_order = self._compute_topo_order()

    def _compute_topo_order(self) -> List[str]:
        """Return node ids in topological execution order (Kahn's algorithm)."""
        in_deg = dict(self._in_degree)
        queue: deque[str] = deque(
            nid for nid, deg in in_deg.items() if deg == 0
        )
        order: List[str] = []

        while queue:
            current = queue.popleft()
            order.append(current)
            for edge in self._successors.get(current, []):
                in_deg[edge.target] -= 1
                if in_deg[edge.target] == 0:
                    queue.append(edge.target)

        if len(order) != len(self._nodes):
            raise RuntimeError(
                "Cycle detected during scheduling — pipeline is not a valid DAG. "
                f"Scheduled {len(order)}/{len(self._nodes)} nodes."
            )

        return order

    def run(self, input_bboxes: List[BBox]) -> "ExecutionResult":
        """Execute all nodes for one frame.

        Source nodes (in-degree 0) receive input_bboxes on their 'input' port.
        All other nodes receive outputs forwarded by upstream edges.
        """
        from bbox_proc.engine.interpreter import ExecutionResult

        # port_data[node_id][port_name] = value
        port_data: Dict[str, Dict[str, Any]] = defaultdict(dict)

        # Seed source nodes
        for node_id, deg in self._in_degree.items():
            if deg == 0:
                port_data[node_id]["input"] = list(input_bboxes)

        node_outputs: Dict[str, Dict[str, Any]] = {}

        for node_id in self._topo_order:
            node = self._nodes[node_id]
            inputs = port_data.get(node_id, {})

            try:
                outputs = node.execute(inputs)
            except Exception as exc:
                raise RuntimeError(
                    f"Node '{node_id}' ({node.__class__.__name__}) "
                    f"raised an error during execution: {exc}"
                ) from exc

            node_outputs[node_id] = outputs

            # Propagate outputs to downstream nodes
            for edge in self._successors.get(node_id, []):
                value = outputs.get(edge.source_port)
                if value is not None:
                    # MergeNode: multiple edges can map to input_0, input_1 …
                    # target_port is set by the exporter (e.g. 'input_0')
                    port_data[edge.target][edge.target_port] = value

        return ExecutionResult(node_outputs)
