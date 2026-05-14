"""Node registry — Registry Pattern for extensible node type management."""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional, Type

from rule_execution_engine.nodes.base import BaseNode
from rule_execution_engine.schema.models import NodeConfig


class NodeRegistry:
    """Central registry mapping node type strings to BaseNode subclasses.

    Usage:
        @NodeRegistry.register("filter", config_class=FilterConfig)
        class FilterNode(BaseNode): ...

        node = NodeRegistry.create(config)
    """

    _registry: ClassVar[Dict[str, Type[BaseNode]]] = {}
    _config_registry: ClassVar[Dict[str, Type[Any]]] = {}

    @classmethod
    def register(cls, node_type: str, *, config_class: Optional[Type[Any]] = None):
        """Decorator that registers a node class (and its config class) under the given type string."""

        def decorator(node_class: Type[BaseNode]) -> Type[BaseNode]:
            if node_type in cls._registry:
                raise KeyError(
                    f"Node type '{node_type}' is already registered. "
                    f"Existing: {cls._registry[node_type].__name__}, "
                    f"New: {node_class.__name__}"
                )
            cls._registry[node_type] = node_class
            if config_class is not None:
                cls._config_registry[node_type] = config_class
            return node_class

        return decorator

    @classmethod
    def get_config_class(cls, node_type: str) -> Optional[Type[Any]]:
        """Return the registered config class for a node type, or None if not registered."""
        return cls._config_registry.get(node_type)

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
        cls._config_registry.clear()
