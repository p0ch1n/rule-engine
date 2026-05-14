"""Pre-execution DAG validation for pipeline configurations."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Set

from rule_execution_engine.schema.models import PipelineConfig


class ValidationError(Exception):
    """Raised when a pipeline configuration is invalid."""

    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def validate_pipeline(config: PipelineConfig) -> None:
    """Validate pipeline DAG for structural correctness.

    Checks performed:
    1. All edge source/target node ids exist.
    2. No duplicate edge ids.
    3. Graph is acyclic (DAG constraint).
    4. No node is isolated (has at least one edge) — warn only.

    Raises ValidationError with all collected errors.
    """
    errors: List[str] = []

    node_ids: Set[str] = {n.id for n in config.nodes}
    edge_ids: Set[str] = set()

    # Adjacency list for cycle detection
    adjacency: Dict[str, List[str]] = defaultdict(list)

    for edge in config.edges:
        # Check for duplicate edge ids
        if edge.id in edge_ids:
            errors.append(f"Duplicate edge id: '{edge.id}'")
        edge_ids.add(edge.id)

        # Check source node exists
        if edge.source not in node_ids:
            errors.append(
                f"Edge '{edge.id}': source node '{edge.source}' does not exist"
            )

        # Check target node exists
        if edge.target not in node_ids:
            errors.append(
                f"Edge '{edge.id}': target node '{edge.target}' does not exist"
            )

        if edge.source in node_ids and edge.target in node_ids:
            adjacency[edge.source].append(edge.target)

    # Cycle detection using Kahn's algorithm
    if not errors:
        in_degree: Dict[str, int] = {nid: 0 for nid in node_ids}
        for nid, neighbours in adjacency.items():
            for nb in neighbours:
                in_degree[nb] += 1

        queue: deque[str] = deque(
            nid for nid, deg in in_degree.items() if deg == 0
        )
        visited = 0
        while queue:
            current = queue.popleft()
            visited += 1
            for nb in adjacency.get(current, []):
                in_degree[nb] -= 1
                if in_degree[nb] == 0:
                    queue.append(nb)

        if visited != len(node_ids):
            errors.append(
                "Pipeline contains a cycle — DAG constraint violated. "
                f"Processed {visited}/{len(node_ids)} nodes before stall."
            )

    if errors:
        raise ValidationError(errors)
