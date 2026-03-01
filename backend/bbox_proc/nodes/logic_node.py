"""LogicNode — existential condition check on a Collection of BBoxes."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from bbox_proc.nodes.base import BaseNode, PortDefinition, PortType
from bbox_proc.nodes.registry import NodeRegistry
from bbox_proc.schema.models import LogicConfig, LogicOperation
from bbox_proc.spatial.geometry import BBox


@NodeRegistry.register("logic")
class LogicNode(BaseNode):
    """Check whether a collection satisfies class-existence conditions.

    Supports AND (all conditions must hold) and OR (at least one must hold).

    Inputs:
        input (Collection): merged BBox collection from upstream.

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
                description="Merged BBox collection to evaluate",
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
        boxes: List[BBox] = self._get_bboxes(inputs, "input")

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
