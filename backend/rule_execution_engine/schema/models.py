"""Pydantic models for pipeline configuration (JSON Schema binding).

Shared primitives only — node-specific config classes live in their
respective node files alongside the node implementation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel


# ------------------------------------------------------------------ #
# Shared enums
# ------------------------------------------------------------------ #


from enum import Enum


class FilterOperator(str, Enum):
    """Comparison operators shared across filter-style conditions."""

    gt = "gt"
    gte = "gte"
    lt = "lt"
    lte = "lte"
    eq = "eq"


class FilterLogic(str, Enum):
    """AND / OR logic shared across multi-condition nodes."""

    AND = "AND"
    OR = "OR"


# ------------------------------------------------------------------ #
# Geometry helpers
# ------------------------------------------------------------------ #


class Position(BaseModel):
    x: float
    y: float


class ObjectOffset(BaseModel):
    dx: float = 0.0
    dy: float = 0.0
    dw: float = 0.0
    dh: float = 0.0


class ObjectScale(BaseModel):
    sx: float = Field(default=1.0, ge=0)
    sy: float = Field(default=1.0, ge=0)
    sw: float = Field(default=1.0, ge=0)
    sh: float = Field(default=1.0, ge=0)


# ------------------------------------------------------------------ #
# Shared schema types
# ------------------------------------------------------------------ #


class InputFile(BaseModel):
    """A single uploaded file stored as a base64 data URI."""

    filename: str = Field(min_length=1)
    data: str = Field(min_length=1)


# ------------------------------------------------------------------ #
# Node + Edge
# ------------------------------------------------------------------ #


class NodeConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str = Field(min_length=1)
    type: str
    position: Position
    function_id: Optional[str] = None
    config: Dict[str, Any]  # raw dict; typed parsing done per-node via NodeRegistry

    def parse_config(self) -> Any:
        """Return a typed config object by delegating to the node's registered config class."""
        from rule_execution_engine.nodes.registry import NodeRegistry  # lazy — avoids circular import
        config_cls = NodeRegistry.get_config_class(self.type)
        if config_cls is None:
            return self.config
        return config_cls.model_validate(self.config)


class EdgeConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_port: str = Field(min_length=1)
    target: str = Field(min_length=1)
    target_port: str = Field(min_length=1)


# ------------------------------------------------------------------ #
# Pipeline root
# ------------------------------------------------------------------ #


class PipelineMetadata(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    tool_id: str = Field(min_length=1)
    class_list: List[str] = Field(min_length=1)
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator("class_list")
    @classmethod
    def class_list_unique(cls, v: List[str]) -> List[str]:
        if len(v) != len(set(v)):
            raise ValueError("class_list must contain unique entries")
        return v


class PipelineConfig(BaseModel):
    version: str
    metadata: PipelineMetadata
    nodes: List[NodeConfig] = Field(min_length=1)
    edges: List[EdgeConfig] = Field(default_factory=list)

    @field_validator("version")
    @classmethod
    def version_format(cls, v: str) -> str:
        parts = v.split(".")
        if len(parts) != 2 or not all(p.isdigit() for p in parts):
            raise ValueError("version must be in 'major.minor' format, e.g. '1.0'")
        return v

    @model_validator(mode="after")
    def node_ids_unique(self) -> "PipelineConfig":
        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("Node ids must be unique within a pipeline")
        return self
