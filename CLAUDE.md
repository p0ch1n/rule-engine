# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Test Status

| Layer | Tests | Coverage | Build |
|-------|-------|----------|-------|
| Backend | 124/124 pass | 89% | — |
| Frontend | — | — | ✓ (103 kB gz) |

TypeScript: clean. ESLint: zero warnings. Model-loading paths (rf_detr, yolov12) are excluded from meaningful coverage as they require real GPU weights.

## Commands

### Backend

```bash
cd backend
pip install -e ".[dev]"          # install with dev deps
pytest tests/ -v                  # run all tests
pytest tests/test_filter_node.py  # run a single test file
pytest tests/ -v --cov=rule_execution_engine  # run with coverage
python examples/run_pipeline.py   # run bundled example
python examples/run_pipeline.py my_pipeline.json  # run exported pipeline
```

### Frontend

```bash
cd frontend
npm install
npm run dev         # http://localhost:5173
npm run build       # tsc + vite production bundle
npm run type-check  # tsc --noEmit
npm run lint        # eslint (zero warnings policy)
```

## Architecture

Two independent layers communicate only through the shared JSON schema at `schema/pipeline.schema.json` (JSON Schema Draft-07).

```
rule-engine/
├── frontend/   # React 18 + Vite + ReactFlow canvas editor
├── backend/    # Python 3.9+ execution engine (pure library)
└── schema/     # pipeline.schema.json — shared contract
```

### Backend (`rule_execution_engine/`)

**Execution path (object pipeline)**: `Interpreter.load(path)` → `Pipeline` → `Pipeline.execute_frame(input_objects=[...])` → `Scheduler.run()` → `ExecutionResult`

**Execution path (image pipeline)**: `Pipeline.execute_frame(images=[...])` — scheduler seeds `ImageStream` input ports; `InputNode` (external mode) passes images through; `DetectionNode` converts images to objects.

- **`schema/models.py`** — Pydantic models: `PipelineConfig`, `NodeConfig`, `EdgeConfig`. All use `ConfigDict(alias_generator=to_camel, populate_by_name=True)` so JSON uses camelCase while Python code uses snake_case. Node-specific config classes (`FilterConfig`, `LogicConfig`, etc.) live in their respective node files.
- **`schema/validator.py`** — DAG structural validation (run after Pydantic)
- **`nodes/base.py`** — `BaseNode` ABC with `input_ports`, `output_ports`, `execute(inputs)` interface; `PortType` enum (`ObjectStream`, `Collection`, `LogicSignal`)
- **`nodes/registry.py`** — `NodeRegistry`: `@NodeRegistry.register("type")` decorator + `NodeRegistry.create(config)`. All node modules auto-import via `rule_execution_engine/nodes/__init__.py`
- **`engine/scheduler.py`** — Kahn's topological sort; source nodes (in-degree 0) receive raw frame objects on their `input` port; propagates outputs through edges
- **`engine/interpreter.py`** — `Interpreter` (static factory), `Pipeline` (runnable), `ExecutionResult` (output container with `signals()`, `get_node_output()`, `all_outputs()`)
- **`spatial/`** — `Object` (frozen dataclass), IoU, centroid distance, transform helpers

**Object is immutable** — all spatial transforms return new instances. Use `Python 3.9`-compatible type hints (`List[T]`, not `list[T]`).

### Frontend (`src/`)

**State**: single Zustand store at `store/pipelineStore.ts` — holds `nodes`, `edges`, `metadata`. All mutations return new state (immutable pattern).

**Node registration**: each node directory has a `definition.ts` (ports, defaultConfig, component) and an `index.tsx` that calls `registerNodeType()` on module load. `src/nodes/index.ts` imports all of them so the registry is populated before the canvas renders.

**Port validation**: `validation/portValidator.ts` — `isValidConnection()` enforces type compatibility via `PORT_TYPE_COMPATIBILITY` map. One input port can only receive one connection.

**Class inference**: `inference/classInferencer.ts` — BFS upstream through the DAG; FilterNodes contribute `className` from each entry in `conditions[]`, source nodes fall back to the global `classList`. Used to populate dropdowns in LogicNode and RelationNode.

**Export/Import**: `export/pipelineExporter.ts` — serializes/deserializes between React Flow state and `PipelineJSON`. React Flow's `sourceHandle`/`targetHandle` maps to schema's `sourcePort`/`targetPort`.

### Adding a New Node Type

**Backend** — create a file in `rule_execution_engine/nodes/`. Define the config class (Pydantic `BaseModel`) and the node class in the same file. Pass `config_class=` to the decorator. Add one import line to `rule_execution_engine/nodes/__init__.py`. No other files need changes.

```python
# my_node.py — config class and node class live together
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class MyNodeConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    threshold: float = 0.5          # JSON key: "threshold" (no change needed)
    min_count: int = 1              # JSON key: "minCount" (auto-aliased)

@NodeRegistry.register("my_node", config_class=MyNodeConfig)
class MyNode(BaseNode):
    ...
```

**Frontend** — create `src/nodes/YourNode/definition.ts` (call `registerNodeType()`), `src/nodes/YourNode/index.tsx` (React component), then add the import to `src/nodes/index.ts`. No other files need changes.

### Input Node (image source)

`InputNode` is the image entry point for UI prototyping and production deployment. It has three modes controlled by `sourceType` in the JSON config (Python attribute: `cfg.source_type`):

| Mode | `input_ports` | Behavior |
|---|---|---|
| `images` | `[]` (self-seeding) | Decodes base64 PNG/JPEG files from config; caches BGR arrays |
| `video` | `[]` (self-seeding) | Decodes a base64 video file via OpenCV; caches frames |
| `external` | `[ImageStream]` (injectable) | Pure pass-through; scheduler injects images from `execute_frame(images=[...])` |

