"""Tests for ImageAnalysisNode and its pixel measurement helpers."""

from __future__ import annotations

import numpy as np
import pytest

from rule_execution_engine.nodes.image_analysis_node import ImageAnalysisNode, measure_roi
from rule_execution_engine.schema.models import NodeConfig
from rule_execution_engine.spatial.annotated import AnnotatedFrame
from rule_execution_engine.spatial.geometry import Object


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _make_node(conditions, logic="AND") -> ImageAnalysisNode:
    config = NodeConfig(
        id="ia-1",
        type="image_analysis",
        position={"x": 0, "y": 0},
        config={"conditions": conditions, "logic": logic},
    )
    return ImageAnalysisNode(config)


def _solid_image(bgr: tuple, size: int = 50) -> np.ndarray:
    """Create a solid-colour HxWx3 uint8 image (BGR order)."""
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[:] = bgr
    return img


def _obj(x=0, y=0, w=50, h=50, cls="obj") -> Object:
    return Object(x=x, y=y, w=w, h=h, confidence=0.9, class_name=cls)


# ------------------------------------------------------------------ #
# Port declarations
# ------------------------------------------------------------------ #


def test_input_port_is_annotated_stream():
    node = _make_node([{"class_name": "", "field": "intensity", "operator": "gt", "threshold": 0}])
    assert node.input_ports[0].port_type.value == "AnnotatedStream"


def test_output_ports():
    node = _make_node([{"class_name": "", "field": "intensity", "operator": "gt", "threshold": 0}])
    port_names = {p.name: p.port_type.value for p in node.output_ports}
    assert port_names["output"] == "AnnotatedStream"
    assert port_names["objects"] == "ObjectStream"


# ------------------------------------------------------------------ #
# Empty input
# ------------------------------------------------------------------ #


def test_empty_input_returns_empty():
    node = _make_node([{"class_name": "", "field": "intensity", "operator": "gt", "threshold": 0}])
    result = node.execute({"input": []})
    assert result == {"output": [], "objects": []}


# ------------------------------------------------------------------ #
# measure_roi — RGB channels
# ------------------------------------------------------------------ #


def test_measure_blue_channel():
    img = _solid_image((200, 50, 30))  # BGR
    val = measure_roi(img, _obj(), "blue")
    assert abs(val - 200.0) < 0.5


def test_measure_green_channel():
    img = _solid_image((10, 180, 5))
    val = measure_roi(img, _obj(), "green")
    assert abs(val - 180.0) < 0.5


def test_measure_red_channel():
    img = _solid_image((0, 0, 255))  # pure red in BGR
    val = measure_roi(img, _obj(), "red")
    assert abs(val - 255.0) < 0.5


def test_measure_intensity_pure_red():
    img = _solid_image((0, 0, 255))  # R=255, G=0, B=0
    val = measure_roi(img, _obj(), "intensity")
    # ITU-R BT.601: 0.299*255 ≈ 76.2
    assert abs(val - 76.2) < 1.0


def test_measure_intensity_gray():
    img = _solid_image((128, 128, 128))
    val = measure_roi(img, _obj(), "intensity")
    assert abs(val - 128.0) < 0.5


# ------------------------------------------------------------------ #
# measure_roi — HSV
# ------------------------------------------------------------------ #


def test_measure_value_pure_red():
    img = _solid_image((0, 0, 255))  # V = 100%
    val = measure_roi(img, _obj(), "value")
    assert abs(val - 100.0) < 0.5


def test_measure_saturation_pure_red():
    img = _solid_image((0, 0, 255))  # S = 100%
    val = measure_roi(img, _obj(), "saturation")
    assert abs(val - 100.0) < 0.5


def test_measure_saturation_gray():
    img = _solid_image((128, 128, 128))  # S = 0 (achromatic)
    val = measure_roi(img, _obj(), "saturation")
    assert abs(val - 0.0) < 0.5


def test_measure_hue_pure_red():
    img = _solid_image((0, 0, 255))  # H ≈ 0°
    val = measure_roi(img, _obj(), "hue")
    assert abs(val - 0.0) < 1.0


def test_measure_hue_pure_green():
    img = _solid_image((0, 255, 0))  # H = 120°
    val = measure_roi(img, _obj(), "hue")
    assert abs(val - 120.0) < 1.0


def test_measure_hue_pure_blue():
    img = _solid_image((255, 0, 0))  # H = 240°
    val = measure_roi(img, _obj(), "hue")
    assert abs(val - 240.0) < 1.0


# ------------------------------------------------------------------ #
# measure_roi — edge cases
# ------------------------------------------------------------------ #


def test_measure_roi_empty_returns_zero():
    img = _solid_image((255, 255, 255))
    # Object that maps to zero-area after clipping
    val = measure_roi(img, Object(x=100, y=100, w=10, h=10, confidence=1.0, class_name="x"), "intensity")
    assert val == 0.0


def test_measure_roi_clipped_obj():
    """Object that extends beyond image bounds is clipped, not errored."""
    img = _solid_image((0, 0, 200), size=10)
    # Object partially outside
    val = measure_roi(img, Object(x=5, y=5, w=20, h=20, confidence=1.0, class_name="x"), "red")
    assert abs(val - 200.0) < 0.5


