"""Detector implementations — imported here to trigger @register decorators."""

from bbox_proc.detectors.base import BaseDetector
from bbox_proc.detectors.catalog import ModelCatalog
from bbox_proc.detectors.registry import DetectorRegistry

# Import concrete detectors to trigger registration
from bbox_proc.detectors.rf_detr import RFDETRDetector
from bbox_proc.detectors.yolov12 import YOLOv12Detector

__all__ = [
    "BaseDetector",
    "DetectorRegistry",
    "ModelCatalog",
    "YOLOv12Detector",
    "RFDETRDetector",
]
