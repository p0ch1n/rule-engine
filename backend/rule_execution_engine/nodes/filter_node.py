"""FilterNode — filter Objects by one or more class/field/operator/threshold conditions."""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Dict, List

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from rule_execution_engine.nodes.base import BaseNode, PortDefinition, PortType
from rule_execution_engine.nodes.registry import NodeRegistry
from rule_execution_engine.schema.models import FilterLogic, FilterOperator
from rule_execution_engine.spatial.geometry import Object


# ------------------------------------------------------------------ #
# Config schema
# ------------------------------------------------------------------ #


class FilterField(str, Enum):
    confidence = "confidence"
    width = "width"
    height = "height"
    area = "area"


class FilterCondition(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    class_name: str = Field(min_length=1)
    field: FilterField
    operator: FilterOperator
    threshold: float = Field(ge=0)


class FilterConfig(BaseModel):
    """Multi-condition filter config.

    logic="AND": an obj must satisfy ALL applicable conditions to pass.
    logic="OR":  an obj must satisfy AT LEAST ONE applicable condition to pass.
    Objects whose class_name is not listed in any condition pass through unchanged.
    """

    conditions: List[FilterCondition] = Field(min_length=1)
    logic: FilterLogic = FilterLogic.AND


def _make_comparator(operator: FilterOperator, threshold: float) -> Callable[[float], bool]:
    ops: Dict[FilterOperator, Callable[[float], bool]] = {
        FilterOperator.gt:  lambda v: v > threshold,
        FilterOperator.gte: lambda v: v >= threshold,
        FilterOperator.lt:  lambda v: v < threshold,
        FilterOperator.lte: lambda v: v <= threshold,
        FilterOperator.eq:  lambda v: v == threshold,
    }
    return ops[operator]


def _get_field_value(obj: Object, field: str) -> float:
    field_map = {
        "confidence": obj.confidence,
        "width":      obj.w,
        "height":     obj.h,
        "area":       obj.area,
    }
    if field not in field_map:
        raise ValueError(f"Unknown field '{field}' in FilterNode")
    return field_map[field]


def _condition_matches(obj: Object, cond: FilterCondition) -> bool:
    """Return True if obj satisfies this condition (class AND field check)."""
    if obj.class_name != cond.class_name:
        return False
    value = _get_field_value(obj, cond.field.value)
    return _make_comparator(cond.operator, cond.threshold)(value)


@NodeRegistry.register("filter", config_class=FilterConfig)
class FilterNode(BaseNode):
    """Filter a ObjectStream by one or more class/field/threshold conditions.

    Conditions are grouped by class_name:
    - Boxes whose class_name is NOT mentioned in any condition pass through unchanged.
    - For boxes whose class_name IS mentioned, the logic field decides:
        AND: the box must satisfy ALL conditions that target its class.
        OR:  the box must satisfy AT LEAST ONE condition that targets its class.

    Inputs:
        input (ObjectStream): incoming bounding boxes.

    Outputs:
        output   (ObjectStream): boxes that pass the filter.
        rejected (ObjectStream): boxes that fail the filter.
    """

    @property
    def input_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition(
                name="input",
                port_type=PortType.ObjectStream,
                description="Incoming Object stream",
            )
        ]

    @property
    def output_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition(
                name="output",
                port_type=PortType.ObjectStream,
                description="Objects passing the filter",
            ),
            PortDefinition(
                name="rejected",
                port_type=PortType.ObjectStream,
                description="Objects failing the filter",
                optional=True,
            ),
        ]

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        cfg: FilterConfig = self._parsed_config  # type: ignore[assignment]
        boxes: List[Object] = self._get_objects(inputs, "input")

        # Index conditions by class_name for O(1) lookup
        class_conditions: Dict[str, List[FilterCondition]] = {}
        for cond in cfg.conditions:
            class_conditions.setdefault(cond.class_name, []).append(cond)

        passed: List[Object] = []
        rejected: List[Object] = []

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
