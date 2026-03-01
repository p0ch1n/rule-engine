"""RelationNode — pairwise spatial relation detection between BBoxes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from bbox_proc.nodes.base import BaseNode, PortDefinition, PortType
from bbox_proc.nodes.registry import NodeRegistry
from bbox_proc.schema.models import RelationConfig, RelationMode, RelationType
from bbox_proc.spatial.geometry import BBox
from bbox_proc.spatial.iou import iou_matrix, centroid_distance_matrix
from bbox_proc.spatial.transform import apply_offset_config, apply_scale_config

import numpy as np


def _find_qualifying_pairs(
    boxes_a: List[BBox],
    boxes_b: List[BBox],
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


def _make_relation_bbox(
    box_a: BBox,
    box_b: BBox,
    cfg: RelationConfig,
    node_id: str,
) -> BBox:
    """Create a new BBox representing the detected relation (union + transform)."""
    union = box_a.union_bbox(box_b)
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


@NodeRegistry.register("relation")
class RelationNode(BaseNode):
    """Detect pairwise spatial relations and emit result BBoxes.

    Modes:
        self_join: compare boxes in the single input against themselves.
        cross_join: compare input_a against input_b (two separate streams).

    Inputs:
        input   (BoxStream): used in self_join, or first stream in cross_join.
        input_b (BoxStream): second stream for cross_join only (optional).

    Outputs:
        output (BoxStream): relation-BBoxes for qualifying pairs.
    """

    @property
    def input_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition(
                name="input",
                port_type=PortType.BoxStream,
                description="Primary input stream",
            ),
            PortDefinition(
                name="input_b",
                port_type=PortType.BoxStream,
                description="Secondary input (cross_join only)",
                optional=True,
            ),
        ]

    @property
    def output_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition(
                name="output",
                port_type=PortType.BoxStream,
                description="Relation BBoxes for qualifying pairs",
            )
        ]

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        cfg: RelationConfig = self._parsed_config  # type: ignore[assignment]

        boxes_a: List[BBox] = self._get_bboxes(inputs, "input")
        boxes_b: Optional[List[BBox]] = inputs.get("input_b")

        def _filter(boxes: List[BBox], cls: Optional[str]) -> List[BBox]:
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

        result_boxes: List[BBox] = []
        seen: set = set()

        for i, j in pairs:
            if same_pool and i >= j:
                # Skip symmetric duplicates within the same class pool
                continue
            pair_key = (i, j)
            if pair_key in seen:
                continue
            seen.add(pair_key)

            relation_bbox = _make_relation_bbox(src_a[i], src_b[j], cfg, self.node_id)
            result_boxes.append(relation_bbox)

        return {"output": result_boxes}
