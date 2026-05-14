# Pipeline Schema Design

`pipeline.schema.json` — JSON Schema Draft-07 shared contract between the frontend canvas editor and backend execution engine.

---

## Top-Level Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | Schema version in `MAJOR.MINOR` format (e.g. `"1.0"`). Used to detect breaking changes during import/export. |
| `metadata` | object | Yes | Pipeline-level identity and class vocabulary. |
| `nodes` | array | Yes | Ordered list of processing nodes forming the DAG. At least one node required. |
| `edges` | array | Yes | Directed connections between node ports. Empty array is valid (single isolated node). |

---

## `metadata`

Global context shared by all nodes in the pipeline.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tool_id` | string | Yes | Unique identifier for the pipeline (e.g. `"safety-zone-check"`). Used by the backend to reference the pipeline in multi-pipeline deployments. |
| `class_list` | string[] | Yes | Master vocabulary of detection class names (e.g. `["person","car","helmet"]`). Minimum 1 entry. Provides the global fallback when a node has no class-specific override. The frontend uses this list to populate dropdowns in LogicNode and RelationNode. |
| `description` | string | No | Human-readable summary of what the pipeline does. |
| `created_at` | string (date-time) | No | ISO-8601 timestamp of pipeline creation. |
| `updated_at` | string (date-time) | No | ISO-8601 timestamp of last modification. |

---

## `nodes[]` — NodeConfig

Each element represents one processing unit in the DAG.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique node identifier within the pipeline. Referenced by `edges[].source` and `edges[].target`. |
| `type` | string | Yes | Node type discriminator: `"filter"`, `"logic"`, `"relation"`, or `"merge"`. Determines which `config` variant applies. |
| `position` | Position | Yes | Canvas (x, y) coordinates for the frontend editor. Has no effect on backend execution. |
| `config` | object | Yes | Type-specific configuration. Validated against the `oneOf` variant matching `type`. |

### `Position`

| Field | Type | Description |
|-------|------|-------------|
| `x` | number | Horizontal canvas position in pixels. |
| `y` | number | Vertical canvas position in pixels. |

---

## Node Config Variants

### `FilterConfig` — type `"filter"`

Keeps only bounding boxes that satisfy the declared threshold conditions.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `conditions` | FilterCondition[] | Yes | — | One or more threshold rules. Minimum 1. |
| `logic` | `"AND"` \| `"OR"` | No | `"AND"` | How conditions are combined: `AND` requires a box to pass **all** conditions for its class; `OR` requires at least one. Conditions for a class the box does not belong to are ignored. |

#### `FilterCondition`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `class_name` | string | Yes | Target class (e.g. `"person"`). Use `""` (empty string) to apply the condition to **all** classes. |
| `field` | string | Yes | Numeric property to test: `"confidence"` (0–1), `"width"` (pixels), `"height"` (pixels), `"area"` (pixels²). |
| `operator` | string | Yes | Comparison operator: `"gt"` (>), `"gte"` (≥), `"lt"` (<), `"lte"` (≤), `"eq"` (=). |
| `threshold` | number | Yes | Value to compare against. Must be ≥ 0. |

---

### `LogicConfig` — type `"logic"`

Emits a `LogicSignal` (trigger) when the count-based conditions over incoming boxes are satisfied. Used as a downstream event gate.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `operation` | `"AND"` \| `"OR"` | Yes | — | `AND`: all conditions must be met; `OR`: at least one. |
| `conditions` | LogicCondition[] | Yes | — | Class-count conditions. Minimum 1. |
| `trigger_label` | string | No | — | Label attached to the trigger event when the node fires. Useful for downstream consumers to identify which rule triggered. |

#### `LogicCondition`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `class_name` | string | Yes | — | Detection class to count (e.g. `"helmet"`). |
| `min_count` | integer | No | `1` | Minimum number of boxes of `class_name` required. Must be ≥ 1. |
| `negate` | boolean | No | `false` | When `true`, the condition is satisfied when the count is **less than** `min_count` — i.e. the class is effectively absent. |

---

### `RelationConfig` — type `"relation"`

Computes spatial relationships between pairs of bounding boxes and produces new synthetic boxes representing matched pairs.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `mode` | `"self_join"` \| `"cross_join"` | Yes | — | `self_join`: pairs boxes from a single input stream against themselves; `cross_join`: pairs boxes from two separate input streams (A and B). |
| `relation_type` | string | No | `"iou"` | Spatial metric used to qualify a pair: `"iou"` (Intersection-over-Union), `"distance"` (edge distance), `"contains"` (A contains B), `"centroid_distance"` (centroid-to-centroid distance). |
| `threshold` | number | No | — | Numeric cut-off for the chosen metric. Pairs scoring below this value (for IoU/contains) or above (for distances) are discarded. Must be ≥ 0. |
| `filter_class_a` | string | No | `""` | Restrict side-A boxes to this class. Empty or omitted means all classes. |
| `filter_class_b` | string | No | `""` | Restrict side-B boxes to this class (cross_join only). Empty or omitted means all classes. |
| `output_class_name` | string | No | `""` | Class name stamped on each output relation box. If empty, the backend auto-generates an `"A+B"` label derived from the two source classes. |
| `offset` | ObjectOffset | No | zeroes | Pixel offset applied to the union bounding box of each qualifying pair. |
| `scale` | ObjectScale | No | ones | Scale factors applied to the union bounding box after the offset. |

#### `ObjectOffset`

Adds a fixed pixel delta to the generated relation box.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `dx` | number | `0` | Horizontal translation of the box origin (positive = right). |
| `dy` | number | `0` | Vertical translation of the box origin (positive = down). |
| `dw` | number | `0` | Width adjustment (positive = wider). |
| `dh` | number | `0` | Height adjustment (positive = taller). |

#### `ObjectScale`

Multiplies the generated relation box dimensions after offset is applied.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `sx` | number ≥ 0 | `1.0` | Horizontal position scale. |
| `sy` | number ≥ 0 | `1.0` | Vertical position scale. |
| `sw` | number ≥ 0 | `1.0` | Width scale. |
| `sh` | number ≥ 0 | `1.0` | Height scale. |

---

### `MergeConfig` — type `"merge"`

Collects multiple `ObjectStream` inputs into a single `Collection`, deduplicating or truncating by confidence score.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `top_k` | integer | No | `1000` | Maximum number of boxes retained after merge, sorted by confidence descending. Must be ≥ 1. Lower values act as a hard cap to limit downstream load. |

---

## `edges[]` — EdgeConfig

Directed connection from one node's output port to another's input port.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique edge identifier within the pipeline. |
| `source` | string | Yes | `id` of the originating node. |
| `source_port` | string | Yes | Output port name on the source node (e.g. `"output"`, `"triggered"`, `"objects"`). |
| `target` | string | Yes | `id` of the receiving node. |
| `target_port` | string | Yes | Input port name on the target node (e.g. `"input"`, `"input_a"`, `"input_b"`). |

Port names must match the declared ports of the corresponding node type. The frontend validates compatibility via `PORT_TYPE_COMPATIBILITY`; the backend enforces the same rules during `Scheduler` initialization.

---

## Design Decisions

### `version` as semver-lite
Using `MAJOR.MINOR` (not full semver) keeps the format simple while still allowing breaking-change detection. Patch-level changes never affect serialization compatibility.

### `metadata.class_list` as global vocabulary
Centralizing class names in metadata avoids scattered string literals across nodes and enables the frontend's class-inference BFS to fall back to a known vocabulary when upstream FilterNodes provide no narrowing.

### `position` in NodeConfig
Canvas coordinates are intentionally part of the serialized format so that exported pipelines can be re-imported with the same visual layout. They are stripped before backend execution.

### `config` as `oneOf`
Using `oneOf` rather than a free `object` ensures that extra unknown fields are rejected (`additionalProperties: false` on each variant) and that the backend Pydantic union discriminator can rely on structural uniqueness between variants.

### Separation of `FilterConfig.logic` from `LogicConfig.operation`
`FilterConfig.logic` governs per-box attribute filtering (pass/fail individual boxes). `LogicConfig.operation` governs scene-level event logic (count thresholds across the whole frame). They serve different abstraction levels and are intentionally kept separate.
