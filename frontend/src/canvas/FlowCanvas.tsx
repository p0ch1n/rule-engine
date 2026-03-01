/**
 * FlowCanvas — main React Flow canvas component.
 *
 * Integrates:
 * - All registered node types
 * - Zustand store (nodes, edges, metadata)
 * - Port type validation
 * - Sidebar for adding nodes
 * - Export / Import controls
 */

import { useCallback, useMemo, useRef } from 'react'
import React from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Panel,
  useReactFlow,
} from 'reactflow'
import 'reactflow/dist/style.css'

import { usePipelineStore } from '@/store/pipelineStore'
import { buildReactFlowNodeTypes, getNodeTypes } from '@/nodes/registry'
import { isValidConnection } from '@/validation/portValidator'
import { enrichNodesWithClasses } from '@/inference/classInferencer'
import {
  downloadPipelineJson,
  importPipelineJson,
} from '@/export/pipelineExporter'
import type { Connection } from 'reactflow'

// ------------------------------------------------------------------ //
// Sidebar — node palette
// ------------------------------------------------------------------ //

function NodePalette() {
  const definitions = Array.from(getNodeTypes().values())

  const onDragStart = (
    e: React.DragEvent,
    type: string,
    defaultConfig: Record<string, unknown>
  ) => {
    e.dataTransfer.setData('application/node-type', type)
    e.dataTransfer.setData(
      'application/node-config',
      JSON.stringify(defaultConfig)
    )
    e.dataTransfer.effectAllowed = 'move'
  }

  return (
    <aside
      style={{
        width: 180,
        background: '#f8fafc',
        borderRight: '1px solid #e2e8f0',
        padding: 12,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      <strong style={{ fontSize: 14, marginBottom: 4 }}>Nodes</strong>
      {definitions.map((def) => (
        <div
          key={def.type}
          draggable
          onDragStart={(e) => onDragStart(e, def.type, def.defaultConfig)}
          title={def.description}
          style={{
            padding: '8px 12px',
            background: '#fff',
            border: '1px solid #cbd5e1',
            borderRadius: 6,
            cursor: 'grab',
            fontSize: 13,
            userSelect: 'none',
          }}
        >
          {def.label}
        </div>
      ))}
    </aside>
  )
}

// ------------------------------------------------------------------ //
// Metadata panel
// ------------------------------------------------------------------ //

function MetadataPanel() {
  const metadata = usePipelineStore((s) => s.metadata)
  const updateMetadata = usePipelineStore((s) => s.updateMetadata)

  // Local draft: non-null while the input is focused so the user can freely
  // type commas without them being eaten by the immediate-split logic.
  const [classListDraft, setClassListDraft] = React.useState<string | null>(null)

  const classListDisplay = classListDraft ?? metadata.class_list.join(', ')

  const commitClassList = () => {
    if (classListDraft !== null) {
      const classList = classListDraft
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
      updateMetadata({ class_list: classList })
      setClassListDraft(null)
    }
  }

  return (
    <Panel
      position="top-right"
      style={{
        background: '#fff',
        border: '1px solid #e2e8f0',
        borderRadius: 8,
        padding: 12,
        minWidth: 240,
        fontSize: 13,
      }}
    >
      <strong style={{ display: 'block', marginBottom: 8 }}>
        Pipeline Metadata
      </strong>
      <label style={{ display: 'block', marginBottom: 6 }}>
        Tool ID
        <input
          value={metadata.tool_id}
          onChange={(e) => updateMetadata({ tool_id: e.target.value })}
          style={{ display: 'block', width: '100%', marginTop: 2 }}
        />
      </label>
      <label style={{ display: 'block' }}>
        Class List (comma-separated)
        <input
          value={classListDisplay}
          onChange={(e) => setClassListDraft(e.target.value)}
          onBlur={commitClassList}
          placeholder="person, car, truck"
          style={{ display: 'block', width: '100%', marginTop: 2 }}
        />
      </label>
    </Panel>
  )
}

// ------------------------------------------------------------------ //
// Export / Import toolbar
// ------------------------------------------------------------------ //

function Toolbar() {
  const nodes = usePipelineStore((s) => s.nodes)
  const edges = usePipelineStore((s) => s.edges)
  const metadata = usePipelineStore((s) => s.metadata)
  const loadPipeline = usePipelineStore((s) => s.loadPipeline)
  const resetPipeline = usePipelineStore((s) => s.resetPipeline)
  const fileRef = useRef<HTMLInputElement>(null)
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null)

  const handleExport = () => {
    downloadPipelineJson(nodes, edges, metadata)
  }

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      const raw = ev.target?.result
      if (typeof raw !== 'string') {
        setErrorMsg('Could not read file.')
        return
      }
      try {
        const { nodes: n, edges: ed, metadata: m } = importPipelineJson(raw)
        loadPipeline(n, ed, m)
        setErrorMsg(null)
      } catch (err) {
        setErrorMsg((err as Error).message)
      }
    }
    reader.readAsText(file)
    if (fileRef.current) fileRef.current.value = ''
  }

  return (
    <Panel
      position="top-left"
      style={{ display: 'flex', flexDirection: 'column', gap: 4 }}
    >
      <div
        style={{
          display: 'flex',
          gap: 8,
          background: '#fff',
          border: '1px solid #e2e8f0',
          borderRadius: 8,
          padding: '8px 12px',
        }}
      >
        <button onClick={handleExport} style={{ cursor: 'pointer', fontSize: 13 }}>
          Export JSON
        </button>
        <button
          onClick={() => fileRef.current?.click()}
          style={{ cursor: 'pointer', fontSize: 13 }}
        >
          Import JSON
        </button>
        <button
          onClick={() => { resetPipeline(); setErrorMsg(null) }}
          style={{ cursor: 'pointer', fontSize: 13, color: '#dc2626' }}
        >
          Reset
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".json"
          onChange={handleImport}
          style={{ display: 'none' }}
        />
      </div>
      {errorMsg && (
        <div
          style={{
            background: '#fef2f2',
            border: '1px solid #fca5a5',
            borderRadius: 6,
            padding: '6px 10px',
            fontSize: 12,
            color: '#991b1b',
            maxWidth: 340,
          }}
        >
          ⚠ {errorMsg}
          <button
            onClick={() => setErrorMsg(null)}
            style={{ marginLeft: 8, cursor: 'pointer', fontSize: 11, border: 'none', background: 'none', color: '#991b1b' }}
          >
            ✕
          </button>
        </div>
      )}
    </Panel>
  )
}

