import { Handle, Position } from 'reactflow'
import type { NodeComponentProps } from '../types'
import { usePipelineStore } from '@/store/pipelineStore'
import { NodeHelp } from '../NodeHelp'
import { parseIntInput } from '@/utils/numericInput'

const HELP_LINES = [
  'Merges multiple BoxStream inputs into a single Collection.',
  'Connect upstream nodes to input ports (in 0, in 1, …).',
  'All boxes are kept — no deduplication. Lineage (source port) is recorded in metadata.',
  'Top-K: keeps only the highest-confidence boxes if total exceeds the limit.',
  'Output is a Collection wire — connect to a Logic node.',
]

const INPUT_PORTS = ['input_0', 'input_1', 'input_2', 'input_3']

// Evenly distribute 4 handles between 15% and 85%
const HANDLE_TOP_PCTS = [15, 38, 62, 85]

export function MergeNodeComponent({ id, data, selected }: NodeComponentProps) {
  const updateNodeConfig = usePipelineStore((s) => s.updateNodeConfig)
  const config = data.config as { top_k: number }

  const handleTopK = (raw: string) => {
    const v = parseIntInput(raw, 1)
    if (v !== null) updateNodeConfig(id, { ...config, top_k: v })
  }

  return (
    <div
      style={{
        background: '#fef3c7',
        border: selected ? '2px solid #d97706' : '2px solid #fbbf24',
        borderRadius: 8,
        padding: '12px 16px',
        minWidth: 200,
        fontSize: 13,
        boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
        position: 'relative',
      }}
    >
      {/* Input handles — one per port, with visible label */}
      {INPUT_PORTS.map((port, i) => (
        <div
          key={port}
          style={{
            position: 'absolute',
            left: -48,
            top: `calc(${HANDLE_TOP_PCTS[i]}% - 8px)`,
            fontSize: 10,
            color: '#92400e',
            textAlign: 'right',
            width: 44,
            lineHeight: '16px',
          }}
        >
          {`in ${i}`}
        </div>
      ))}
      {INPUT_PORTS.map((port, i) => (
        <Handle
          key={port}
          type="target"
          position={Position.Left}
          id={port}
          style={{
            background: '#f59e0b',
            width: 12,
            height: 12,
            top: `${HANDLE_TOP_PCTS[i]}%`,
          }}
        />
      ))}

      <div style={{ fontWeight: 700, marginBottom: 8, color: '#92400e' }}>
        Merge
      </div>

      <label style={{ display: 'block', marginBottom: 4 }}>
        Top-K
        <input
          type="number"
          min={1}
          step={1}
          value={config.top_k}
          onChange={(e) => handleTopK(e.target.value)}
          style={{ display: 'block', width: '100%', marginTop: 2 }}
        />
      </label>

      <NodeHelp lines={HELP_LINES} accentColor="#d97706" />

      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        style={{ background: '#f59e0b', width: 12, height: 12 }}
      />
    </div>
  )
}
