import { Handle, Position } from 'reactflow'
import type { NodeComponentProps } from '../types'
import { usePipelineStore } from '@/store/pipelineStore'
import { NodeHelp } from '../NodeHelp'
import { parseNumericInput } from '@/utils/numericInput'

// ------------------------------------------------------------------ //
// Model catalog — mirror of backend/models.yaml
// Update both files when adding new model weights.
// ------------------------------------------------------------------ //

const ARCHITECTURES = ['yolov12', 'rf_detr'] as const
type Architecture = typeof ARCHITECTURES[number]

interface ModelEntry {
  name: string
  description: string
}

const MODELS_BY_ARCHITECTURE: Record<Architecture, ModelEntry[]> = {
  yolov12: [
    { name: 'person_detection', description: 'Person detection' },
    { name: 'forklift_detection', description: 'Forklift detection' },
  ],
  rf_detr: [
    { name: 'person_detection', description: 'RF-DETR person detection' },
    { name: 'forklift_detection', description: 'RF-DETR forklift detection' },
  ],
}

// ------------------------------------------------------------------ //

const HELP_LINES = [
  'Runs an object detection model on input image frames.',
  'Select an architecture, then choose a model weight.',
  'Left port (purple): ImageStream input.',
  'Right port (blue): ObjectStream output — connects to Filter, Merge, Logic, etc.',
  'NMS threshold is not used by transformer-based models (RF-DETR).',
  'Multiple Detection nodes can coexist in the same pipeline.',
]

interface DetectionConfig {
  architecture: Architecture
  modelName: string
  confidenceThreshold: number
  nmsThreshold: number
  device: 'cpu' | 'cuda'
}

export function DetectionNodeComponent({ id, data, selected }: NodeComponentProps) {
  const updateNodeConfig = usePipelineStore((s) => s.updateNodeConfig)
  const config = data.config as unknown as DetectionConfig

  const architecture: Architecture = ARCHITECTURES.includes(config.architecture as Architecture)
    ? (config.architecture as Architecture)
    : 'yolov12'

  const availableModels = MODELS_BY_ARCHITECTURE[architecture]
  const isValidModel = availableModels.some((m) => m.name === config.modelName)
  const isInvalid = !isValidModel

  const setConfig = (patch: Partial<DetectionConfig>) =>
    updateNodeConfig(id, { ...config, ...patch } as Record<string, unknown>)

  const handleArchChange = (arch: Architecture) => {
    const models = MODELS_BY_ARCHITECTURE[arch]
    const stillValid = models.some((m) => m.name === config.modelName)
    setConfig({ architecture: arch, modelName: stillValid ? config.modelName : '' })
  }

  const handleThreshold = (field: 'confidenceThreshold' | 'nmsThreshold', raw: string) => {
    const v = parseNumericInput(raw, 0.01, 0)
    if (v !== null) setConfig({ [field]: Math.min(1, Math.max(0, v)) })
  }

  const isRfDetr = architecture === 'rf_detr'

  return (
    <div
      style={{
        background: '#f0fdf4',
        border: selected
          ? '2px solid #16a34a'
          : isInvalid
          ? '2px solid #f87171'
          : '2px solid #86efac',
        borderRadius: 8,
        padding: '12px 16px',
        minWidth: 260,
        fontSize: 13,
        boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
      }}
    >
      {/* ImageStream input handle — purple to distinguish from ObjectStream */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        style={{ background: '#7c3aed', width: 12, height: 12 }}
      />

      {/* Header */}
      <div
        style={{
          fontWeight: 700,
          marginBottom: 8,
          color: '#15803d',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        Detection
        {isInvalid && (
          <span style={{ color: '#dc2626', fontSize: 11, fontWeight: 400 }}>
            ⚠ select model
          </span>
        )}
      </div>

      {/* Architecture */}
      <label style={{ display: 'block', marginBottom: 6 }}>
        Architecture
        <select
          value={architecture}
          onChange={(e) => handleArchChange(e.target.value as Architecture)}
          style={{ display: 'block', width: '100%', marginTop: 2 }}
        >
          {ARCHITECTURES.map((arch) => (
            <option key={arch} value={arch}>
              {arch}
            </option>
          ))}
        </select>
      </label>

      {/* Model weight */}
      <label style={{ display: 'block', marginBottom: 6 }}>
        Model
        <select
          value={config.modelName}
          onChange={(e) => setConfig({ modelName: e.target.value })}
          style={{
            display: 'block',
            width: '100%',
            marginTop: 2,
            borderColor: isInvalid ? '#f87171' : undefined,
          }}
        >
          <option value="">-- select model --</option>
          {availableModels.map((m) => (
            <option key={m.name} value={m.name}>
              {m.description}
            </option>
          ))}
        </select>
      </label>

      {/* Confidence + NMS row */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
        <label style={{ flex: 1 }}>
          Conf thr
          <input
            type="number"
            step="0.05"
            min={0}
            max={1}
            value={config.confidenceThreshold}
            onChange={(e) => handleThreshold('confidenceThreshold', e.target.value)}
            style={{ display: 'block', width: '100%', marginTop: 2 }}
          />
        </label>
        <label
          style={{ flex: 1, opacity: isRfDetr ? 0.45 : 1 }}
          title={isRfDetr ? 'Not used by transformer-based models' : undefined}
        >
          NMS thr
          <input
            type="number"
            step="0.05"
            min={0}
            max={1}
            value={config.nmsThreshold}
            disabled={isRfDetr}
            onChange={(e) => handleThreshold('nmsThreshold', e.target.value)}
            style={{ display: 'block', width: '100%', marginTop: 2 }}
          />
        </label>
      </div>

      {/* Device */}
      <label style={{ display: 'block', marginBottom: 4 }}>
        Device
        <select
          value={config.device}
          onChange={(e) => setConfig({ device: e.target.value as 'cpu' | 'cuda' })}
          style={{ display: 'block', width: '100%', marginTop: 2 }}
        >
          <option value="cpu">CPU</option>
          <option value="cuda">CUDA (GPU)</option>
        </select>
      </label>

      <NodeHelp lines={HELP_LINES} accentColor="#16a34a" />

      {/* Output handles */}
      <div style={{ marginTop: 6, fontSize: 11, color: '#6b7280', textAlign: 'right' }}>
        <div style={{ marginBottom: 14 }}>Objects ●</div>
        <div>Annotated ●</div>
      </div>

      {/* ObjectStream output */}
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        style={{ background: '#3b82f6', width: 12, height: 12, top: '65%' }}
      />
      {/* AnnotatedStream output — orange */}
      <Handle
        type="source"
        position={Position.Right}
        id="annotated"
        style={{ background: '#f97316', width: 12, height: 12, top: '82%' }}
      />
    </div>
  )
}
