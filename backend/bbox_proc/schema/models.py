"""Pydantic models for pipeline configuration (JSON Schema binding)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


# ------------------------------------------------------------------ #
# Enums
# ------------------------------------------------------------------ #


class FilterOperator(str, Enum):
    gt = "gt"
    gte = "gte"
    lt = "lt"
    lte = "lte"
    eq = "eq"


class FilterField(str, Enum):
    confidence = "confidence"
    width = "width"
    height = "height"
    area = "area"


class LogicOperation(str, Enum):
    AND = "AND"
    OR = "OR"


class RelationType(str, Enum):
    iou = "iou"
    distance = "distance"
    contains = "contains"
    centroid_distance = "centroid_distance"


class RelationMode(str, Enum):
    self_join = "self_join"
    cross_join = "cross_join"


# ------------------------------------------------------------------ #
# Geometry helpers
# ------------------------------------------------------------------ #


class Position(BaseModel):
    x: float
    y: float


class BBoxOffset(BaseModel):
    dx: float = 0.0
    dy: float = 0.0
    dw: float = 0.0
    dh: float = 0.0


class BBoxScale(BaseModel):
    sx: float = Field(default=1.0, ge=0)
    sy: float = Field(default=1.0, ge=0)
    sw: float = Field(default=1.0, ge=0)
    sh: float = Field(default=1.0, ge=0)


# ------------------------------------------------------------------ #
# Node configs
# ------------------------------------------------------------------ #


class FilterCondition(BaseModel):
    """A single filter predicate applied to bounding boxes of a given class."""

    class_name: str = Field(min_length=1)
    field: FilterField
    operator: FilterOperator
    threshold: float = Field(ge=0)


class FilterLogic(str, Enum):
    AND = "AND"
    OR = "OR"


class FilterConfig(BaseModel):
    """Multi-condition filter config.

    logic="AND": a bbox must satisfy ALL applicable conditions to pass.
    logic="OR":  a bbox must satisfy AT LEAST ONE applicable condition to pass.
    Boxes whose class_name is not listed in any condition pass through unchanged.
    """

    conditions: List[FilterCondition] = Field(min_length=1)
    logic: FilterLogic = FilterLogic.AND


class LogicCondition(BaseModel):
    class_name: str = Field(min_length=1)
    min_count: int = Field(default=1, ge=1)
    negate: bool = False


class LogicConfig(BaseModel):
    operation: LogicOperation
    conditions: List[LogicCondition] = Field(min_length=1)
    trigger_label: Optional[str] = None


class RelationConfig(BaseModel):
    mode: RelationMode
    relation_type: RelationType = RelationType.iou
    threshold: float = Field(default=0.0, ge=0)
    filter_class_a: Optional[str] = None
    filter_class_b: Optional[str] = None
    output_class_name: Optional[str] = None
    offset: Optional[BBoxOffset] = None
    scale: Optional[BBoxScale] = None


class MergeConfig(BaseModel):
    top_k: int = Field(default=1000, ge=1)


class DetectionConfig(BaseModel):
    """Config for object detection source nodes."""

    architecture: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    nms_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    device: Literal["cpu", "cuda"] = "cpu"


class ImageAnalysisField(str, Enum):
    """Pixel measurement fields for ImageAnalysisNode (BGR channel order)."""

    intensity = "intensity"      # ITU-R BT.601 luminance, 0–255
    red = "red"                  # R channel mean, 0–255
    green = "green"              # G channel mean, 0–255
    blue = "blue"                # B channel mean, 0–255
    hue = "hue"                  # HSV H channel mean, 0–360
    saturation = "saturation"    # HSV S channel mean, 0–100
    value = "value"              # HSV V channel mean, 0–100


class ImageAnalysisCondition(BaseModel):
    """A single measurement condition applied to BBoxes of a given class."""

    class_name: str = ""         # empty string = applies to all classes
    field: ImageAnalysisField
    operator: FilterOperator
    threshold: float = Field(ge=0.0)


class ImageAnalysisConfig(BaseModel):
    """Config for ImageAnalysisNode.

    logic="AND": a bbox must satisfy ALL applicable conditions to survive.
    logic="OR":  a bbox must satisfy AT LEAST ONE applicable condition to survive.
    BBoxes whose class does not match any condition's class_name pass through unchanged.
    """

    conditions: List[ImageAnalysisCondition] = Field(min_length=1)
    logic: FilterLogic = FilterLogic.AND


# ------------------------------------------------------------------ #
# Node + Edge
# ------------------------------------------------------------------ #

NodeConfigUnion = Union[
    FilterConfig, LogicConfig, RelationConfig, MergeConfig,
    DetectionConfig, ImageAnalysisConfig,
]


class NodeConfig(BaseModel):
    id: str = Field(min_length=1)
    type: Literal["filter", "logic", "relation", "merge", "detection", "image_analysis"]
    position: Position
    config: Dict[str, Any]  # raw dict; typed parsing done in nodes

    def parse_config(self) -> NodeConfigUnion:
        """Return typed config object based on node type."""
        config_map = {
            "filter": FilterConfig,
            "logic": LogicConfig,
            "relation": RelationConfig,
            "merge": MergeConfig,
            "detection": DetectionConfig,
            "image_analysis": ImageAnalysisConfig,
        }
        cls = config_map[self.type]
        return cls.model_validate(self.config)


class EdgeConfig(BaseModel):
    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_port: str = Field(min_length=1)
    target: str = Field(min_length=1)
    target_port: str = Field(min_length=1)


# ------------------------------------------------------------------ #
# Pipeline root
# ------------------------------------------------------------------ #


class PipelineMetadata(BaseModel):
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
