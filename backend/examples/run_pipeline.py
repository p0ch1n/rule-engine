"""
範例：載入 pipeline JSON，執行推論，並顯示每個節點的輸出結果。

安裝：
    cd backend
    pip install -e .

執行：
    python examples/run_pipeline.py                              # 使用 examples/pipeline.json（物件 pipeline）
    python examples/run_pipeline.py examples/pipeline.json       # 明確指定
    python examples/run_pipeline.py ../pipeline-config.example.json  # 影像 pipeline（需要真實模型）
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import numpy as np

from rule_execution_engine.engine.interpreter import ExecutionResult, Interpreter
from rule_execution_engine.schema.models import PipelineConfig
from rule_execution_engine.spatial.geometry import Object


# ── 1. 載入 pipeline ────────────────────────────────────────────────────────

_default = Path(__file__).parent / "pipeline.json"
pipeline_path = sys.argv[1] if len(sys.argv) > 1 else str(_default)
pipeline = Interpreter.load(pipeline_path)

meta = pipeline.metadata
print(f"Pipeline: {pipeline_path}")
print(f"  tool_id : {meta['tool_id']}")
print(f"  classes : {meta['class_list']}")
print()


# ── 2. 輸入資料 ──────────────────────────────────────────────────────────────
#
#  物件 pipeline（Filter / Merge / Logic）：
#      pass input_objects=[...]
#
#  影像 pipeline（Input[external] → Detection → ...）：
#      pass images=[np.ndarray, ...]
#
# 這裡預設使用假的偵測結果（物件 pipeline）。

def fake_detections() -> list[Object]:
    return [
        Object(x=100, y=50,  w=80,  h=180, confidence=0.92, class_name="person"),
        Object(x=300, y=200, w=150, h=90,  confidence=0.88, class_name="car"),
        Object(x=120, y=60,  w=75,  h=170, confidence=0.76, class_name="person"),
    ]


# ── 3. 執行 ─────────────────────────────────────────────────────────────────

result = pipeline.execute_frame(input_objects=fake_detections())
print(result)
print()


# ── 4. 顯示每個節點的完整輸出 ────────────────────────────────────────────────

def _print_value(value: Any) -> None:
    """印出單一 port 的值（依型別選擇格式）。"""
    if isinstance(value, list) and value and isinstance(value[0], Object):
        print(f"      ObjectStream  ({len(value)} objects)")
        for obj in value:
            print(f"        {obj.class_name:<14} conf={obj.confidence:.3f}"
                  f"  [{obj.x:.0f},{obj.y:.0f}  {obj.w:.0f}×{obj.h:.0f}]")

    elif isinstance(value, list) and value and isinstance(value[0], np.ndarray):
        print(f"      ImageStream   ({len(value)} frames)")
        for i, frame in enumerate(value):
            print(f"        frame[{i}]  shape={frame.shape}")

    elif isinstance(value, list) and value and hasattr(value[0], "objects"):
        # AnnotatedFrame list
        print(f"      AnnotatedStream  ({len(value)} frames)")
        for i, af in enumerate(value):
            print(f"        frame[{i}]  shape={af.image.shape}  "
                  f"objects={len(af.objects)}")
            for obj in af.objects:
                print(f"          {obj.class_name:<14} conf={obj.confidence:.3f}")

    elif isinstance(value, dict) and "triggered" in value:
        triggered = value["triggered"]
        status = "TRIGGERED ✓" if triggered else "not triggered"
        print(f"      LogicSignal  {status}")
        print(f"        label          : {value.get('label', '')!r}")
        print(f"        matched_classes: {value.get('matched_classes', [])}")
        print(f"        class_counts   : {value.get('class_counts', {})}")
        print(f"        total_count    : {value.get('total_count', 0)}")

    elif isinstance(value, list) and len(value) == 0:
        print(f"      (empty)")

    else:
        print(f"      {value!r}")


def print_node_outputs(result: ExecutionResult, config: PipelineConfig) -> None:
    node_types: Dict[str, str] = {n.id: n.type for n in config.nodes}
    outputs = result.all_outputs()

    print("=" * 56)
    print("NODE OUTPUTS")
    print("=" * 56)

    for node_id, ports in outputs.items():
        node_type = node_types.get(node_id, "?")
        print(f"\n  [{node_id}]  type={node_type}")
        for port_name, value in ports.items():
            print(f"    └─ {port_name}")
            _print_value(value)

    print()


print_node_outputs(result, pipeline.config)


# ── 5. 觸發訊號摘要 ──────────────────────────────────────────────────────────

signals = result.signals()
if signals:
    print("=" * 56)
    print("SIGNAL SUMMARY")
    print("=" * 56)
    for node_id, signal in signals.items():
        triggered = signal["triggered"]
        label = signal["label"]
        status = "TRIGGERED" if triggered else "not triggered"
        print(f"  [{node_id}] {status}  label={label!r}")
        if triggered:
            print(f"  >>> ALERT: {label or node_id}")
    print()
