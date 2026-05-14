"""Detector implementations — imported here to trigger @register decorators."""

from rule_execution_engine.detectors.base import BaseDetector
from rule_execution_engine.detectors.catalog import ModelCatalog
from rule_execution_engine.detectors.registry import DetectorRegistry

# Import concrete detectors to trigger registration
from rule_execution_engine.detectors.rf_detr import RFDETRDetector
from rule_execution_engine.detectors.yolov12 import YOLOv12Detector

__all__ = [
    "BaseDetector",
    "DetectorRegistry",
    "ModelCatalog",
    "YOLOv12Detector",
    "RFDETRDetector",
]