// ------------------------------------------------------------------ //
// Main canvas
// ------------------------------------------------------------------ //

function FlowCanvasInner() {
  const {
    nodes,
    edges,
    metadata,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
  } = usePipelineStore()

  const { screenToFlowPosition } = useReactFlow()

  // Build nodeTypes map once (memoized — stable across renders)
  const nodeTypes = useMemo(() => buildReactFlowNodeTypes(), [])

  // Enrich nodes with inferred class lists whenever topology changes
  const enrichedNodes = useMemo(
    () => enrichNodesWithClasses(nodes, edges, metadata.class_list),
    [nodes, edges, metadata.class_list]
  )

  // Validate connections before accepting them
  const validateConnection = useCallback(
    (connection: Connection) => isValidConnection(connection, nodes, edges),
    [nodes, edges]
  )

  // Drag-and-drop from palette
  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      const type = e.dataTransfer.getData('application/node-type')
      const configStr = e.dataTransfer.getData('application/node-config')
      if (!type) return
      const config = configStr ? JSON.parse(configStr) : {}
      const position = screenToFlowPosition({ x: e.clientX, y: e.clientY })
      addNode(type, position, config)
    },
    [addNode, screenToFlowPosition]
  )

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }, [])

  return (
    <ReactFlow
      nodes={enrichedNodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      isValidConnection={validateConnection}
      nodeTypes={nodeTypes}
      onDrop={onDrop}
      onDragOver={onDragOver}
      fitView
    >
      <Background />
      <Controls />
      <MiniMap />
      <MetadataPanel />
      <Toolbar />
    </ReactFlow>
  )
}

export function FlowCanvas() {
  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw' }}>
      <NodePalette />
      <div style={{ flex: 1 }}>
        <FlowCanvasInner />
      </div>
    </div>
  )
}
