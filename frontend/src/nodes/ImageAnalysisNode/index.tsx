import { Handle, Position } from 'reactflow'
import type { NodeComponentProps } from '../types'
import { usePipelineStore } from '@/store/pipelineStore'
import { NodeHelp } from '../NodeHelp'
import { parseNumericInput } from '@/utils/numericInput'

// ------------------------------------------------------------------ //
// Constants
// ------------------------------------------------------------------ //

const FIELD_OPTIONS = [
  { value: 'intensity',   label: 'Intensity',   range: '0 – 255',  hint: 'ITU-R luminance (BT.601)' },
  { value: 'red',         label: 'Red',         range: '0 – 255',  hint: 'R channel mean (BGR ch2)' },
  { value: 'green',       label: 'Green',       range: '0 – 255',  hint: 'G channel mean (BGR ch1)' },
  { value: 'blue',        label: 'Blue',        range: '0 – 255',  hint: 'B channel mean (BGR ch0)' },
  { value: 'hue',         label: 'Hue',         range: '0 – 360°', hint: 'HSV H channel mean' },
  { value: 'saturation',  label: 'Saturation',  range: '0 – 100',  hint: 'HSV S channel mean' },
  { value: 'value',       label: 'Value',       range: '0 – 100',  hint: 'HSV V channel mean' },
] as const

type Field = typeof FIELD_OPTIONS[number]['value']

const OPERATOR_OPTIONS = [
  { value: 'gt',  label: '>'  },
  { value: 'gte', label: '>=' },
  { value: 'lt',  label: '<'  },
  { value: 'lte', label: '<=' },
  { value: 'eq',  label: '='  },
]

const HELP_LINES = [
  'Filters annotated frames by measuring pixels inside each Object ROI.',
  'Images are assumed BGR channel order (OpenCV convention).',
  'className empty → condition applies to all classes.',
  'Objects whose class matches no condition pass through unchanged.',
  'AND: Object must pass ALL applicable conditions.',
  'OR:  Object must pass ANY one applicable condition.',
  'Frames with zero surviving Objects are dropped from the output.',
  'Chain multiple Image Analysis nodes for compound pixel filters.',
  'Connect "Objects" output to Filter / Merge / Logic nodes.',
]

// ------------------------------------------------------------------ //
// Types
// ------------------------------------------------------------------ //

interface AnalysisCondition {
  className: string
  field: Field
  operator: string
  threshold: number
}

interface AnalysisConfig {
  conditions: AnalysisCondition[]
  logic: 'AND' | 'OR'
}

// ------------------------------------------------------------------ //
// Component
// ------------------------------------------------------------------ //

