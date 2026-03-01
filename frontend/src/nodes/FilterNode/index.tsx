import { Handle, Position } from 'reactflow'
import type { NodeComponentProps } from '../types'
import { usePipelineStore } from '@/store/pipelineStore'
import { NodeHelp } from '../NodeHelp'
import { parseNumericInput } from '@/utils/numericInput'

const FIELD_OPTIONS = ['confidence', 'width', 'height', 'area']
const OPERATOR_OPTIONS = [
  { value: 'gt',  label: '>'  },
  { value: 'gte', label: '>=' },
  { value: 'lt',  label: '<'  },
  { value: 'lte', label: '<=' },
  { value: 'eq',  label: '='  },
]

const HELP_LINES = [
  'Filters a BBox stream by class and numeric criteria.',
  'Add one or more conditions — each targets a class name + numeric field.',
  'AND: a box must pass ALL conditions for its class.',
  'OR:  a box must pass ANY one condition for its class.',
  'Boxes whose class is not in any condition pass through unchanged.',
  'Left port: incoming stream.  Right top: passed.  Right bottom: rejected.',
]

interface FilterCondition {
  class_name: string
  field: string
  operator: string
  threshold: number
}

interface FilterConfig {
  conditions: FilterCondition[]
  logic: 'AND' | 'OR'
}

export function FilterNodeComponent({ id, data, selected }: NodeComponentProps) {
  const updateNodeConfig = usePipelineStore((s) => s.updateNodeConfig)
  const config = data.config as unknown as FilterConfig
  const availableClasses = data.availableClasses ?? []

  const hasEmpty  = config.conditions.some((c) => !c.class_name)
  const isInvalid = config.conditions.length === 0 || hasEmpty

  const setConfig = (updates: Partial<FilterConfig>) =>
    updateNodeConfig(id, { ...config, ...updates } as Record<string, unknown>)

  const updateCond = (i: number, patch: Partial<FilterCondition>) => {
    const next = config.conditions.map((c, idx) => (idx === i ? { ...c, ...patch } : c))
    setConfig({ conditions: next })
  }

  const handleThreshold = (i: number, raw: string) => {
    const v = parseNumericInput(raw, 0.01, 0)
    if (v !== null) updateCond(i, { threshold: v })
  }

  const addCondition = () =>
    setConfig({
      conditions: [
        ...config.conditions,
        { class_name: '', field: 'confidence', operator: 'gt', threshold: 0.5 },
      ],
    })

  const removeCond = (i: number) =>
    setConfig({ conditions: config.conditions.filter((_, idx) => idx !== i) })

  return (
    <div
      style={{
        background: '#e0f0ff',
        border: selected
          ? '2px solid #2563eb'
          : isInvalid
          ? '2px solid #f87171'
          : '2px solid #93c5fd',
        borderRadius: 8,
        padding: '12px 16px',
        minWidth: 260,
        fontSize: 13,
        boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        style={{ background: '#3b82f6', width: 12, height: 12 }}
      />

      {/* Header */}
      <div style={{ fontWeight: 700, marginBottom: 6, color: '#1e40af', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        Filter
        {isInvalid && (
          <span style={{ color: '#dc2626', fontSize: 11, fontWeight: 400 }}>
            {config.conditions.length === 0 ? '⚠ add condition' : '⚠ fill classes'}
          </span>
        )}
      </div>

      {/* Logic selector (only shown when > 1 condition) */}
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

      {/* Conditions list */}
      {config.conditions.map((cond, i) => (
        <div
          key={i}
          style={{
            background: '#f0f7ff',
            border: '1px solid #bfdbfe',
            borderRadius: 6,
            padding: '8px 10px',
            marginBottom: 6,
            position: 'relative',
          }}
        >
          {/* Remove button */}
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
                lineHeight: 1,
              }}
            >
              ✕
            </button>
          )}

          {/* Class */}
          <label style={{ display: 'block', marginBottom: 4 }}>
            Class
            {availableClasses.length > 0 ? (
              <select
                value={cond.class_name}
                onChange={(e) => updateCond(i, { class_name: e.target.value })}
                style={{
                  display: 'block', width: '100%', marginTop: 2,
                  borderColor: !cond.class_name ? '#f87171' : undefined,
                }}
              >
                <option value="">-- select --</option>
                {availableClasses.map((cls) => (
                  <option key={cls} value={cls}>{cls}</option>
                ))}
              </select>
            ) : (
              <input
                value={cond.class_name}
                onChange={(e) => updateCond(i, { class_name: e.target.value })}
                placeholder="class name"
                style={{
                  display: 'block', width: '100%', marginTop: 2,
                  borderColor: !cond.class_name ? '#f87171' : undefined,
                }}
              />
            )}
          </label>

          {/* Field + Operator + Threshold row */}
          <div style={{ display: 'flex', gap: 4 }}>
            <label style={{ flex: 2 }}>
              Field
              <select
                value={cond.field}
                onChange={(e) => updateCond(i, { field: e.target.value })}
                style={{ display: 'block', width: '100%', marginTop: 2 }}
              >
                {FIELD_OPTIONS.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </label>
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
              Value
              <input
                type="number"
                step="0.01"
                min={0}
                value={cond.threshold}
                onChange={(e) => handleThreshold(i, e.target.value)}
                style={{ display: 'block', width: '100%', marginTop: 2 }}
              />
            </label>
          </div>
        </div>
      ))}

      {/* Add condition button */}
      <button
        onClick={addCondition}
        style={{
          fontSize: 12,
          cursor: 'pointer',
          color: '#2563eb',
          background: 'none',
          border: '1px dashed #93c5fd',
          borderRadius: 4,
          padding: '4px 10px',
          width: '100%',
          marginBottom: 2,
        }}
      >
        + Add condition
      </button>

      <NodeHelp lines={HELP_LINES} accentColor="#3b82f6" />

      {/* Output handles */}
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        style={{ background: '#3b82f6', width: 12, height: 12, top: '40%' }}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="rejected"
        style={{ background: '#f87171', width: 12, height: 12, top: '70%' }}
      />
    </div>
  )
}
