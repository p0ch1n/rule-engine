"""Detector registry — maps architecture strings to BaseDetector subclasses."""

from __future__ import annotations

from typing import ClassVar, Dict, List, Type

from rule_execution_engine.detectors.base import BaseDetector


class DetectorRegistry:
    """Maps architecture name → detector class.

    Usage:
        @DetectorRegistry.register("yolov12")
        class YOLOv12Detector(BaseDetector): ...

        detector = DetectorRegistry.create("yolov12", model_path, device)
    """

    _registry: ClassVar[Dict[str, Type[BaseDetector]]] = {}

    @classmethod
    def register(cls, architecture: str):
        """Decorator that registers a detector class under the given architecture name."""

        def decorator(detector_class: Type[BaseDetector]) -> Type[BaseDetector]:
            if architecture in cls._registry:
                raise KeyError(
                    f"Architecture '{architecture}' is already registered. "
                    f"Existing: {cls._registry[architecture].__name__}"
                )
            cls._registry[architecture] = detector_class
            return detector_class

        return decorator

    @classmethod
    def create(cls, architecture: str, model_path: str, device: str) -> BaseDetector:
        """Instantiate a detector by architecture name."""
        detector_class = cls._registry.get(architecture)
        if detector_class is None:
            available = sorted(cls._registry.keys())
            raise KeyError(
                f"Unknown detector architecture: '{architecture}'. "
                f"Available: {available}"
            )
        return detector_class(model_path=model_path, device=device)

    @classmethod
    def registered_architectures(cls) -> List[str]:
        """Return sorted list of all registered architecture names."""
        return sorted(cls._registry.keys())
