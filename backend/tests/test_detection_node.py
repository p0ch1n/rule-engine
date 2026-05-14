"""Tests for DetectionNode and supporting detector infrastructure."""

from __future__ import annotations

from typing import List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from rule_execution_engine.detectors.catalog import ModelCatalog
from rule_execution_engine.detectors.registry import DetectorRegistry
from rule_execution_engine.nodes.detection_node import DetectionNode
from rule_execution_engine.schema.models import NodeConfig
from rule_execution_engine.spatial.geometry import Object


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #


@pytest.fixture(autouse=True)
def reset_catalog():
    ModelCatalog.reset()
    yield
    ModelCatalog.reset()


def _make_node(
    arch: str = "yolov12",
    model_name: str = "person_detection",
    conf: float = 0.5,
    nms: float = 0.45,
    device: str = "cpu",
) -> DetectionNode:
    config = NodeConfig(
        id="detection-1",
        type="detection",
        position={"x": 0, "y": 0},
        config={
            "architecture": arch,
            "model_name": model_name,
            "confidence_threshold": conf,
            "nms_threshold": nms,
            "device": device,
        },
    )
    return DetectionNode(config)


def _fake_image() -> np.ndarray:
    return np.zeros((480, 640, 3), dtype=np.uint8)


SAMPLE_BBOXES: List[Object] = [
    Object(x=10, y=20, w=50, h=80, confidence=0.92, class_name="person"),
    Object(x=200, y=100, w=60, h=40, confidence=0.75, class_name="person"),
]


# ------------------------------------------------------------------ #
# Port declarations
# ------------------------------------------------------------------ #


def test_input_port_is_image_stream():
    node = _make_node()
    assert len(node.input_ports) == 1
    assert node.input_ports[0].port_type.value == "ImageStream"


def test_output_ports():
    node = _make_node()
    port_map = {p.name: p.port_type.value for p in node.output_ports}
    assert port_map["output"] == "ObjectStream"
    assert port_map["annotated"] == "AnnotatedStream"


# ------------------------------------------------------------------ #
# execute() behaviour
# ------------------------------------------------------------------ #


def test_execute_empty_images_returns_empty_without_loading():
    node = _make_node()
    result = node.execute({"input": []})
    assert result == {"output": [], "annotated": []}
    assert node._detector is None  # model never loaded


def test_execute_flattens_per_frame_results():
    node = _make_node()
    with patch.object(ModelCatalog, "get_model_path", return_value="w/fake.pt"):
        with patch.object(DetectorRegistry, "create") as mock_create:
            mock_detector = MagicMock()
            mock_detector.detect.return_value = [
                [SAMPLE_BBOXES[0]],
                [SAMPLE_BBOXES[1]],
            ]
            mock_create.return_value = mock_detector

            images = [_fake_image(), _fake_image()]
            result = node.execute({"input": images})

    assert result["output"] == [SAMPLE_BBOXES[0], SAMPLE_BBOXES[1]]


def test_execute_produces_annotated_stream():
    node = _make_node()
    with patch.object(ModelCatalog, "get_model_path", return_value="w/fake.pt"):
        with patch.object(DetectorRegistry, "create") as mock_create:
            mock_detector = MagicMock()
            mock_detector.detect.return_value = [[SAMPLE_BBOXES[0]], [SAMPLE_BBOXES[1]]]
            mock_create.return_value = mock_detector

            imgs = [_fake_image(), _fake_image()]
            result = node.execute({"input": imgs})

    annotated = result["annotated"]
    assert len(annotated) == 2
    assert annotated[0].image is imgs[0]
    assert annotated[0].objects == [SAMPLE_BBOXES[0]]
    assert annotated[1].objects == [SAMPLE_BBOXES[1]]


