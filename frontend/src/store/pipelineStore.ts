/**
 * Zustand store for the pipeline editor state.
 *
 * Immutable update pattern: all mutations return new state objects.
 */

import { create } from 'zustand'
import type { Edge, Node, OnEdgesChange, OnNodesChange } from 'reactflow'
import { addEdge, applyEdgeChanges, applyNodeChanges } from 'reactflow'
import type { Connection } from 'reactflow'
import type { PipelineMetadata, NodeData } from '@/nodes/types'

// ------------------------------------------------------------------ //
// Helpers
// ------------------------------------------------------------------ //

let _edgeSeq = 0
function nextEdgeId(): string {
  return `e-${++_edgeSeq}`
}

/**
 * Compute a safe _nodeCounter from imported node IDs so newly added
 * nodes never collide. Parses trailing numbers from IDs like "filter-3".
 */
function maxNodeCounter(nodes: Node<NodeData>[]): number {
  return nodes.reduce((max, n) => {
    const m = n.id.match(/(\d+)$/)
    return m ? Math.max(max, parseInt(m[1], 10)) : max
  }, nodes.length)
}

// ------------------------------------------------------------------ //
// State shape
// ------------------------------------------------------------------ //

interface PipelineState {
  /** React Flow nodes */
  nodes: Node<NodeData>[]
  /** React Flow edges */
  edges: Edge[]
  /** Pipeline-level metadata */
  metadata: PipelineMetadata
  /** Counter for auto-generated node IDs */
  _nodeCounter: number
}

interface PipelineActions {
  onNodesChange: OnNodesChange
  onEdgesChange: OnEdgesChange
  onConnect: (connection: Connection) => void
  addNode: (type: string, position: { x: number; y: number }, defaultConfig: Record<string, unknown>) => void
  removeNode: (id: string) => void
  updateNodeConfig: (id: string, config: Record<string, unknown>) => void
  updateMetadata: (patch: Partial<PipelineMetadata>) => void
  loadPipeline: (nodes: Node<NodeData>[], edges: Edge[], metadata: PipelineMetadata) => void
  resetPipeline: () => void
}

// ------------------------------------------------------------------ //
// Initial state
// ------------------------------------------------------------------ //

const INITIAL_METADATA: PipelineMetadata = {
  toolId: 'cam-01',
  classList: ['person', 'car', 'truck'],
}

const INITIAL_STATE: PipelineState = {
  nodes: [],
  edges: [],
  metadata: INITIAL_METADATA,
  _nodeCounter: 0,
}

// ------------------------------------------------------------------ //
// Store
// ------------------------------------------------------------------ //

export const usePipelineStore = create<PipelineState & PipelineActions>((set) => ({
  ...INITIAL_STATE,

  onNodesChange: (changes) =>
    set((state) => ({ nodes: applyNodeChanges(changes, state.nodes) })),

  onEdgesChange: (changes) =>
    set((state) => ({ edges: applyEdgeChanges(changes, state.edges) })),

  onConnect: (connection) =>
    set((state) => ({
      edges: addEdge({ ...connection, id: nextEdgeId() }, state.edges),
    })),

  addNode: (type, position, defaultConfig) =>
    set((state) => {
      const counter = state._nodeCounter + 1
      const newNode: Node<NodeData> = {
        id: `${type}-${counter}`,
        type,
        position,
        data: {
          label: type,
          nodeType: type,
          config: defaultConfig,
          availableClasses: state.metadata.classList,
        },
      }
      return {
        nodes: [...state.nodes, newNode],
        _nodeCounter: counter,
      }
    }),

  removeNode: (id) =>
    set((state) => ({
      nodes: state.nodes.filter((n) => n.id !== id),
      edges: state.edges.filter((e) => e.source !== id && e.target !== id),
    })),

  updateNodeConfig: (id, config) =>
    set((state) => ({
      nodes: state.nodes.map((n) =>
        n.id === id ? { ...n, data: { ...n.data, config } } : n
      ),
    })),

  updateMetadata: (patch) =>
    set((state) => ({
      metadata: { ...state.metadata, ...patch },
    })),

  loadPipeline: (nodes, edges, metadata) =>
    set(() => ({
      nodes,
      edges,
      metadata,
      _nodeCounter: maxNodeCounter(nodes),
    })),

  resetPipeline: () =>
    set(() => ({ ...INITIAL_STATE })),
}))