**Embedded mode** (images/video) — `input_ports = []` so the scheduler treats it as self-seeding. Files are stored as base64 data URIs in the pipeline config. Frames are decoded once and cached.

**External mode** — `input_ports = [ImageStream]` so the scheduler injects images on every `execute_frame` call. No files are stored; no caching. Used when deploying a config exported from the UI to another environment where images come from a camera or upstream service.

```python
# Embedded mode: run the pipeline as designed in the UI
pipeline = Interpreter.load("pipeline.json")
result = pipeline.execute_frame()          # InputNode self-seeds from config files

# External mode: inject images at runtime
result = pipeline.execute_frame(images=[bgr_frame])  # InputNode passes images through
```

**UI behavior** — the three-button toggle (Images / Video / External) in the frontend sets `sourceType`. Switching to External shows an info panel and removes the upload zone. The node shows a red border when in Images/Video mode with no files uploaded.

### Detection Node (image → obj)

`DetectionNode` is the entry point for image-based pipelines. It is a source node with an `ImageStream` input and `ObjectStream` output, which connects to any existing node (FilterNode, MergeNode, etc.).

**Model catalog** — `backend/models.yaml` lists all available weights per architecture. `ModelCatalog` auto-discovers this file from the backend directory on first use. Call `ModelCatalog.load(path)` to load from a custom path.

**Adding a new model** — append an entry to `models.yaml` and mirror it in `MODELS_BY_ARCHITECTURE` in `src/nodes/DetectionNode/index.tsx`. No code changes otherwise.

**Adding a new architecture** — implement `BaseDetector` in `rule_execution_engine/detectors/`, decorate with `@DetectorRegistry.register("arch_name")`, import in `rule_execution_engine/detectors/__init__.py`, and add to `ARCHITECTURES` + `MODELS_BY_ARCHITECTURE` in the frontend component.

**Image pipelines** — call `pipeline.execute_frame(images=[...])` instead of `execute_frame(input_objects=[...])`. Pipelines with both node types are supported; source nodes are seeded based on their declared input port type (`ImageStream` vs everything else).

**Lazy loading** — the model is loaded on the first `execute_frame` call and reused. The `DetectionNode` instance persists on `Pipeline._nodes` across frames.

**NMS threshold** — accepted by all detectors for API consistency but has no effect on transformer-based models (RF-DETR). The frontend greys out the field when RF-DETR is selected.

### Image Analysis Node (AnnotatedStream → AnnotatedStream + ObjectStream)

`ImageAnalysisNode` filters frames by measuring pixel statistics inside each Object ROI. It operates on `AnnotatedStream` — a new port type that carries `List[AnnotatedFrame]` where each `AnnotatedFrame` holds an `image: np.ndarray` and `objects: List[Object]`.

**Data model** — `rule_execution_engine/spatial/annotated.py`: `AnnotatedFrame(image, objects)` with `with_objects(objects)` helper (shares image reference, no copy).

**Measurement fields** (`rule_execution_engine/nodes/image_analysis_node.py:measure_roi`):
- `intensity` — ITU-R BT.601 luminance, 0–255
- `red` / `green` / `blue` — channel means, 0–255 (BGR order: ch0=B, ch1=G, ch2=R)
- `hue` — 0–360°, `saturation` / `value` — 0–100 (pure-NumPy HSV, no OpenCV)

**Filter semantics** — same as FilterNode: conditions with `class_name=""` apply to all classes; Objects whose class matches no condition pass through unchanged. AND/OR logic applies across applicable conditions.

**Outputs**: `output` (AnnotatedStream, frames with ≥1 survivor) + `objects` (ObjectStream, flat list, for connecting to FilterNode/LogicNode).

**AnnotatedStream port** — orange handles (#f97316) in the canvas. `DetectionNode` now has two outputs: `output` (blue, ObjectStream) and `annotated` (orange, AnnotatedStream). The AnnotatedStream path is: DetectionNode.annotated → ImageAnalysisNode → [chain or] LogicNode via .objects.

### Port Type Compatibility

| Source → Target | ObjectStream | Collection | LogicSignal | ImageStream | AnnotatedStream | ReferenceImageStream |
|---|---|---|---|---|---|---|
| ObjectStream | ✓ | ✓ | — | — | — | — |
| Collection | — | ✓ | — | — | — | — |
| LogicSignal | — | — | ✓ | — | — | — |
| ImageStream | — | — | — | ✓ | — | — |
| AnnotatedStream | — | — | — | — | ✓ | — |
| ReferenceImageStream | — | — | — | — | — | ✓ |

Source nodes (FilterNode, RelationNode): `ObjectStream → ObjectStream`  
MergeNode: `N × ObjectStream → Collection`  
LogicNode: `ObjectStream or Collection → LogicSignal`

**`ReferenceImageStream`** — static config-time images (template matching references, background models). Nodes that output this type declare **no input ports** (self-seeding); the scheduler does NOT inject pipeline data into them. See `docs/developer-guide.md §5.2`.

**Port colors** — defined in `frontend/src/nodes/types.ts:PORT_TYPE_COLORS`. Always import from there; do not hardcode hex strings in node components.

## Developer Guide

See **`docs/developer-guide.md`** for:
- Full port type reference with colors and compatibility rules
- Step-by-step instructions for adding backend + frontend nodes
- Self-seeding source node pattern (ReferenceImageStream)
- Template matching end-to-end example
- Testing requirements and checklist
