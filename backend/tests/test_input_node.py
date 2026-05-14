"""Tests for InputNode and its helper functions."""

from __future__ import annotations

import base64
import io
from typing import List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from rule_execution_engine.nodes.input_node import (
    InputNode,
    InputNodeConfig,
    InputSourceType,
    _decode_images,
    _extract_frames,
    _strip_header,
    _video_suffix,
)
from rule_execution_engine.nodes.base import PortType
from rule_execution_engine.schema.models import InputFile, NodeConfig


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _make_png_b64(width: int = 4, height: int = 4) -> str:
    """Return a base64 data URI for a small solid-colour PNG."""
    from PIL import Image

    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def _make_node(
    source_type: str = "images",
    files: list | None = None,
    frame_step: int = 1,
    max_frames: int = 100,
) -> InputNode:
    config = NodeConfig(
        id="input-1",
        type="input",
        position={"x": 0, "y": 0},
        config={
            "source_type": source_type,
            "files": files or [],
            "frame_step": frame_step,
            "max_frames": max_frames,
        },
    )
    return InputNode(config)


# ------------------------------------------------------------------ #
# Port declarations
# ------------------------------------------------------------------ #

def test_input_ports_empty_for_embedded_modes():
    for mode in ("images", "video"):
        node = _make_node(source_type=mode)
        assert node.input_ports == [], f"source_type={mode} should be self-seeding"


def test_input_ports_image_stream_for_external_mode():
    node = _make_node(source_type="external")
    assert len(node.input_ports) == 1
    assert node.input_ports[0].name == "input"
    assert node.input_ports[0].port_type == PortType.ImageStream


def test_output_port_is_image_stream():
    node = _make_node()
    assert len(node.output_ports) == 1
    assert node.output_ports[0].name == "output"
    assert node.output_ports[0].port_type == PortType.ImageStream


# ------------------------------------------------------------------ #
# External mode — pass-through
# ------------------------------------------------------------------ #

def test_external_mode_passes_through_images():
    node = _make_node(source_type="external")
    frames = [np.zeros((4, 4, 3), dtype=np.uint8) for _ in range(2)]
    result = node.execute({"input": frames})
    assert result["output"] is frames


def test_external_mode_empty_input_returns_empty():
    node = _make_node(source_type="external")
    result = node.execute({})
    assert result == {"output": []}


def test_external_mode_does_not_cache():
    node = _make_node(source_type="external")
    frames_a = [np.zeros((2, 2, 3), dtype=np.uint8)]
    frames_b = [np.ones((2, 2, 3), dtype=np.uint8)]
    r1 = node.execute({"input": frames_a})
    r2 = node.execute({"input": frames_b})
    assert r1["output"] is frames_a
    assert r2["output"] is frames_b


# ------------------------------------------------------------------ #
# _strip_header
# ------------------------------------------------------------------ #

def test_strip_header_with_prefix():
    assert _strip_header("data:image/png;base64,ABCD") == "ABCD"


def test_strip_header_without_prefix():
    assert _strip_header("ABCD") == "ABCD"


# ------------------------------------------------------------------ #
# _video_suffix
# ------------------------------------------------------------------ #

def test_video_suffix_known():
    assert _video_suffix("clip.mp4") == ".mp4"
    assert _video_suffix("clip.AVI") == ".avi"


def test_video_suffix_unknown_defaults_to_mp4():
    assert _video_suffix("clip") == ".mp4"


# ------------------------------------------------------------------ #
# _decode_images
# ------------------------------------------------------------------ #

def test_decode_images_returns_bgr_array():
    data_uri = _make_png_b64(4, 4)
    files = [InputFile(filename="test.png", data=data_uri)]
    frames = _decode_images(files)

    assert len(frames) == 1
    arr = frames[0]
    assert isinstance(arr, np.ndarray)
    assert arr.shape == (4, 4, 3)
    assert arr.dtype == np.uint8


def test_decode_images_multiple_files():
    data_uri = _make_png_b64(2, 2)
    files = [InputFile(filename=f"img{i}.png", data=data_uri) for i in range(3)]
    frames = _decode_images(files)
    assert len(frames) == 3


def test_decode_images_empty_list():
    assert _decode_images([]) == []