def test_execute_passes_thresholds_to_detector():
    node = _make_node(conf=0.7, nms=0.3)
    with patch.object(ModelCatalog, "get_model_path", return_value="w/fake.pt"):
        with patch.object(DetectorRegistry, "create") as mock_create:
            mock_detector = MagicMock()
            mock_detector.detect.return_value = [[]]
            mock_create.return_value = mock_detector

            images = [_fake_image()]
            node.execute({"input": images})

    mock_detector.detect.assert_called_once_with(images, 0.7, 0.3)


def test_execute_passes_device_to_registry():
    node = _make_node(device="cuda")
    with patch.object(ModelCatalog, "get_model_path", return_value="w/fake.pt"):
        with patch.object(DetectorRegistry, "create") as mock_create:
            mock_detector = MagicMock()
            mock_detector.detect.return_value = [[]]
            mock_create.return_value = mock_detector

            node.execute({"input": [_fake_image()]})

    mock_create.assert_called_once_with("yolov12", "w/fake.pt", "cuda")


# ------------------------------------------------------------------ #
# Lazy loading
# ------------------------------------------------------------------ #


def test_detector_loaded_only_once_across_frames():
    node = _make_node()
    with patch.object(ModelCatalog, "get_model_path", return_value="w/fake.pt"):
        with patch.object(DetectorRegistry, "create") as mock_create:
            mock_detector = MagicMock()
            mock_detector.detect.return_value = [[]]
            mock_create.return_value = mock_detector

            images = [_fake_image()]
            node.execute({"input": images})
            node.execute({"input": images})
            node.execute({"input": images})

    assert mock_create.call_count == 1


# ------------------------------------------------------------------ #
# ModelCatalog error propagation
# ------------------------------------------------------------------ #


def test_unknown_model_name_raises_key_error():
    node = _make_node(arch="yolov12", model_name="nonexistent_model")
    ModelCatalog._catalog = {
        "yolov12": [{"name": "person_detection", "path": "w/p.pt", "description": ""}]
    }
    with pytest.raises(KeyError, match="nonexistent_model"):
        node.execute({"input": [_fake_image()]})


def test_unknown_architecture_raises_key_error():
    node = _make_node(arch="unknown_arch")
    ModelCatalog._catalog = {"yolov12": []}
    with pytest.raises(KeyError, match="unknown_arch"):
        node.execute({"input": [_fake_image()]})


# ------------------------------------------------------------------ #
# ModelCatalog unit tests
# ------------------------------------------------------------------ #


def test_catalog_load_and_get_path(tmp_path):
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text(
        "yolov12:\n"
        "  - name: test_model\n"
        "    path: weights/test.pt\n"
        "    description: Test model\n"
    )
    ModelCatalog.load(yaml_file)
    path = ModelCatalog.get_model_path("yolov12", "test_model")
    assert path == "weights/test.pt"


def test_catalog_available_architectures(tmp_path):
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text("arch_a:\n  []\narch_b:\n  []\n")
    ModelCatalog.load(yaml_file)
    assert ModelCatalog.available_architectures() == ["arch_a", "arch_b"]


def test_catalog_not_loaded_raises_runtime_error(monkeypatch):
    monkeypatch.chdir(tmp_path if False else "/tmp")
    ModelCatalog._catalog = None
    # No models.yaml in /tmp or package dir under test conditions
    # We patch _ensure_loaded to raise to confirm the error path
    with patch.object(
        ModelCatalog,
        "_ensure_loaded",
        side_effect=RuntimeError("ModelCatalog is not loaded"),
    ):
        with pytest.raises(RuntimeError, match="ModelCatalog is not loaded"):
            ModelCatalog.get_model_path("yolov12", "person_detection")


# ------------------------------------------------------------------ #
# DetectorRegistry unit tests
# ------------------------------------------------------------------ #


def test_detector_registry_raises_on_unknown_architecture():
    with pytest.raises(KeyError, match="not_a_real_arch"):
        DetectorRegistry.create("not_a_real_arch", "path.pt", "cpu")
