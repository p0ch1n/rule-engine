"""LogicNode — existential condition check on a Collection of Objects."""

from __future__ import annotations

from collections import Counter
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from rule_execution_engine.nodes.base import BaseNode, PortDefinition, PortType
from rule_execution_engine.nodes.registry import NodeRegistry
from rule_execution_engine.spatial.geometry import Object


# ------------------------------------------------------------------ #
# Config schema
# ------------------------------------------------------------------ #


class LogicOperation(str, Enum):
    AND = "AND"
    OR = "OR"


class LogicCondition(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    class_name: str = Field(min_length=1)
    min_count: int = Field(default=1, ge=1)
    negate: bool = False


class LogicConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    operation: LogicOperation
    conditions: List[LogicCondition] = Field(min_length=1)
    trigger_label: Optional[str] = None


@NodeRegistry.register("logic", config_class=LogicConfig)
class LogicNode(BaseNode):
    """Check whether a collection satisfies class-existence conditions.

    Supports AND (all conditions must hold) and OR (at least one must hold).

    Inputs:
        input (Collection): merged Object collection from upstream.

    Outputs:
        signal (LogicSignal): dict with keys:
            - triggered (bool): whether the condition fired.
            - label (str): trigger_label from config (or empty string).
            - matched_classes (list[str]): which class conditions were satisfied.
            - total_count (int): total number of input boxes examined.
    """

    @property
    def input_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition(
                name="input",
                port_type=PortType.Collection,
                description="Merged Object collection to evaluate",
            )
        ]

    @property
    def output_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition(
                name="signal",
                port_type=PortType.LogicSignal,
                description="Boolean trigger signal with metadata",
            )
        ]

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        cfg: LogicConfig = self._parsed_config  # type: ignore[assignment]
        boxes: List[Object] = self._get_objects(inputs, "input")

        # Count occurrences per class
        class_counts: Counter = Counter(b.class_name for b in boxes)

        matched_classes: List[str] = []
        for condition in cfg.conditions:
            count = class_counts.get(condition.class_name, 0)
            positive = count >= condition.min_count
            satisfied = (not positive) if condition.negate else positive
            if satisfied:
                matched_classes.append(condition.class_name)

        total_conditions = len(cfg.conditions)
        matched_count = len(matched_classes)

        if cfg.operation == LogicOperation.AND:
            triggered = matched_count == total_conditions
        else:  # OR
            triggered = matched_count >= 1

        signal = {
            "triggered": triggered,
            "label": cfg.trigger_label or "",
            "matched_classes": matched_classes,
            "total_count": len(boxes),
            "class_counts": dict(class_counts),
        }

        return {"signal": signal}
