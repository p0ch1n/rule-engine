/**
 * Collapsible usage instructions panel for node components.
 */

import { useState } from 'react'

interface NodeHelpProps {
  lines: string[]
  accentColor?: string
}

export function NodeHelp({ lines, accentColor = '#6b7280' }: NodeHelpProps) {
  const [open, setOpen] = useState(false)

  return (
    <div style={{ marginTop: 8, borderTop: `1px solid ${accentColor}33` }}>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          fontSize: 11,
          color: accentColor,
          padding: '4px 0',
          width: '100%',
          textAlign: 'left',
        }}
      >
        {open ? '▾ Hide help' : '▸ How to use'}
      </button>
      {open && (
        <ul
          style={{
            margin: '4px 0 0 0',
            paddingLeft: 14,
            fontSize: 11,
            color: '#374151',
            lineHeight: 1.6,
          }}
        >
          {lines.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