export function ImageAnalysisNodeComponent({ id, data, selected }: NodeComponentProps) {
  const updateNodeConfig = usePipelineStore((s) => s.updateNodeConfig)
  const config = data.config as unknown as AnalysisConfig
  const availableClasses = data.availableClasses ?? []

  const isInvalid = config.conditions.length === 0

  const setConfig = (patch: Partial<AnalysisConfig>) =>
    updateNodeConfig(id, { ...config, ...patch } as Record<string, unknown>)

  const updateCond = (i: number, patch: Partial<AnalysisCondition>) => {
    const next = config.conditions.map((c, idx) => (idx === i ? { ...c, ...patch } : c))
    setConfig({ conditions: next })
  }

  const handleThreshold = (i: number, raw: string) => {
    const v = parseNumericInput(raw, 0.1, 0)
    if (v !== null) updateCond(i, { threshold: v })
  }

  const addCondition = () =>
    setConfig({
      conditions: [
        ...config.conditions,
        { className: '', field: 'intensity', operator: 'gt', threshold: 100 },
      ],
    })

  const removeCond = (i: number) =>
    setConfig({ conditions: config.conditions.filter((_, idx) => idx !== i) })

  const fieldInfo = (field: string) =>
    FIELD_OPTIONS.find((f) => f.value === field)

  return (
    <div
      style={{
        background: '#fff7ed',
        border: selected
          ? '2px solid #ea580c'
          : isInvalid
          ? '2px solid #f87171'
          : '2px solid #fdba74',
        borderRadius: 8,
        padding: '12px 16px',
        minWidth: 280,
        fontSize: 13,
        boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
      }}
    >
      {/* AnnotatedStream input handle — orange */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        style={{ background: '#f97316', width: 12, height: 12 }}
      />

      {/* Header */}
      <div
        style={{
          fontWeight: 700,
          marginBottom: 6,
          color: '#c2410c',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        Image Analysis
        {isInvalid && (
          <span style={{ color: '#dc2626', fontSize: 11, fontWeight: 400 }}>
            ⚠ add condition
          </span>
        )}
      </div>

      {/* Logic selector (only when > 1 condition) */}
      {config.conditions.length > 1 && (
        <label style={{ display: 'block', marginBottom: 6 }}>
          Combine with
          <select
            value={config.logic}
            onChange={(e) => setConfig({ logic: e.target.value as 'AND' | 'OR' })}
            style={{ display: 'block', width: '100%', marginTop: 2 }}
          >
            <option value="AND">AND (all must pass)</option>
            <option value="OR">OR (any must pass)</option>
          </select>
        </label>
      )}

      {/* Conditions */}
      {config.conditions.map((cond, i) => {
        const info = fieldInfo(cond.field)
        return (
          <div
            key={i}
            style={{
              background: '#fef3c7',
              border: '1px solid #fcd34d',
              borderRadius: 6,
              padding: '8px 10px',
              marginBottom: 6,
              position: 'relative',
            }}
          >
            {config.conditions.length > 1 && (
              <button
                onClick={() => removeCond(i)}
                title="Remove condition"
                style={{
                  position: 'absolute',
                  top: 4,
                  right: 6,
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: 12,
                  color: '#9ca3af',
                }}
              >
                ✕
              </button>
            )}

            {/* Class name */}
            <label style={{ display: 'block', marginBottom: 4 }}>
              Class <span style={{ color: '#9ca3af', fontSize: 11 }}>(empty = all)</span>
              {availableClasses.length > 0 ? (
                <select
                  value={cond.className}
                  onChange={(e) => updateCond(i, { className: e.target.value })}
                  style={{ display: 'block', width: '100%', marginTop: 2 }}
                >
                  <option value="">-- all classes --</option>
                  {availableClasses.map((cls) => (
                    <option key={cls} value={cls}>{cls}</option>
                  ))}
                </select>
              ) : (
                <input
                  value={cond.className}
                  onChange={(e) => updateCond(i, { className: e.target.value })}
                  placeholder="all classes"
                  style={{ display: 'block', width: '100%', marginTop: 2 }}
                />
              )}
            </label>

            {/* Field */}
            <label style={{ display: 'block', marginBottom: 4 }}>
              Field
              {info && (
                <span style={{ color: '#9ca3af', fontSize: 11, marginLeft: 4 }}>
                  range: {info.range}
                </span>
              )}
              <select
                value={cond.field}
                onChange={(e) => updateCond(i, { field: e.target.value as Field })}
                style={{ display: 'block', width: '100%', marginTop: 2 }}
              >
                {FIELD_OPTIONS.map((f) => (
                  <option key={f.value} value={f.value} title={f.hint}>
                    {f.label}
                  </option>
                ))}
              </select>
            </label>

            {/* Operator + Threshold row */}
            <div style={{ display: 'flex', gap: 6 }}>
              <label style={{ flex: 1 }}>
                Op
                <select
                  value={cond.operator}
                  onChange={(e) => updateCond(i, { operator: e.target.value })}
                  style={{ display: 'block', width: '100%', marginTop: 2 }}
                >
                  {OPERATOR_OPTIONS.map((op) => (
                    <option key={op.value} value={op.value}>{op.label}</option>
                  ))}
                </select>
              </label>
              <label style={{ flex: 2 }}>
                Threshold
                <input
                  type="number"
                  step="1"
                  min={0}
                  value={cond.threshold}
                  onChange={(e) => handleThreshold(i, e.target.value)}
                  style={{ display: 'block', width: '100%', marginTop: 2 }}
                />
              </label>
            </div>
          </div>
        )
      })}

      <button
        onClick={addCondition}
        style={{
          fontSize: 12,
          cursor: 'pointer',
          color: '#ea580c',
          background: 'none',
          border: '1px dashed #fdba74',
          borderRadius: 4,
          padding: '4px 10px',
          width: '100%',
          marginBottom: 2,
        }}
      >
        + Add condition
      </button>

      <NodeHelp lines={HELP_LINES} accentColor="#ea580c" />

      {/* Output handle labels */}
      <div style={{ marginTop: 6, fontSize: 11, color: '#6b7280', textAlign: 'right' }}>
        <div style={{ marginBottom: 14 }}>Annotated ●</div>
        <div>Objects ●</div>
      </div>

      {/* AnnotatedStream output — orange */}
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        style={{ background: '#f97316', width: 12, height: 12, top: '70%' }}
      />
      {/* ObjectStream output — blue */}
      <Handle
        type="source"
        position={Position.Right}
        id="objects"
        style={{ background: '#3b82f6', width: 12, height: 12, top: '85%' }}
      />
    </div>
  )
}
