"""InputNode — image source that supports both embedded (UI) and external (deployment) modes."""

from __future__ import annotations

import base64
import io
import os
import tempfile
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from rule_execution_engine.nodes.base import BaseNode, PortDefinition, PortType
from rule_execution_engine.nodes.registry import NodeRegistry
from rule_execution_engine.schema.models import InputFile


# ------------------------------------------------------------------ #
# Config schema
# ------------------------------------------------------------------ #


class InputSourceType(str, Enum):
    images = "images"      # embedded: base64 image files stored in config
    video = "video"        # embedded: base64 video file stored in config
    external = "external"  # deployment: images injected via execute_frame(images=[...])


class InputNodeConfig(BaseModel):
    """Config for InputNode.

    embedded modes (images / video): files are stored as base64 in the config;
        the node is self-seeding and produces frames on every execute() call.
    external mode: no stored files; the scheduler injects images provided by
        the caller via pipeline.execute_frame(images=[...]) on each call.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    source_type: InputSourceType = InputSourceType.images
    files: List[InputFile] = Field(default_factory=list)
    frame_step: int = Field(default=1, ge=1)
    max_frames: int = Field(default=100, ge=1)


@NodeRegistry.register("input", config_class=InputNodeConfig)
class InputNode(BaseNode):
    """Image source node bridging UI prototyping and production deployment.

    Embedded modes (images / video)
        input_ports = []  ← self-seeding; scheduler skips injection.
        On execute() the base64 files from config are decoded to BGR arrays
        and cached for the lifetime of the Pipeline instance.

    External mode
        input_ports = [ImageStream]  ← scheduler seeds this node with the
        images supplied by the caller via pipeline.execute_frame(images=[...]).
        execute() is a pure pass-through; no caching, no file I/O.

    Output:
        output (ImageStream) — List[np.ndarray], BGR channel order.
    """

    def __init__(self, config: Any) -> None:
        super().__init__(config)
        self._cache: Optional[List[np.ndarray]] = None

    @property
    def input_ports(self) -> List[PortDefinition]:
        cfg: InputNodeConfig = self._parsed_config  # type: ignore[assignment]
        if cfg.source_type == InputSourceType.external:
            return [PortDefinition("input", PortType.ImageStream, "Frames from execute_frame(images=[...])")]
        return []

    @property
    def output_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition("output", PortType.ImageStream, "Image frames (BGR)")
        ]

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        cfg: InputNodeConfig = self._parsed_config  # type: ignore[assignment]
        if cfg.source_type == InputSourceType.external:
            return {"output": inputs.get("input", [])}
        if self._cache is None:
            self._cache = self._load_frames()
        return {"output": self._cache}

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _load_frames(self) -> List[np.ndarray]:
        cfg: InputNodeConfig = self._parsed_config  # type: ignore[assignment]
        if cfg.source_type == InputSourceType.images:
            return _decode_images(cfg.files)
        return _decode_video_frames(cfg.files, cfg.frame_step, cfg.max_frames)


# ------------------------------------------------------------------ #
# Module-level helpers (easier to test in isolation)
# ------------------------------------------------------------------ #

def _decode_images(files: List[InputFile]) -> List[np.ndarray]:
    """Decode a list of base64 image files → BGR numpy arrays."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "Image decoding requires Pillow. Install it with: pip install Pillow"
        ) from exc

    frames: List[np.ndarray] = []
    for f in files:
        raw = base64.b64decode(_strip_header(f.data))
        img_rgb = Image.open(io.BytesIO(raw)).convert("RGB")
        arr = np.array(img_rgb)
        frames.append(arr[:, :, ::-1].copy())  # RGB → BGR
    return frames


def _decode_video_frames(
    files: List[InputFile],
    frame_step: int,
    max_frames: int,
) -> List[np.ndarray]:
    """Decode a base64 video file → list of BGR frame arrays."""
    try:
        import cv2  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "Video decoding requires opencv-python. "
            "Install it with: pip install opencv-python"
        ) from exc

    if not files:
        return []

    f = files[0]
    raw = base64.b64decode(_strip_header(f.data))
    suffix = _video_suffix(f.filename)

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    try:
        return _extract_frames(tmp_path, frame_step, max_frames)
    finally:
        os.unlink(tmp_path)


def _extract_frames(path: str, frame_step: int, max_frames: int) -> List[np.ndarray]:
    import cv2  # type: ignore[import]

    cap = cv2.VideoCapture(path)
    frames: List[np.ndarray] = []
    idx = 0
    while len(frames) < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % frame_step == 0:
            frames.append(frame)  # already BGR from OpenCV
        idx += 1
    cap.release()
    return frames


def _strip_header(data: str) -> str:
    """Remove 'data:<mime>;base64,' prefix if present."""
    if "," in data:
        return data.split(",", 1)[1]
    return data


def _video_suffix(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return ext if ext else ".mp4"
