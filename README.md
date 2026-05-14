# rule-engine

Real-time bounding box processing pipeline — visual editor (React + Vite) + Python execution engine.

## Architecture

```
rule-engine/
├── frontend/   # React 18 + Vite + React-Flow canvas editor
├── backend/    # Python 3.9+ execution engine (pure library)
├── schema/     # Shared JSON Schema (Draft-07)
└── docs/       # spec.md
```

### Design Principles

- **Registry Pattern**: adding a new node type requires zero changes to the framework.
- **Immutable data**: `Object` is frozen; all transformations return new instances.
- **Pure library engine**: `Pipeline.execute_frame(objects)` — no side effects; caller decides what to do with results.
- **Single-frame processing**: stateless by design, safe for concurrent frame processing.

---

## Backend

### Install

```bash
cd backend
pip install -e ".[dev]"
```

### Run tests

```bash
pytest tests/ -v
```

Coverage: **89%** (requirement: 80%).

### Run a pipeline exported from the frontend

```bash
# Run the bundled example (uses built-in fake detections)
python examples/run_pipeline.py

# Run with your own exported pipeline file
python examples/run_pipeline.py my_pipeline.json
```

Full annotated source: [`backend/examples/run_pipeline.py`](backend/examples/run_pipeline.py)

### API usage

**Object pipeline** (external detections):

```python
from rule_execution_engine.engine.interpreter import Interpreter
from rule_execution_engine.spatial.geometry import Object

# ── Load ──────────────────────────────────────────────────────────────────
pipeline = Interpreter.load("pipeline.json")        # from file
# pipeline = Interpreter.from_json(json_string)     # from string (API / stream)

# ── Execute a frame ───────────────────────────────────────────────────────
objects = [
    Object(x=100, y=50, w=80,  h=180, confidence=0.92, class_name="person"),
    Object(x=300, y=200, w=150, h=90,  confidence=0.88, class_name="car"),
]
result = pipeline.execute_frame(input_objects=objects)

# ── Read results ──────────────────────────────────────────────────────────
for node_id, signal in result.signals().items():
    if signal["triggered"]:
        print(f"ALERT [{node_id}] label={signal['label']!r}  counts={signal['class_counts']}")

# Get a specific node's output boxes
passed_boxes = result.get_node_output("filter-1", port="output")

# Full output map (all nodes, all ports)
all_outputs = result.all_outputs()
```

**Image pipeline** — `InputNode` in external mode receives images at runtime:

```python
import cv2

pipeline = Interpreter.load("pipeline_with_input_node.json")
# pipeline.json was exported from the UI with InputNode set to "External" mode

cap = cv2.VideoCapture(0)
while True:
    ok, frame = cap.read()
    if not ok:
        break
    # frame is a BGR np.ndarray — pass it through InputNode into DetectionNode
    result = pipeline.execute_frame(images=[frame])
    for node_id, signal in result.signals().items():
        if signal["triggered"]:
            print(f"ALERT [{node_id}]")
```

#### `Object` fields

| Field | Type | Description |
|---|---|---|
| `x`, `y` | float | Top-left corner (pixels) |
| `w`, `h` | float | Width and height (pixels) |
| `confidence` | float | Detector confidence score [0, 1] |
| `class_name` | str | Object class label |
| `metadata` | dict | Optional key/value pairs (lineage, relation info, …) |

#### `ExecutionResult` methods

| Method | Returns | Description |
|---|---|---|
| `signals()` | `dict[node_id, signal]` | All Logic node trigger states |
| `get_node_output(id, port)` | any | Output of a specific node port |
| `all_outputs()` | `dict` | Full per-node output map |

### Extending with a new node type

```python
# my_node.py
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from rule_execution_engine.nodes.base import BaseNode, PortDefinition, PortType
from rule_execution_engine.nodes.registry import NodeRegistry

class MyNodeConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    min_count: int = 1          # JSON key: "minCount"
    threshold: float = 0.5     # JSON key: "threshold"

@NodeRegistry.register("my_node", config_class=MyNodeConfig)
class MyNode(BaseNode):
    @property
    def input_ports(self): ...
    @property
    def output_ports(self): ...
    def execute(self, inputs): ...
```

