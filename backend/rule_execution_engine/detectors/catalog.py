"""Model catalog — loads models.yaml and resolves weight paths by name."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Union

import yaml


class ModelCatalog:
    """Registry of available model weights per detector architecture.

    Load the catalog from a YAML file before running detection pipelines.
    If not explicitly loaded, the catalog auto-discovers models.yaml from:
    1. The backend package directory (rule_execution_engine/../../models.yaml)
    2. The current working directory (./models.yaml)

    YAML format:
        yolov12:
          - name: person_detection
            path: weights/yolov12_person.pt
            description: Person detection model
        rf_detr:
          - name: person_detection
            path: weights/rf_detr_person.pt
            description: RF-DETR person detection
    """

    _catalog: ClassVar[Optional[Dict[str, List[Dict]]]] = None

    @classmethod
    def load(cls, path: Union[str, Path]) -> None:
        """Explicitly load the model catalog from a YAML file."""
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(
                f"models.yaml must be a top-level mapping, got {type(data).__name__}"
            )
        cls._catalog = data

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls._catalog is not None:
            return
        candidates = [
            Path(__file__).parent.parent.parent / "models.yaml",  # backend/models.yaml
            Path("models.yaml"),
        ]
        for candidate in candidates:
            if candidate.exists():
                cls.load(candidate)
                return
        raise RuntimeError(
            "ModelCatalog is not loaded and no models.yaml was found. "
            "Call ModelCatalog.load('path/to/models.yaml') before running "
            "pipelines that contain detection nodes."
        )

    @classmethod
    def get_model_path(cls, architecture: str, model_name: str) -> str:
        """Return the weight file path for a given architecture + model name."""
        cls._ensure_loaded()
        arch_entries = cls._catalog.get(architecture)  # type: ignore[union-attr]
        if arch_entries is None:
            available = sorted(cls._catalog.keys())  # type: ignore[union-attr]
            raise KeyError(
                f"Architecture '{architecture}' not found in catalog. "
                f"Available architectures: {available}"
            )
        for entry in arch_entries:
            if entry.get("name") == model_name:
                return entry["path"]
        names = [e.get("name") for e in arch_entries]
        raise KeyError(
            f"Model '{model_name}' not found under architecture '{architecture}'. "
            f"Available models: {names}"
        )

    @classmethod
    def available_architectures(cls) -> List[str]:
        """Return all architecture names defined in the catalog."""
        cls._ensure_loaded()
        return sorted(cls._catalog.keys())  # type: ignore[union-attr]

    @classmethod
    def available_models(cls, architecture: str) -> List[Dict]:
        """Return model entries for a given architecture."""
        cls._ensure_loaded()
        return list(cls._catalog.get(architecture, []))  # type: ignore[union-attr]

    @classmethod
    def reset(cls) -> None:
        """Clear the cached catalog (intended for testing only)."""
        cls._catalog = None
