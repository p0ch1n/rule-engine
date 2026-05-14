# Node Developer Guide

This guide explains how to add a new processing node to rule-engine. The system is designed so that adding a node requires changes only inside well-defined boundaries — the framework discovers new types automatically.

---

## Table of Contents

1. [Port Type System](#1-port-type-system)
2. [Node Categories](#2-node-categories)
3. [Adding a Backend Node](#3-adding-a-backend-node)
4. [Adding a Frontend Node](#4-adding-a-frontend-node)
5. [Common Patterns](#5-common-patterns)
   - [Frame-by-frame Processing Node](#51-frame-by-frame-processing-node)
   - [Self-seeding Reference Image Node](#52-self-seeding-reference-image-node)
   - [Template Matching Node (end-to-end example)](#53-template-matching-node-end-to-end-example)
   - [Dynamic-Mode Source Node (InputNode Pattern)](#54-dynamic-mode-source-node-inputnode-pattern)
6. [Schema and Serialization](#6-schema-and-serialization)
7. [Testing Requirements](#7-testing-requirements)
8. [Checklist](#8-checklist)

---

## 1. Port Type System

Every connection in the pipeline carries a typed value. Connecting ports of incompatible types is rejected both at canvas editing time (frontend) and validated implicitly at runtime (backend).

### Port Types

| Type | Backend enum | Frontend enum | Color | Carries |
|------|-------------|---------------|-------|---------|
| `ObjectStream` | `PortType.ObjectStream` | `PortType.ObjectStream` | `#3b82f6` blue | `List[Object]` |
| `Collection` | `PortType.Collection` | `PortType.Collection` | `#f59e0b` amber | `List[Object]` with lineage metadata |
| `LogicSignal` | `PortType.LogicSignal` | `PortType.LogicSignal` | `#22c55e` green | `bool` + metadata dict |
| `ImageStream` | `PortType.ImageStream` | `PortType.ImageStream` | `#7c3aed` purple | `List[np.ndarray]` — per-frame pipeline input |
| `AnnotatedStream` | `PortType.AnnotatedStream` | `PortType.AnnotatedStream` | `#f97316` orange | `List[AnnotatedFrame]` — image + obj pairs |
| `ReferenceImageStream` | `PortType.ReferenceImageStream` | `PortType.ReferenceImageStream` | `#e11d48` rose | `List[np.ndarray]` — static config-time images |

### Key Distinction: ImageStream vs ReferenceImageStream

| | `ImageStream` | `ReferenceImageStream` |
|---|---|---|
| **Changes per frame?** | Yes | No |
| **Source** | `pipeline.execute_frame(images=[...])` call | Node's own config (file path, base64, etc.) |
| **Typical node** | `DetectionNode` | `TemplateLoaderNode`, `BackgroundModelNode` |
| **Scheduler behavior** | Injected by scheduler on every run | Node loads once, caches in `self._ref` |

### Compatibility Rules

A source port can only connect to a target port of the same type, with one exception:

```
ObjectStream  →  ObjectStream   ✓
ObjectStream  →  Collection  ✓  (single-stream shortcut to LogicNode)
Collection →  Collection  ✓
LogicSignal → LogicSignal ✓
ImageStream → ImageStream ✓
AnnotatedStream → AnnotatedStream ✓
ReferenceImageStream → ReferenceImageStream ✓
```

All cross-type connections are rejected.

### Port Colors — Always Use the Canonical Map

Never hardcode color hex strings in node components. Import `PORT_TYPE_COLORS`:

```typescript
import { PORT_TYPE_COLORS, PortType } from '@/nodes/types'

// In your node component:
<Handle style={{ background: PORT_TYPE_COLORS[PortType.ReferenceImageStream] }} />
```

The map lives in `frontend/src/nodes/types.ts` and is the single source of truth.

---

## 2. Node Categories

Before implementing, decide which category your node falls into:

| Category | input_ports | Scheduler behavior | Example |
|---|---|---|---|
| **Pipeline-input source** | `[PortDefinition("input", PortType.ImageStream)]` | Injected with `images` from `execute_frame` | `DetectionNode` |
| **Object-input source** | `[PortDefinition("input", PortType.ObjectStream)]` | Injected with `input_objects` from `execute_frame` | legacy source nodes |
| **Self-seeding source** | `[]` (empty list) | Not injected — receives `{}`, loads own data | `TemplateLoaderNode`, `InputNode` (images/video mode) |
| **Dynamic-mode source** | `[]` or `[ImageStream]` — determined at runtime from config | Self-seeding OR injected depending on `source_type` config field | `InputNode` |
| **Processing node** | one or more ports | Receives upstream outputs via edges | `FilterNode`, `ImageAnalysisNode` |

`InputNode` is the only built-in node whose `input_ports` changes based on config. See §5.4 for the pattern.

---

## 3. Adding a Backend Node

### Step 1: Create the node file

Create `backend/rule_execution_engine/nodes/your_node.py`. **The config class lives in the same file** — no changes to `schema/models.py` are needed.

```python
"""YourNode — one-line description."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from rule_execution_engine.nodes.base import BaseNode, PortDefinition, PortType
from rule_execution_engine.nodes.registry import NodeRegistry


class YourNodeConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    # add any other config fields here


@NodeRegistry.register("your_type", config_class=YourNodeConfig)
class YourNode(BaseNode):

    @property
    def input_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition("input", PortType.ObjectStream, "Incoming bounding boxes"),
        ]

    @property
    def output_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition("output", PortType.ObjectStream, "Filtered bounding boxes"),
        ]

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        objects = self._get_objects(inputs, "input")
        result = [b for b in objects if self._passes(b)]
        return {"output": result}

    def _passes(self, obj) -> bool:
        ...
```

### Step 2: Register the import

Add one line to `backend/rule_execution_engine/nodes/__init__.py`:

```python
from rule_execution_engine.nodes import your_node as _your_node  # noqa: F401
```

That is all. `NodeRegistry.create(config)` will find the new type automatically.

### Accessing Config in execute()

`BaseNode.__init__` calls `config.parse_config()`, which looks up the registered `config_class` and returns a typed instance as `self._parsed_config`. Cast it to your config type inside `execute()`:

```python
def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    cfg: YourNodeConfig = self._parsed_config  # type: ignore[assignment]
    ...
```

### Object is Immutable

`Object` is a frozen dataclass. All spatial transforms return new instances. Never modify a Object in place.

### Python 3.9 Compatibility

Use `List[T]` and `Dict[K, V]` from `typing`, not `list[T]` or `dict[K, V]`:

```python
# Correct
from typing import Any, Dict, List
def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]: ...

# Wrong (Python 3.10+ only)
def execute(self, inputs: dict[str, Any]) -> dict[str, Any]: ...
```

---

## 4. Adding a Frontend Node

### Step 1: Create the node directory

```
frontend/src/nodes/YourNode/
├── definition.ts    # port declarations + defaultConfig
└── index.tsx        # React component
```

### Step 2: definition.ts

```typescript
import type { NodeDefinition } from '../types'
import { PortType } from '../types'
import { YourNodeComponent } from './index'

export const YourNodeDefinition: NodeDefinition = {
  type: 'your_type',           // must match backend @NodeRegistry.register value
  label: 'Your Node',
  description: 'One-line description shown in the canvas sidebar',
  inputPorts: [
    {
      name: 'input',
      portType: PortType.ObjectStream,
      label: 'Objects',
      description: 'Incoming bounding boxes',
    },
  ],
  outputPorts: [
    {
      name: 'output',
      portType: PortType.ObjectStream,
      label: 'Filtered',
      description: 'Filtered bounding boxes',
    },
  ],
  defaultConfig: {
    threshold: 0.5,
  },
  component: YourNodeComponent,
}
```

### Step 3: index.tsx

```typescript
import { Handle, Position } from 'reactflow'
import { PORT_TYPE_COLORS, PortType } from '@/nodes/types'
import type { NodeComponentProps } from '@/nodes/types'
import { registerNodeType } from '@/nodes/registry'
import { YourNodeDefinition } from './definition'

registerNodeType(YourNodeDefinition)

export function YourNodeComponent({ id, data, selected }: NodeComponentProps) {
  return (
    <div style={{ border: selected ? '2px solid #3b82f6' : '2px solid #e5e7eb', borderRadius: 8, padding: 12, background: '#fff', minWidth: 180 }}>
      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        style={{ background: PORT_TYPE_COLORS[PortType.ObjectStream], width: 12, height: 12 }}
      />

      <div style={{ fontWeight: 600, marginBottom: 8 }}>{data.label}</div>

      {/* Config fields */}
      <label style={{ fontSize: 12 }}>
        Threshold
        <input type="number" defaultValue={data.config.threshold as number} style={{ width: '100%' }} />
      </label>

      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        style={{ background: PORT_TYPE_COLORS[PortType.ObjectStream], width: 12, height: 12 }}
      />
    </div>
  )
}
```

### Step 4: Register the import

Add one line to `frontend/src/nodes/index.ts`:

```typescript
import './YourNode'
```

---

## 5. Common Patterns

### 5.1 Frame-by-frame Processing Node

Receives `AnnotatedStream` (image + objects), does per-obj ROI analysis, outputs filtered result.

```python
def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    frames: List[AnnotatedFrame] = inputs.get("input", [])
    out_frames: List[AnnotatedFrame] = []
    out_objects: List[Object] = []

    for frame in frames:
        survivors = [b for b in frame.objects if self._analyze_roi(frame.image, b)]
        if survivors:
            out_frames.append(frame.with_objects(survivors))   # shares image ref, no copy
            out_objects.extend(survivors)

    return {"output": out_frames, "objects": out_objects}
```

`AnnotatedFrame.with_objects()` returns a new frame sharing the same image array (zero copy).

### 5.2 Self-seeding Reference Image Node

A node that loads a static reference image from config (e.g., a template for template matching). It declares **no input ports** and caches the loaded image across frames.

```python
@NodeRegistry.register("template_loader")
class TemplateLoaderNode(BaseNode):

    def __init__(self, config: NodeConfig) -> None:
        super().__init__(config)
        raw = config.config or {}
        self._path: str = str(raw.get("image_path", ""))
        self._cache: Optional[List[np.ndarray]] = None   # loaded on first execute

    @property
    def input_ports(self) -> List[PortDefinition]:
        return []   # ← empty: self-seeding, scheduler will NOT inject pipeline input

    @property
    def output_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition("output", PortType.ReferenceImageStream, "Template image"),
        ]

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        if self._cache is None:
            import cv2
            img = cv2.imread(self._path)
            if img is None:
                raise RuntimeError(f"TemplateLoaderNode: cannot read image at {self._path!r}")
            self._cache = [img]
        return {"output": self._cache}
```

**Why `input_ports = []` matters**: The scheduler only injects per-frame data into nodes that explicitly declare input ports. With an empty list the node is left alone — `execute({})` is called and the node provides its own data.

### 5.3 Template Matching Node (end-to-end example)

A node that receives both target frames (`AnnotatedStream`) and a reference template (`ReferenceImageStream`), filters objects whose ROI matches the template above a threshold.

**Backend:**

```python
@NodeRegistry.register("template_match")
class TemplateMatchNode(BaseNode):

    @property
    def input_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition("input",    PortType.AnnotatedStream,     "Target frames"),
            PortDefinition("template", PortType.ReferenceImageStream, "Template image"),
        ]

    @property
    def output_ports(self) -> List[PortDefinition]:
        return [
            PortDefinition("output", PortType.AnnotatedStream, "Matched frames"),
            PortDefinition("objects", PortType.ObjectStream,       "Matched objects (flat)"),
        ]

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        frames:    List[AnnotatedFrame] = inputs.get("input",    [])
        templates: List[np.ndarray]     = inputs.get("template", [])

        if not templates:
            return {"output": [], "objects": []}

        template = templates[0]   # use first reference image
        cfg = self._cfg

        out_frames, out_objects = [], []
        for frame in frames:
            survivors = [
                b for b in frame.objects
                if self._match_score(frame.image, b, template) >= cfg.threshold
            ]
            if survivors:
                out_frames.append(frame.with_objects(survivors))
                out_objects.extend(survivors)

        return {"output": out_frames, "objects": out_objects}
```

**Canvas wiring:**

```
TemplateLoaderNode ──(ReferenceImageStream)──► TemplateMatchNode.template
DetectionNode.annotated ─(AnnotatedStream)───► TemplateMatchNode.input
TemplateMatchNode.objects ──(ObjectStream)────────► LogicNode
```

**Frontend definition:**

```typescript
inputPorts: [
  { name: 'input',    portType: PortType.AnnotatedStream,     label: 'Frames'    },
  { name: 'template', portType: PortType.ReferenceImageStream, label: 'Template'  },
],
outputPorts: [
  { name: 'output', portType: PortType.AnnotatedStream, label: 'Matched frames' },
  { name: 'objects', portType: PortType.ObjectStream,       label: 'Matched Objects' },
],
```

### 5.4 Dynamic-Mode Source Node (InputNode Pattern)

`InputNode` demonstrates a node whose `input_ports` property is **not static** — it returns different values based on the `source_type` field in config. This lets a single node behave as either a self-seeding embedded source or a runtime-injectable source, without any changes to the scheduler.

```python
@property
def input_ports(self) -> List[PortDefinition]:
    cfg: InputNodeConfig = self._parsed_config
    if cfg.source_type == InputSourceType.external:
        # scheduler will inject images from execute_frame(images=[...])
        return [PortDefinition("input", PortType.ImageStream, "Frames from execute_frame(images=[...])")]
    # images / video: self-seeding; scheduler leaves this node alone
    return []

def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    cfg: InputNodeConfig = self._parsed_config
    if cfg.source_type == InputSourceType.external:
        return {"output": inputs.get("input", [])}  # pure pass-through
    if self._cache is None:
        self._cache = self._load_frames()            # decode base64 files once
    return {"output": self._cache}
```

**Why this works**: The scheduler calls `node.input_ports` once per `Pipeline.execute_frame()` call to determine which nodes to seed. When the JSON config field `sourceType` is `"external"`, `input_ports` returns `[ImageStream]`, so the scheduler injects the images passed by the caller. When `sourceType` is `"images"` or `"video"`, `input_ports` returns `[]`, so the scheduler skips it and the node self-seeds from its cached decoded files.

**Deployment workflow**:

1. Designer builds pipeline in UI, uploads test images, verifies results.
2. Designer switches InputNode to **External** mode and exports `pipeline.json`.
3. In production code:

```python
pipeline = Interpreter.load("pipeline.json")

# InputNode is now in external mode — it will pass images through to DetectionNode
result = pipeline.execute_frame(images=[bgr_frame])
```

No other pipeline changes needed. The same `pipeline.json` works in both modes.

---

## 6. Schema and Serialization

`schema/pipeline.schema.json` lists valid node `type` strings. When you add a new node type, add it to the `"type"` enum in the schema so that exported pipelines validate correctly:

```json
"type": {
  "type": "string",
  "enum": ["filter", "logic", "relation", "merge", "detection", "image_analysis", "input", "template_loader", "template_match"]
}
```

The schema does **not** encode port types — type safety is enforced in application code only.

### camelCase Keys

The JSON schema uses **camelCase keys throughout** (e.g., `sourcePort`, `targetPort`, `className`, `minCount`, `modelName`, `sourceType`). Python attributes in backend code remain snake_case as usual — camelCase is for JSON serialization only.

Every node config class must include a `ConfigDict` so that Pydantic accepts both forms:

```python
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

class YourNodeConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    # Fields use snake_case in Python; camelCase in JSON via the alias generator.
```

- `alias_generator=to_camel` — JSON produced by the frontend (and validated against the schema) uses camelCase keys.
- `populate_by_name=True` — Python code and tests can still pass snake_case field names directly.

### `functionId` field

Each node in the pipeline may carry an optional `functionId` string at the top level of its `NodeConfig`. This field is used for function/step binding in external systems and is passed through unchanged by the execution engine.

---

## 7. Testing Requirements

Minimum 80% line coverage. Write tests in `backend/tests/test_your_node.py`.

### Required test cases

1. **Happy path** — node processes valid input and returns expected output.
2. **Empty input** — `execute({})` or `execute({"input": []})` returns `{"output": []}` without crashing.
3. **Config parsing** — config defaults are applied correctly; invalid values raise early.
4. **Immutability** — output Objects are not the same objects as input Objects when transforms are applied.

### Self-seeding node tests

For reference image loader nodes, mock the filesystem call (`cv2.imread`) and verify:
- Cache is populated on first call.
- Second call does NOT re-read the file (cached).
- Missing file raises `RuntimeError` with a useful message.

### Example test skeleton

```python
import pytest
from rule_execution_engine.nodes.your_node import YourNode
from rule_execution_engine.schema.models import NodeConfig
from rule_execution_engine.spatial.geometry import Object

def _make_node(config: dict | None = None) -> YourNode:
    nc = NodeConfig(id="test", type="your_type", position={"x": 0, "y": 0}, config=config or {})
    return YourNode(nc)

def test_empty_input_returns_empty():
    node = _make_node()
    result = node.execute({"input": []})
    assert result == {"output": []}

def test_filters_correctly():
    node = _make_node({"threshold": 0.5})
    obj = Object(x=0, y=0, w=10, h=10, confidence=0.8, class_name="cat")
    result = node.execute({"input": [obj]})
    assert len(result["output"]) == 1
```

---

## 8. Checklist

Before opening a PR for a new node:

**Backend**
- [ ] `@NodeRegistry.register("type_string")` decorator present
- [ ] `input_ports` and `output_ports` declared correctly
- [ ] `execute()` handles empty inputs gracefully
- [ ] Config parsed to typed dataclass in `__init__`
- [ ] `Object` objects never mutated — transforms return new instances
- [ ] `List[T]` / `Dict[K, V]` used (Python 3.9 compat)
- [ ] Import added to `rule_execution_engine/nodes/__init__.py`
- [ ] Tests written and coverage ≥ 80%

**Frontend**
- [ ] `definition.ts` created with correct `type` string
- [ ] `registerNodeType()` called in `index.tsx` on module load
- [ ] Port handles use `PORT_TYPE_COLORS[PortType.X]` — no raw hex strings
- [ ] Import added to `src/nodes/index.ts`
- [ ] TypeScript: `npm run type-check` passes

**Schema**
- [ ] New `type` string added to `"type"` enum in `schema/pipeline.schema.json`
