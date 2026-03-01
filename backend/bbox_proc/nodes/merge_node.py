"""MergeNode — aggregate multiple BoxStreams into one Collection."""

from __future__ import annotations

from typing import Any, Dict, List

from bbox_proc.nodes.base import BaseNode, PortDefinition, PortType
from bbox_proc.nodes.registry import NodeRegistry
from bbox_proc.schema.models import MergeConfig
from bbox_proc.spatial.geometry import BBox
from bbox_proc.spatial.transform import top_k_by_confidence


@NodeRegistry.register("merge")
class MergeNode(BaseNode):
    """Merge multiple BoxStream inputs into a single Collection.

    Each incoming BBox is tagged with its source node_id in metadata
    to preserve lineage. Boxes are NOT deduplicated — all copies are kept.
    A Top-K guard (default K=1000, ordered by confidence desc) prevents
    runaway processing when many streams converge.

    Inputs:
        input_0 … input_N (BoxStream): each source branch.

    Outputs:
        output (Collection): merged, lineage-tagged, top-k-truncated boxes.
    """

    # MergeNode supports variable number of inputs (determined at connect time).
    # We declare a representative set; the engine adds ports dynamically.
    _MAX_STATIC_PORTS = 16

    @property
    def input_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition(
                name=f"input_{i}",
                port_type=PortType.BoxStream,
                description=f"Source branch {i}",
                optional=(i > 0),
            )
            for i in range(self._MAX_STATIC_PORTS)
        ]

    @property
    def output_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition(
                name="output",
                port_type=PortType.Collection,
                description="Merged collection with lineage metadata",
            )
        ]

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        cfg: MergeConfig = self._parsed_config  # type: ignore[assignment]
        merged: List[BBox] = []

        # Collect from all input_N ports present in inputs
        port_keys = sorted(
            (k for k in inputs if k.startswith("input_")),
            key=lambda k: int(k.split("_", 1)[1]),
        )

        for port_key in port_keys:
            source_boxes: List[BBox] = inputs.get(port_key, [])
            for box in source_boxes:
                # Tag lineage: which port (and by convention which upstream node)
                tagged = box.with_metadata(
                    lineage_port=port_key,
                    lineage_node=self.node_id,
                )
                merged.append(tagged)

        # Top-K protection — sort by confidence descending, keep best K
        output = top_k_by_confidence(merged, cfg.top_k)

        return {"output": output}