No other files need modification.

### Node vs Detector — when to use which

`detectors/` is a **strategy layer inside `DetectionNode`**, not a parallel concept to nodes. Choosing between them:

| Scenario | Use |
|---|---|
| New ML architecture running locally (YOLO, RT-DETR, …) | `BaseDetector` in `detectors/` |
| API-based model (OpenAI VLM, cloud vision API, …) | `BaseNode` directly in `nodes/` |
| Any processing block that doesn't load model weights | `BaseNode` directly in `nodes/` |

**Why API-based models are `BaseNode`, not `BaseDetector`:**  
`BaseDetector` assumes `model_path`, `device`, and `nms_threshold` — none of which apply to a REST API call. A VLM node also isn't constrained to returning `List[Object]`; it may output text, structured data, or a new port type. Implement it as a `BaseNode` with its own config and ports.

**Adding a new local detector architecture:**

```python
# detectors/my_arch.py
from rule_execution_engine.detectors.base import BaseDetector
from rule_execution_engine.detectors.registry import DetectorRegistry

@DetectorRegistry.register("my_arch")
class MyArchDetector(BaseDetector):
    def _load_model(self): ...
    def _run_inference(self, images, confidence_threshold, nms_threshold): ...
```

Then add an entry to `backend/models.yaml` and mirror it in the frontend's `MODELS_BY_ARCHITECTURE`. No other files need modification.

---

## Frontend

### Install & run

```bash
cd frontend
npm install
npm run dev       # http://localhost:5173
npm run build     # production bundle
npm run type-check
```

### Features

- Drag nodes from the left palette onto the canvas.
- Connect ports — type validation prevents invalid wires.
- **InputNode** — upload images or video for UI prototyping, or switch to External mode for deployment pipelines that inject frames at runtime.
- Class list auto-inferred from upstream FilterNodes.
- **Export JSON** — downloads `pipeline.json` matching the shared schema.
- **Import JSON** — reloads a saved pipeline from disk.

---

## JSON Schema

Located at `schema/pipeline.schema.json` (Draft-07). Shared between frontend validation and backend Pydantic models.

```json
{
  "version": "1.0",
  "metadata": { "toolId": "cam-01", "classList": ["person", "car"] },
  "nodes": [
    {
      "id": "filter-1", "type": "filter",
      "position": {"x": 100, "y": 100},
      "config": {
        "conditions": [{ "className": "person", "field": "confidence", "operator": "gte", "threshold": 0.7 }],
        "logic": "AND"
      }
    }
  ],
  "edges": [
    { "id": "e1", "source": "filter-1", "sourcePort": "output",
      "target": "logic-1", "targetPort": "input" }
  ]
}
```

---

## Port Type System

| Type | Color | Description | Connects to |
|---|---|---|---|
| `ObjectStream` | blue | Single-branch Object stream | ObjectStream, Collection |
| `Collection` | amber | Multi-branch aggregate (with lineage) | Collection |
| `LogicSignal` | green | Boolean trigger + metadata | LogicSignal |
| `ImageStream` | purple | Per-frame images (BGR `np.ndarray`) | ImageStream |
| `AnnotatedStream` | orange | Images paired with bounding boxes | AnnotatedStream |
| `ReferenceImageStream` | rose | Static config-time images | ReferenceImageStream |

**InputNode**: self-seeding (images/video mode) or ImageStream pass-through (external mode)  
**DetectionNode**: ImageStream → ObjectStream + AnnotatedStream  
**FilterNode / RelationNode**: ObjectStream → ObjectStream  
**MergeNode**: N × ObjectStream → Collection  
**LogicNode**: ObjectStream or Collection → LogicSignal

> An `ObjectStream` can connect directly to a `LogicNode` without going through a `MergeNode`.