# ------------------------------------------------------------------ #
# Filtering logic
# ------------------------------------------------------------------ #


def test_obj_passes_intensity_threshold():
    img = _solid_image((0, 0, 255))  # intensity ≈ 76
    node = _make_node([{"class_name": "", "field": "intensity", "operator": "gt", "threshold": 50}])
    frame = AnnotatedFrame(image=img, objects=[_obj(cls="obj")])
    result = node.execute({"input": [frame]})
    assert len(result["output"]) == 1
    assert len(result["objects"]) == 1


def test_obj_fails_intensity_threshold():
    img = _solid_image((0, 0, 255))  # intensity ≈ 76
    node = _make_node([{"class_name": "", "field": "intensity", "operator": "gt", "threshold": 200}])
    frame = AnnotatedFrame(image=img, objects=[_obj(cls="obj")])
    result = node.execute({"input": [frame]})
    assert result["output"] == []
    assert result["objects"] == []


def test_frame_dropped_when_all_objects_fail():
    img = _solid_image((0, 0, 10))  # very low intensity
    node = _make_node([{"class_name": "", "field": "intensity", "operator": "gt", "threshold": 100}])
    frames = [
        AnnotatedFrame(image=img, objects=[_obj(cls="obj")]),  # fails
    ]
    result = node.execute({"input": frames})
    assert result["output"] == []


def test_partial_obj_survival_in_frame():
    """Some Objects pass, some fail — only survivors remain in the frame."""
    bright = _solid_image((255, 255, 255))  # intensity = 255
    dark = _solid_image((0, 0, 0))          # intensity = 0

    # Two objects at different positions on a composite image
    img = np.zeros((50, 100, 3), dtype=np.uint8)
    img[:, :50] = (255, 255, 255)  # left half bright
    img[:, 50:] = (0, 0, 0)        # right half dark

    b_bright = Object(x=0, y=0, w=50, h=50, confidence=0.9, class_name="obj")
    b_dark = Object(x=50, y=0, w=50, h=50, confidence=0.9, class_name="obj")

    node = _make_node([{"class_name": "", "field": "intensity", "operator": "gt", "threshold": 100}])
    frame = AnnotatedFrame(image=img, objects=[b_bright, b_dark])
    result = node.execute({"input": [frame]})

    assert len(result["output"]) == 1
    assert len(result["output"][0].objects) == 1
    assert result["output"][0].objects[0] == b_bright
    assert len(result["objects"]) == 1


def test_class_specific_condition():
    """Condition with class_name='person' does not affect 'car' objects."""
    img = _solid_image((0, 0, 10))  # would fail intensity > 100

    person = Object(x=0, y=0, w=50, h=50, confidence=0.9, class_name="person")
    car = Object(x=0, y=0, w=50, h=50, confidence=0.9, class_name="car")

    node = _make_node([
        {"class_name": "person", "field": "intensity", "operator": "gt", "threshold": 100}
    ])
    frame = AnnotatedFrame(image=img, objects=[person, car])
    result = node.execute({"input": [frame]})

    # 'car' passes through (no applicable conditions), 'person' fails
    assert len(result["objects"]) == 1
    assert result["objects"][0].class_name == "car"


def test_and_logic_both_must_pass():
    img = _solid_image((0, 0, 255))  # R=255, B=0
    # Both conditions must pass: red > 200 AND blue > 100 (blue is 0 → fails)
    node = _make_node(
        [
            {"class_name": "", "field": "red", "operator": "gt", "threshold": 200},
            {"class_name": "", "field": "blue", "operator": "gt", "threshold": 100},
        ],
        logic="AND",
    )
    frame = AnnotatedFrame(image=img, objects=[_obj()])
    result = node.execute({"input": [frame]})
    assert result["output"] == []


def test_or_logic_one_suffices():
    img = _solid_image((0, 0, 255))  # R=255, B=0
    # OR: red > 200 (passes) OR blue > 100 (fails) → overall passes
    node = _make_node(
        [
            {"class_name": "", "field": "red", "operator": "gt", "threshold": 200},
            {"class_name": "", "field": "blue", "operator": "gt", "threshold": 100},
        ],
        logic="OR",
    )
    frame = AnnotatedFrame(image=img, objects=[_obj()])
    result = node.execute({"input": [frame]})
    assert len(result["objects"]) == 1


# ------------------------------------------------------------------ #
# Chained frames and obj flattening
# ------------------------------------------------------------------ #


def test_objects_flattened_across_frames():
    img = _solid_image((200, 200, 200))
    b1 = _obj(x=0, y=0, w=10, h=10, cls="a")
    b2 = _obj(x=10, y=0, w=10, h=10, cls="b")
    node = _make_node([{"class_name": "", "field": "intensity", "operator": "gt", "threshold": 0}])
    frames = [
        AnnotatedFrame(image=img, objects=[b1]),
        AnnotatedFrame(image=img, objects=[b2]),
    ]
    result = node.execute({"input": frames})
    assert len(result["output"]) == 2
    assert result["objects"] == [b1, b2]


def test_with_objects_shares_image_reference():
    img = _solid_image((100, 100, 100))
    frame = AnnotatedFrame(image=img, objects=[_obj()])
    new_frame = frame.with_objects([])
    assert new_frame.image is img  # no copy