def test_decode_images_bgr_channel_order():
    """Red pixel in RGB (255,0,0) should appear as (0,0,255) in BGR."""
    from PIL import Image

    img = Image.new("RGB", (1, 1), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    data_uri = f"data:image/png;base64,{b64}"

    frames = _decode_images([InputFile(filename="red.png", data=data_uri)])
    pixel = frames[0][0, 0]  # BGR
    assert pixel[0] == 0    # B
    assert pixel[1] == 0    # G
    assert pixel[2] == 255  # R


# ------------------------------------------------------------------ #
# InputNode.execute
# ------------------------------------------------------------------ #

def test_execute_returns_images():
    data_uri = _make_png_b64(8, 8)
    node = _make_node(
        source_type="images",
        files=[{"filename": "a.png", "data": data_uri}],
    )
    result = node.execute({})
    assert "output" in result
    assert len(result["output"]) == 1
    assert result["output"][0].shape == (8, 8, 3)


def test_execute_empty_files_returns_empty():
    node = _make_node(source_type="images", files=[])
    result = node.execute({})
    assert result == {"output": []}


def test_execute_caches_frames():
    data_uri = _make_png_b64(2, 2)
    node = _make_node(files=[{"filename": "x.png", "data": data_uri}])

    r1 = node.execute({})
    r2 = node.execute({})
    assert r1["output"] is r2["output"]


# ------------------------------------------------------------------ #
# Video path (cv2 mocked)
# ------------------------------------------------------------------ #

def _make_fake_cap(frames: List[np.ndarray]):
    """Build a mock cv2.VideoCapture that returns the given frames."""
    call_count = {"n": 0}

    def read_side_effect():
        i = call_count["n"]
        call_count["n"] += 1
        if i < len(frames):
            return True, frames[i]
        return False, None

    cap = MagicMock()
    cap.read.side_effect = read_side_effect
    return cap


def _mock_cv2_module(frames: List[np.ndarray]) -> MagicMock:
    """Build a complete mock cv2 module with a VideoCapture returning given frames."""
    fake_cap = _make_fake_cap(frames)
    mock_cv2 = MagicMock()
    mock_cv2.VideoCapture.return_value = fake_cap
    return mock_cv2


@patch("rule_execution_engine.nodes.input_node.tempfile.NamedTemporaryFile")
@patch("rule_execution_engine.nodes.input_node.os.unlink")
def test_execute_video_calls_cv2(mock_unlink, mock_tmpfile):
    import sys

    fake_frames = [np.zeros((4, 4, 3), dtype=np.uint8) for _ in range(3)]
    mock_cv2 = _mock_cv2_module(fake_frames)

    video_b64 = base64.b64encode(b"fake_video_bytes").decode()
    data_uri = f"data:video/mp4;base64,{video_b64}"

    mock_tmp = MagicMock()
    mock_tmp.__enter__ = MagicMock(return_value=mock_tmp)
    mock_tmp.__exit__ = MagicMock(return_value=False)
    mock_tmp.name = "/tmp/fake.mp4"
    mock_tmpfile.return_value = mock_tmp

    with patch.dict(sys.modules, {"cv2": mock_cv2}):
        node = _make_node(
            source_type="video",
            files=[{"filename": "clip.mp4", "data": data_uri}],
        )
        result = node.execute({})

    assert len(result["output"]) == 3


def test_video_frame_step():
    import sys

    fake_frames = [np.zeros((2, 2, 3), dtype=np.uint8) for _ in range(6)]
    mock_cv2 = _mock_cv2_module(fake_frames)

    with patch.dict(sys.modules, {"cv2": mock_cv2}):
        frames = _extract_frames("/fake/path.mp4", frame_step=2, max_frames=100)

    assert len(frames) == 3  # frames at index 0, 2, 4


def test_video_max_frames():
    import sys

    fake_frames = [np.zeros((2, 2, 3), dtype=np.uint8) for _ in range(10)]
    mock_cv2 = _mock_cv2_module(fake_frames)

    with patch.dict(sys.modules, {"cv2": mock_cv2}):
        frames = _extract_frames("/fake/path.mp4", frame_step=1, max_frames=4)

    assert len(frames) == 4


# ------------------------------------------------------------------ #
# Error handling
# ------------------------------------------------------------------ #

def test_video_import_error_without_cv2():
    video_b64 = base64.b64encode(b"x").decode()
    node = _make_node(
        source_type="video",
        files=[{"filename": "v.mp4", "data": video_b64}],
    )
    with patch.dict("sys.modules", {"cv2": None}):
        with pytest.raises(ImportError, match="opencv-python"):
            node.execute({})


def test_video_empty_files_returns_empty():
    node = _make_node(source_type="video", files=[])
    # _decode_video_frames returns [] early before touching cv2
    with patch("rule_execution_engine.nodes.input_node._decode_video_frames", return_value=[]):
        result = node.execute({})
    assert result == {"output": []}
