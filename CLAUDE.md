# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
cd backend
pip install -e ".[dev]"          # install with dev deps
pytest tests/ -v                  # run all tests
pytest tests/test_filter_node.py  # run a single test file
pytest tests/ -v --cov=bbox_proc  # run with coverage
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
bbox-proc-rules/
├── frontend/   # React 18 + Vite + ReactFlow canvas editor
├── backend/    # Python 3.9+ execution engine (pure library)
└── schema/     # pipeline.schema.json — shared contract
```

### Backend (`bbox_proc/`)

**Execution path**: `Interpreter.load(path)` → `Pipeline` → `Pipeline.execute_frame(bboxes)` → `Scheduler.run()` → `ExecutionResult`

- **`schema/models.py`** — Pydantic models: `PipelineConfig`, `NodeConfig`, `EdgeConfig`, typed config unions (`FilterConfig`, `LogicConfig`, etc.)
- **`schema/validator.py`** — DAG structural validation (run after Pydantic)
- **`nodes/base.py`** — `BaseNode` ABC with `input_ports`, `output_ports`, `execute(inputs)` interface; `PortType` enum (`BoxStream`, `Collection`, `LogicSignal`)
- **`nodes/registry.py`** — `NodeRegistry`: `@NodeRegistry.register("type")` decorator + `NodeRegistry.create(config)`. All node modules auto-import via `bbox_proc/nodes/__init__.py`
- **`engine/scheduler.py`** — Kahn's topological sort; source nodes (in-degree 0) receive raw frame bboxes on their `input` port; propagates outputs through edges
- **`engine/interpreter.py`** — `Interpreter` (static factory), `Pipeline` (runnable), `ExecutionResult` (output container with `signals()`, `get_node_output()`, `all_outputs()`)
- **`spatial/`** — `BBox` (frozen dataclass), IoU, centroid distance, transform helpers

**BBox is immutable** — all spatial transforms return new instances. Use `Python 3.9`-compatible type hints (`List[T]`, not `list[T]`).

### Frontend (`src/`)

**State**: single Zustand store at `store/pipelineStore.ts` — holds `nodes`, `edges`, `metadata`. All mutations return new state (immutable pattern).

**Node registration**: each node directory has a `definition.ts` (ports, defaultConfig, component) and an `index.tsx` that calls `registerNodeType()` on module load. `src/nodes/index.ts` imports all of them so the registry is populated before the canvas renders.

**Port validation**: `validation/portValidator.ts` — `isValidConnection()` enforces type compatibility via `PORT_TYPE_COMPATIBILITY` map. One input port can only receive one connection.

**Class inference**: `inference/classInferencer.ts` — BFS upstream through the DAG; FilterNodes contribute their `class_name`, source nodes fall back to the global `class_list`. Used to populate dropdowns in LogicNode and RelationNode.

**Export/Import**: `export/pipelineExporter.ts` — serializes/deserializes between React Flow state and `PipelineJSON`. React Flow's `sourceHandle`/`targetHandle` maps to schema's `source_port`/`target_port`.

### Adding a New Node Type

**Backend** — create a file in `bbox_proc/nodes/`, implement `BaseNode`, decorate with `@NodeRegistry.register("type_string")`, then add the import to `bbox_proc/nodes/__init__.py`. No other files need changes.

**Frontend** — create `src/nodes/YourNode/definition.ts` (call `registerNodeType()`), `src/nodes/YourNode/index.tsx` (React component), then add the import to `src/nodes/index.ts`. No other files need changes.

### Detection Node (image → bbox)

`DetectionNode` is the entry point for image-based pipelines. It is a source node with an `ImageStream` input and `BoxStream` output, which connects to any existing node (FilterNode, MergeNode, etc.).

**Model catalog** — `backend/models.yaml` lists all available weights per architecture. `ModelCatalog` auto-discovers this file from the backend directory on first use. Call `ModelCatalog.load(path)` to load from a custom path.

**Adding a new model** — append an entry to `models.yaml` and mirror it in `MODELS_BY_ARCHITECTURE` in `src/nodes/DetectionNode/index.tsx`. No code changes otherwise.

**Adding a new architecture** — implement `BaseDetector` in `bbox_proc/detectors/`, decorate with `@DetectorRegistry.register("arch_name")`, import in `bbox_proc/detectors/__init__.py`, and add to `ARCHITECTURES` + `MODELS_BY_ARCHITECTURE` in the frontend component.

**Image pipelines** — call `pipeline.execute_frame(images=[...])` instead of `execute_frame(input_bboxes=[...])`. Pipelines with both node types are supported; source nodes are seeded based on their declared input port type (`ImageStream` vs everything else).

**Lazy loading** — the model is loaded on the first `execute_frame` call and reused. The `DetectionNode` instance persists on `Pipeline._nodes` across frames.

**NMS threshold** — accepted by all detectors for API consistency but has no effect on transformer-based models (RF-DETR). The frontend greys out the field when RF-DETR is selected.

### Image Analysis Node (AnnotatedStream → AnnotatedStream + BoxStream)

`ImageAnalysisNode` filters frames by measuring pixel statistics inside each BBox ROI. It operates on `AnnotatedStream` — a new port type that carries `List[AnnotatedFrame]` where each `AnnotatedFrame` holds an `image: np.ndarray` and `bboxes: List[BBox]`.

**Data model** — `bbox_proc/spatial/annotated.py`: `AnnotatedFrame(image, bboxes)` with `with_bboxes(bboxes)` helper (shares image reference, no copy).

**Measurement fields** (`bbox_proc/nodes/image_analysis_node.py:measure_roi`):
- `intensity` — ITU-R BT.601 luminance, 0–255
- `red` / `green` / `blue` — channel means, 0–255 (BGR order: ch0=B, ch1=G, ch2=R)
- `hue` — 0–360°, `saturation` / `value` — 0–100 (pure-NumPy HSV, no OpenCV)

**Filter semantics** — same as FilterNode: conditions with `class_name=""` apply to all classes; BBoxes whose class matches no condition pass through unchanged. AND/OR logic applies across applicable conditions.

**Outputs**: `output` (AnnotatedStream, frames with ≥1 survivor) + `bboxes` (BoxStream, flat list, for connecting to FilterNode/LogicNode).

**AnnotatedStream port** — orange handles (#f97316) in the canvas. `DetectionNode` now has two outputs: `output` (blue, BoxStream) and `annotated` (orange, AnnotatedStream). The AnnotatedStream path is: DetectionNode.annotated → ImageAnalysisNode → [chain or] LogicNode via .bboxes.

### Port Type Compatibility

| Source → Target | BoxStream | Collection | LogicSignal |
|---|---|---|---|
| BoxStream | ✓ | ✓ | — |
| Collection | — | ✓ | — |
| LogicSignal | — | — | ✓ |

Source nodes (FilterNode, RelationNode): `BoxStream → BoxStream`  
MergeNode: `N × BoxStream → Collection`  
LogicNode: `BoxStream or Collection → LogicSignal`
