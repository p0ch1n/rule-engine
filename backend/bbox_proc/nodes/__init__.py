"""Node implementations — imported here to trigger @register decorators."""

from bbox_proc.nodes.base import BaseNode, PortDefinition, PortType
from bbox_proc.nodes.registry import NodeRegistry

# Import nodes to trigger registration
from bbox_proc.nodes.filter_node import FilterNode
from bbox_proc.nodes.logic_node import LogicNode
from bbox_proc.nodes.merge_node import MergeNode
from bbox_proc.nodes.relation_node import RelationNode

__all__ = [
    "BaseNode",
    "PortDefinition",
    "PortType",
    "NodeRegistry",
    "FilterNode",
    "LogicNode",
    "MergeNode",
    "RelationNode",
]
