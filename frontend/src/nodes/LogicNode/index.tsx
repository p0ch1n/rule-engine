import { Handle, Position } from 'reactflow'
import type { NodeComponentProps } from '../types'
import { usePipelineStore } from '@/store/pipelineStore'
import { NodeHelp } from '../NodeHelp'
import { parseIntInput } from '@/utils/numericInput'

const HELP_LINES = [
  'Checks whether certain object classes exist in the input boxes.',
  'Connect a Merge node output OR any ObjectStream (Filter, Relation) to the left port.',
  'AND: ALL listed conditions must pass to trigger.',
  'OR:  ANY one condition passing triggers the signal.',
  '"Min count" sets how many boxes of that class are required.',
  'NOT button: inverts the condition — passes when count < minCount.',
  '  e.g. class=person, min=1, NOT → triggers when no person is present.',
  'Trigger label is included in the output signal metadata.',
  'Right port outputs a LogicSignal — not a Object stream.',
]

interface LogicCondition {
  className: string
  minCount: number
  negate: boolean
}

interface LogicConfig {
  operation: 'AND' | 'OR'
  conditions: LogicCondition[]
  triggerLabel: string
}

export function LogicNodeComponent({ id, data, selected }: NodeComponentProps) {
  const updateNodeConfig = usePipelineStore((s) => s.updateNodeConfig)
  const config = data.config as unknown as LogicConfig
  const availableClasses = data.availableClasses ?? []

  const hasEmptyCondition = config.conditions.some((c) => !c.className)
  const isInvalid = config.conditions.length === 0 || hasEmptyCondition

  const setConfig = (updates: Partial<LogicConfig>) => {
    updateNodeConfig(id, { ...config, ...updates } as Record<string, unknown>)
  }

  const updateCondition = (index: number, updates: Partial<LogicCondition>) => {
    const newConditions = config.conditions.map((c, i) =>
      i === index ? { ...c, ...updates } : c
    )
    setConfig({ conditions: newConditions })
  }

  const handleMinCount = (index: number, raw: string) => {
    const v = parseIntInput(raw, 1)
    if (v !== null) updateCondition(index, { minCount: v })
  }

  const addCondition = () => {
    setConfig({ conditions: [...config.conditions, { className: '', minCount: 1, negate: false }] })
  }

  const removeCondition = (index: number) => {
    setConfig({ conditions: config.conditions.filter((_, i) => i !== index) })
  }

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
        minWidth: 240,
        fontSize: 13,
        boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        style={{ background: '#22c55e', width: 12, height: 12 }}
      />

      <div style={{ fontWeight: 700, marginBottom: 4, color: '#166534', display: 'flex', justifyContent: 'space-between' }}>
        Logic
        {isInvalid && (
          <span style={{ color: '#dc2626', fontSize: 11, fontWeight: 400 }}>
            {config.conditions.length === 0 ? '⚠ add condition' : '⚠ fill classes'}
          </span>
        )}
      </div>

      {/* AND / OR toggle */}
      <label style={{ display: 'block', marginBottom: 6 }}>
        Operation
        <select
          value={config.operation}
          onChange={(e) => setConfig({ operation: e.target.value as 'AND' | 'OR' })}
          style={{ display: 'block', width: '100%', marginTop: 2 }}
        >
          <option value="AND">AND (all must exist)</option>
          <option value="OR">OR (any must exist)</option>
        </select>
      </label>

      {/* Conditions */}
      <div style={{ marginBottom: 6 }}>
        <strong>Conditions</strong>
        {config.conditions.map((cond, i) => (
          <div key={i} style={{ display: 'flex', gap: 4, marginTop: 4, alignItems: 'center', flexWrap: 'wrap' }}>
            {availableClasses.length > 0 ? (
              <select
                value={cond.className}
                onChange={(e) => updateCondition(i, { className: e.target.value })}
                style={{
                  flex: 2,
                  borderColor: !cond.className ? '#f87171' : undefined,
                }}
              >
                <option value="">-- select --</option>
                {availableClasses.map((cls) => (
                  <option key={cls} value={cls}>{cls}</option>
                ))}
              </select>
            ) : (
              <input
                value={cond.className}
                onChange={(e) => updateCondition(i, { className: e.target.value })}
                placeholder="class"
                style={{
                  flex: 2,
                  borderColor: !cond.className ? '#f87171' : undefined,
                }}
              />
            )}
            <input
              type="number"
              min={1}
              step={1}
              value={cond.minCount}
              onChange={(e) => handleMinCount(i, e.target.value)}
              style={{ flex: 1, width: 44 }}
              title="Min count required"
            />
            <button
              onClick={() => updateCondition(i, { negate: !cond.negate })}
              title={cond.negate ? 'NOT active — click to disable' : 'Click to negate (NOT)'}
              style={{
                padding: '0 6px',
                cursor: 'pointer',
                flexShrink: 0,
                fontWeight: 700,
                fontSize: 11,
                borderRadius: 4,
                border: cond.negate ? '1px solid #dc2626' : '1px solid #d1d5db',
                background: cond.negate ? '#fee2e2' : '#f9fafb',
                color: cond.negate ? '#dc2626' : '#6b7280',
              }}
            >
              NOT
            </button>
            <button
              onClick={() => removeCondition(i)}
              style={{ padding: '0 6px', cursor: 'pointer', flexShrink: 0 }}
              title="Remove condition"
            >
              ✕
            </button>
          </div>
        ))}
        <button
          onClick={addCondition}
          style={{ marginTop: 6, fontSize: 12, cursor: 'pointer' }}
        >
          + Add condition
        </button>
      </div>

      {/* Trigger label */}
      <label style={{ display: 'block' }}>
        Trigger label
        <input
          value={config.triggerLabel}
          onChange={(e) => setConfig({ triggerLabel: e.target.value })}
          placeholder="alert label"
          style={{ display: 'block', width: '100%', marginTop: 2 }}
        />
      </label>

      <NodeHelp lines={HELP_LINES} accentColor="#16a34a" />

      <Handle
        type="source"
        position={Position.Right}
        id="signal"
        style={{ background: '#22c55e', width: 12, height: 12 }}
      />
    </div>
  )
}
