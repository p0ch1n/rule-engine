"""Node registry — Registry Pattern for extensible node type management."""

from __future__ import annotations

from typing import ClassVar, Dict, List, Type

from bbox_proc.nodes.base import BaseNode
from bbox_proc.schema.models import NodeConfig


class NodeRegistry:
    """Central registry mapping node type strings to BaseNode subclasses.

    Usage:
        @NodeRegistry.register("filter")
        class FilterNode(BaseNode): ...

        node = NodeRegistry.create(config)
    """

    _registry: ClassVar[Dict[str, Type[BaseNode]]] = {}

    @classmethod
    def register(cls, node_type: str):
        """Decorator that registers a node class under the given type string."""

        def decorator(node_class: Type[BaseNode]) -> Type[BaseNode]:
            if node_type in cls._registry:
                raise KeyError(
                    f"Node type '{node_type}' is already registered. "
                    f"Existing: {cls._registry[node_type].__name__}, "
                    f"New: {node_class.__name__}"
                )
            cls._registry[node_type] = node_class
            return node_class

        return decorator

    @classmethod
    def create(cls, config: NodeConfig) -> BaseNode:
        """Instantiate a node from its configuration.

        Raises:
            KeyError: if node type is not registered.
        """
        node_class = cls._registry.get(config.type)
        if node_class is None:
            available = sorted(cls._registry.keys())
            raise KeyError(
                f"Unknown node type: '{config.type}'. "
                f"Available types: {available}"
            )
        return node_class(config)

    @classmethod
    def registered_types(cls) -> List[str]:
        """Return sorted list of all registered node type names."""
        return sorted(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear the registry (intended for testing only)."""
        cls._registry.clear()
