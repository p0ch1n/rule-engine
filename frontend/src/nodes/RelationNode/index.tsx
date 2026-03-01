import { Handle, Position } from 'reactflow'
import type { NodeComponentProps } from '../types'
import { usePipelineStore } from '@/store/pipelineStore'
import { NodeHelp } from '../NodeHelp'
import { parseNumericInput } from '@/utils/numericInput'

const HELP_LINES = [
  'Finds pairs of boxes with a spatial relationship and emits a new box for each pair.',
  'Self Join: compares boxes within a single stream against each other.',
  'Cross Join: compares stream A against stream B (connect Input B).',
  'Relation types: IoU overlap, centroid distance, contains.',
  'Threshold: minimum IoU (or max distance) for a pair to qualify.',
  'Class A / Class B: filter which classes participate on each side.',
  '  e.g. Class A=person, Class B=car → only person-car IoU is computed.',
  '  Leave blank to include all classes.',
  'Output Class Name: class label assigned to each output relation box.',
  '  Leave blank for auto label "A+B" (e.g. "person+car").',
  'Offset / Scale: transform the output box (e.g. expand 10%: scale sw/sh = 1.1).',
  'Output is a BoxStream — each box represents one qualifying pair.',
]

interface RelationConfig {
  mode: 'self_join' | 'cross_join'
  relation_type: 'iou' | 'distance' | 'contains' | 'centroid_distance'
  threshold: number
  filter_class_a: string
  filter_class_b: string
  output_class_name: string
  offset: { dx: number; dy: number; dw: number; dh: number }
  scale: { sx: number; sy: number; sw: number; sh: number }
}

