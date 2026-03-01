"""
範例：載入前端 Export 的 pipeline JSON，對每一幀的偵測結果執行推論。

安裝：
    cd backend
    pip install -e .

執行：
    python examples/run_pipeline.py                     # 使用內建假資料
    python examples/run_pipeline.py my_pipeline.json    # 指定 pipeline 檔案
"""

from __future__ import annotations

import sys
from bbox_proc.engine.interpreter import Interpreter
from bbox_proc.spatial.geometry import BBox


# ── 1. 載入 pipeline ────────────────────────────────────────────────────────

pipeline_path = sys.argv[1] if len(sys.argv) > 1 else "pipeline.json"
pipeline = Interpreter.load(pipeline_path)

meta = pipeline.metadata
print(f"Loaded pipeline  tool_id={meta['tool_id']}  classes={meta['class_list']}")
print()


# ── 2. 模擬偵測器輸出（實際使用時替換成真實資料）───────────────────────────

def fake_detections() -> list[BBox]:
    """模擬一幀中偵測到的 bounding boxes。"""
    return [
        BBox(x=100, y=50,  w=80,  h=180, confidence=0.92, class_name="person"),
        BBox(x=300, y=200, w=150, h=90,  confidence=0.88, class_name="car"),
        BBox(x=120, y=60,  w=75,  h=170, confidence=0.76, class_name="person"),
    ]


# ── 3. 執行單幀推論 ─────────────────────────────────────────────────────────

bboxes = fake_detections()
result = pipeline.execute_frame(bboxes)

print(result)   # ExecutionResult(nodes=N, signals=M)
print()


# ── 4. 讀取 Logic 節點的觸發訊號 ────────────────────────────────────────────

signals = result.signals()
if not signals:
    print("No Logic nodes in pipeline.")
else:
    for node_id, signal in signals.items():
        triggered = signal["triggered"]
        label     = signal["label"]
        matched   = signal["matched_classes"]
        counts    = signal["class_counts"]

        status = "TRIGGERED" if triggered else "not triggered"
        print(f"[{node_id}] {status}  label={label!r}")
        print(f"  matched conditions : {matched}")
        print(f"  class counts       : {counts}")

        if triggered:
            print(f"  >>> ALERT: {label or node_id}")
        print()


# ── 5. 讀取任意節點的輸出（可選）────────────────────────────────────────────

# 範例：取得 id 為 "filter-1" 的節點通過篩選的 boxes
# passed = result.get_node_output("filter-1", port="output")
# if passed is not None:
#     print(f"filter-1 passed {len(passed)} boxes")
#     for box in passed:
#         print(f"  {box}")

# 取得所有節點的完整輸出（除錯用）
# import pprint
# pprint.pprint(result.all_outputs())
