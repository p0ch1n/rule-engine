"""RelationNode — pairwise spatial relation detection between Objects."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from rule_execution_engine.nodes.base import BaseNode, PortDefinition, PortType
from rule_execution_engine.nodes.registry import NodeRegistry
from rule_execution_engine.schema.models import ObjectOffset, ObjectScale
from rule_execution_engine.spatial.geometry import Object
from rule_execution_engine.spatial.iou import iou_matrix, centroid_distance_matrix
from rule_execution_engine.spatial.transform import apply_offset_config, apply_scale_config


# ------------------------------------------------------------------ #
# Config schema
# ------------------------------------------------------------------ #


class RelationType(str, Enum):
    iou = "iou"
    distance = "distance"
    contains = "contains"
    centroid_distance = "centroid_distance"


class RelationMode(str, Enum):
    self_join = "self_join"
    cross_join = "cross_join"


class RelationConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    mode: RelationMode
    relation_type: RelationType = RelationType.iou
    threshold: float = Field(default=0.0, ge=0)
    filter_class_a: Optional[str] = None
    filter_class_b: Optional[str] = None
    output_class_name: Optional[str] = None
    offset: Optional[ObjectOffset] = None
    scale: Optional[ObjectScale] = None


def _find_qualifying_pairs(
    boxes_a: List[Object],
    boxes_b: List[Object],
    relation_type: RelationType,
    threshold: float,
) -> List[Tuple[int, int]]:
    """Return (i, j) index pairs that satisfy the relation constraint."""
    if not boxes_a or not boxes_b:
        return []

    if relation_type == RelationType.iou:
        matrix = iou_matrix(boxes_a, boxes_b)
        indices = np.argwhere(matrix >= threshold)
    elif relation_type == RelationType.distance:
        matrix = centroid_distance_matrix(boxes_a, boxes_b)
        indices = np.argwhere(matrix <= threshold)
    elif relation_type == RelationType.centroid_distance:
        matrix = centroid_distance_matrix(boxes_a, boxes_b)
        indices = np.argwhere(matrix <= threshold)
    elif relation_type == RelationType.contains:
        # Box A contains Box B: A's area encompasses B entirely
        pairs = []
        for i, ba in enumerate(boxes_a):
            for j, bb in enumerate(boxes_b):
                if (
                    ba.x <= bb.x
                    and ba.y <= bb.y
                    and ba.x2 >= bb.x2
                    and ba.y2 >= bb.y2
                ):
                    pairs.append((i, j))
        return pairs
    else:
        return []

    return [(int(r), int(c)) for r, c in indices]


def _make_relation_obj(
    box_a: Object,
    box_b: Object,
    cfg: RelationConfig,
    node_id: str,
) -> Object:
    """Create a new Object representing the detected relation (union + transform)."""
    union = box_a.union_obj(box_b)
    # Apply user-defined offset and scale
    transformed = apply_offset_config(union, cfg.offset.model_dump() if cfg.offset else None)
    transformed = apply_scale_config(transformed, cfg.scale.model_dump() if cfg.scale else None)

    result = transformed.with_metadata(
        relation_type=cfg.relation_type.value,
        source_a_class=box_a.class_name,
        source_b_class=box_b.class_name,
        relation_node=node_id,
    )
    if cfg.output_class_name:
        result = result.with_class(cfg.output_class_name)
    return result


@NodeRegistry.register("relation", config_class=RelationConfig)
class RelationNode(BaseNode):
    """Detect pairwise spatial relations and emit result Objects.

    Modes:
        self_join: compare boxes in the single input against themselves.
        cross_join: compare input_a against input_b (two separate streams).

    Inputs:
        input   (ObjectStream): used in self_join, or first stream in cross_join.
        input_b (ObjectStream): second stream for cross_join only (optional).

    Outputs:
        output (ObjectStream): relation-Objects for qualifying pairs.
    """

    @property
    def input_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition(
                name="input",
                port_type=PortType.ObjectStream,
                description="Primary input stream",
            ),
            PortDefinition(
                name="input_b",
                port_type=PortType.ObjectStream,
                description="Secondary input (cross_join only)",
                optional=True,
            ),
        ]

    @property
    def output_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition(
                name="output",
                port_type=PortType.ObjectStream,
                description="Relation Objects for qualifying pairs",
            )
        ]

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        cfg: RelationConfig = self._parsed_config  # type: ignore[assignment]

        boxes_a: List[Object] = self._get_objects(inputs, "input")
        boxes_b: Optional[List[Object]] = inputs.get("input_b")

        def _filter(boxes: List[Object], cls: Optional[str]) -> List[Object]:
            if not cls:
                return boxes
            return [b for b in boxes if b.class_name == cls]

        if cfg.mode == RelationMode.self_join:
            # Both sides draw from the single input, filtered to their respective classes.
            src_a = _filter(boxes_a, cfg.filter_class_a)
            src_b = _filter(boxes_a, cfg.filter_class_b)
        else:
            src_a = _filter(boxes_a, cfg.filter_class_a)
            src_b = _filter(boxes_b or [], cfg.filter_class_b)

        # Symmetric dedup only makes sense when both sides are the same class pool
        same_pool = (
            cfg.mode == RelationMode.self_join
            and cfg.filter_class_a == cfg.filter_class_b
        )

        pairs = _find_qualifying_pairs(src_a, src_b, cfg.relation_type, cfg.threshold)

        result_boxes: List[Object] = []
        seen: set = set()

        for i, j in pairs:
            if same_pool and i >= j:
                # Skip symmetric duplicates within the same class pool
                continue
            pair_key = (i, j)
            if pair_key in seen:
                continue
            seen.add(pair_key)

            relation_obj = _make_relation_obj(src_a[i], src_b[j], cfg, self.node_id)
            result_boxes.append(relation_obj)

        return {"output": result_boxes}