export function RelationNodeComponent({ id, data, selected }: NodeComponentProps) {
  const updateNodeConfig = usePipelineStore((s) => s.updateNodeConfig)
  const config = data.config as unknown as RelationConfig
  const availableClasses = data.availableClasses ?? []
  const isCrossJoin = config.mode === 'cross_join'

  const set = (updates: Partial<RelationConfig>) => {
    updateNodeConfig(id, { ...config, ...updates } as Record<string, unknown>)
  }

  const setOffset = (key: keyof RelationConfig['offset'], raw: string) => {
    const v = parseNumericInput(raw, 1)
    if (v !== null) set({ offset: { ...config.offset, [key]: v } })
  }

  const setScale = (key: keyof RelationConfig['scale'], raw: string) => {
    const v = parseNumericInput(raw, 0.1, 0)
    if (v !== null) set({ scale: { ...config.scale, [key]: v } })
  }

  const handleThreshold = (raw: string) => {
    const v = parseNumericInput(raw, 0.01, 0)
    if (v !== null) set({ threshold: v })
  }

  return (
    <div
      style={{
        background: '#fdf4ff',
        border: selected ? '2px solid #9333ea' : '2px solid #d8b4fe',
        borderRadius: 8,
        padding: '12px 16px',
        minWidth: 260,
        fontSize: 13,
        boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
        position: 'relative',
      }}
    >
      {/* Input A — always shown */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        style={{
          background: '#a855f7',
          width: 12,
          height: 12,
          top: isCrossJoin ? '35%' : '50%',
        }}
      />
      {/* Input B — only rendered (and connectable) in cross_join mode */}
      {isCrossJoin && (
        <Handle
          type="target"
          position={Position.Left}
          id="input_b"
          style={{ background: '#c084fc', width: 10, height: 10, top: '65%' }}
        />
      )}

      <div style={{ fontWeight: 700, marginBottom: 8, color: '#6b21a8' }}>
        Relation
      </div>

      <label style={{ display: 'block', marginBottom: 4 }}>
        Mode
        <select
          value={config.mode}
          onChange={(e) => set({ mode: e.target.value as RelationConfig['mode'] })}
          style={{ display: 'block', width: '100%', marginTop: 2 }}
        >
          <option value="self_join">Self Join (1 input)</option>
          <option value="cross_join">Cross Join (2 inputs)</option>
        </select>
      </label>

      {isCrossJoin && (
        <div style={{ fontSize: 11, color: '#7c3aed', marginBottom: 6 }}>
          Connect a second stream to Input B
        </div>
      )}

      <label style={{ display: 'block', marginBottom: 4 }}>
        Relation Type
        <select
          value={config.relation_type}
          onChange={(e) =>
            set({ relation_type: e.target.value as RelationConfig['relation_type'] })
          }
          style={{ display: 'block', width: '100%', marginTop: 2 }}
        >
          <option value="iou">IoU Overlap</option>
          <option value="distance">Distance</option>
          <option value="centroid_distance">Centroid Distance</option>
          <option value="contains">Contains</option>
        </select>
      </label>

      <label style={{ display: 'block', marginBottom: 8 }}>
        Threshold
        <input
          type="number"
          step="0.01"
          min={0}
          value={config.threshold}
          onChange={(e) => handleThreshold(e.target.value)}
          style={{ display: 'block', width: '100%', marginTop: 2 }}
        />
      </label>

      {/* Class filters */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 8 }}>
        {(['filter_class_a', 'filter_class_b'] as const).map((key, idx) => {
          const label = isCrossJoin
            ? (idx === 0 ? 'Class (Input A)' : 'Class (Input B)')
            : (idx === 0 ? 'Class A' : 'Class B')
          return (
            <label key={key}>
              {label}
              {availableClasses.length > 0 ? (
                <select
                  value={config[key]}
                  onChange={(e) => set({ [key]: e.target.value } as Partial<RelationConfig>)}
                  style={{ display: 'block', width: '100%', marginTop: 2 }}
                >
                  <option value="">-- all --</option>
                  {availableClasses.map((cls) => (
                    <option key={cls} value={cls}>{cls}</option>
                  ))}
                </select>
              ) : (
                <input
                  value={config[key]}
                  onChange={(e) => set({ [key]: e.target.value } as Partial<RelationConfig>)}
                  placeholder="all classes"
                  style={{ display: 'block', width: '100%', marginTop: 2 }}
                />
              )}
            </label>
          )
        })}
      </div>

      {/* Output class name */}
      <label style={{ display: 'block', marginBottom: 8 }}>
        Output Class Name
        {availableClasses.length > 0 ? (
          <select
            value={config.output_class_name}
            onChange={(e) => set({ output_class_name: e.target.value })}
            style={{ display: 'block', width: '100%', marginTop: 2 }}
          >
            <option value="">-- auto (A+B) --</option>
            {availableClasses.map((cls) => (
              <option key={cls} value={cls}>{cls}</option>
            ))}
          </select>
        ) : (
          <input
            value={config.output_class_name}
            onChange={(e) => set({ output_class_name: e.target.value })}
            placeholder="leave blank for auto (A+B)"
            style={{ display: 'block', width: '100%', marginTop: 2 }}
          />
        )}
      </label>

      {/* Offset */}
      <details style={{ marginBottom: 6 }}>
        <summary style={{ cursor: 'pointer', color: '#7c3aed' }}>
          Offset (dx, dy, dw, dh)
        </summary>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, marginTop: 4 }}>
          {(['dx', 'dy', 'dw', 'dh'] as const).map((k) => (
            <label key={k}>
              {k}
              <input
                type="number"
                step="1"
                value={config.offset[k]}
                onChange={(e) => setOffset(k, e.target.value)}
                style={{ display: 'block', width: '100%' }}
              />
            </label>
          ))}
        </div>
      </details>

      {/* Scale */}
      <details>
        <summary style={{ cursor: 'pointer', color: '#7c3aed' }}>
          Scale (sx, sy, sw, sh)
        </summary>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, marginTop: 4 }}>
          {(['sx', 'sy', 'sw', 'sh'] as const).map((k) => (
            <label key={k}>
              {k}
              <input
                type="number"
                step="0.1"
                min={0}
                value={config.scale[k]}
                onChange={(e) => setScale(k, e.target.value)}
                style={{ display: 'block', width: '100%' }}
              />
            </label>
          ))}
        </div>
      </details>

      <NodeHelp lines={HELP_LINES} accentColor="#9333ea" />

      <Handle
        type="source"
        position={Position.Right}
        id="output"
        style={{ background: '#a855f7', width: 12, height: 12 }}
      />
    </div>
  )
}
