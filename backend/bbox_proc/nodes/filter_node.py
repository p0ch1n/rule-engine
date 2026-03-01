"""FilterNode — filter BBoxes by one or more class/field/operator/threshold conditions."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from bbox_proc.nodes.base import BaseNode, PortDefinition, PortType
from bbox_proc.nodes.registry import NodeRegistry
from bbox_proc.schema.models import FilterCondition, FilterConfig, FilterLogic, FilterOperator
from bbox_proc.spatial.geometry import BBox


def _make_comparator(operator: FilterOperator, threshold: float) -> Callable[[float], bool]:
    ops: Dict[FilterOperator, Callable[[float], bool]] = {
        FilterOperator.gt:  lambda v: v > threshold,
        FilterOperator.gte: lambda v: v >= threshold,
        FilterOperator.lt:  lambda v: v < threshold,
        FilterOperator.lte: lambda v: v <= threshold,
        FilterOperator.eq:  lambda v: v == threshold,
    }
    return ops[operator]


def _get_field_value(bbox: BBox, field: str) -> float:
    field_map = {
        "confidence": bbox.confidence,
        "width":      bbox.w,
        "height":     bbox.h,
        "area":       bbox.area,
    }
    if field not in field_map:
        raise ValueError(f"Unknown field '{field}' in FilterNode")
    return field_map[field]


def _condition_matches(bbox: BBox, cond: FilterCondition) -> bool:
    """Return True if bbox satisfies this condition (class AND field check)."""
    if bbox.class_name != cond.class_name:
        return False
    value = _get_field_value(bbox, cond.field.value)
    return _make_comparator(cond.operator, cond.threshold)(value)


@NodeRegistry.register("filter")
class FilterNode(BaseNode):
    """Filter a BoxStream by one or more class/field/threshold conditions.

    Conditions are grouped by class_name:
    - Boxes whose class_name is NOT mentioned in any condition pass through unchanged.
    - For boxes whose class_name IS mentioned, the logic field decides:
        AND: the box must satisfy ALL conditions that target its class.
        OR:  the box must satisfy AT LEAST ONE condition that targets its class.

    Inputs:
        input (BoxStream): incoming bounding boxes.

    Outputs:
        output   (BoxStream): boxes that pass the filter.
        rejected (BoxStream): boxes that fail the filter.
    """

    @property
    def input_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition(
                name="input",
                port_type=PortType.BoxStream,
                description="Incoming BBox stream",
            )
        ]

    @property
    def output_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition(
                name="output",
                port_type=PortType.BoxStream,
                description="BBoxes passing the filter",
            ),
            PortDefinition(
                name="rejected",
                port_type=PortType.BoxStream,
                description="BBoxes failing the filter",
                optional=True,
            ),
        ]

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        cfg: FilterConfig = self._parsed_config  # type: ignore[assignment]
        boxes: List[BBox] = self._get_bboxes(inputs, "input")

        # Index conditions by class_name for O(1) lookup
        class_conditions: Dict[str, List[FilterCondition]] = {}
        for cond in cfg.conditions:
            class_conditions.setdefault(cond.class_name, []).append(cond)

        passed: List[BBox] = []
        rejected: List[BBox] = []

        for box in boxes:
            relevant = class_conditions.get(box.class_name)

            if not relevant:
                # No condition targets this class → pass through unchanged
                passed.append(box)
                continue

            results = [_condition_matches(box, c) for c in relevant]

            if cfg.logic == FilterLogic.AND:
                ok = all(results)
            else:  # OR
                ok = any(results)

            (passed if ok else rejected).append(box)

        return {"output": passed, "rejected": rejected}
