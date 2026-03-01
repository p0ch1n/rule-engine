/**
 * Pipeline exporter / importer — converts between React Flow state and
 * the shared pipeline.schema.json format.
 */

import type { Edge, Node } from 'reactflow'
import type { NodeData, PipelineJSON, PipelineMetadata } from '@/nodes/types'
import { getNodeDefinition } from '@/nodes/registry'

// ------------------------------------------------------------------ //
// Export
// ------------------------------------------------------------------ //

/**
 * Serialize the current canvas state to the pipeline JSON format.
 */
export function exportPipeline(
  nodes: Node<NodeData>[],
  edges: Edge[],
  metadata: PipelineMetadata
): PipelineJSON {
  const pipelineNodes = nodes.map((n) => ({
    id: n.id,
    type: n.type ?? 'unknown',
    position: { x: Math.round(n.position.x), y: Math.round(n.position.y) },
    config: n.data.config,
  }))

  // Map React Flow edges → pipeline edges
  // React Flow uses sourceHandle / targetHandle; we map to source_port / target_port
  const pipelineEdges = edges.map((e) => ({
    id: e.id,
    source: e.source,
    source_port: e.sourceHandle ?? 'output',
    target: e.target,
    target_port: e.targetHandle ?? 'input',
  }))

  return {
    version: '1.0',
    metadata,
    nodes: pipelineNodes,
    edges: pipelineEdges,
  }
}

/**
 * Serialize to a pretty-printed JSON string.
 */
export function exportPipelineJson(
  nodes: Node<NodeData>[],
  edges: Edge[],
  metadata: PipelineMetadata
): string {
  return JSON.stringify(exportPipeline(nodes, edges, metadata), null, 2)
}

/**
 * Trigger a browser download of the pipeline JSON.
 */
export function downloadPipelineJson(
  nodes: Node<NodeData>[],
  edges: Edge[],
  metadata: PipelineMetadata,
  filename = 'pipeline.json'
): void {
  const json = exportPipelineJson(nodes, edges, metadata)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

// ------------------------------------------------------------------ //
// Import
// ------------------------------------------------------------------ //

/**
 * Deserialize a pipeline JSON into React Flow nodes, edges and metadata.
 */
export function importPipeline(json: PipelineJSON): {
  nodes: Node<NodeData>[]
  edges: Edge[]
  metadata: PipelineMetadata
} {
  // Validate all node types are registered before importing
  const unknownTypes = json.nodes
    .map((n) => n.type)
    .filter((t) => !getNodeDefinition(t))
  if (unknownTypes.length > 0) {
    throw new Error(
      `Unknown node type(s) in pipeline: ${unknownTypes.join(', ')}. ` +
        `Make sure all node modules are loaded.`
    )
  }

  const nodes: Node<NodeData>[] = json.nodes.map((n) => ({
    id: n.id,
    type: n.type,
    position: n.position,
    data: {
      label: n.type,
      nodeType: n.type,
      config: n.config,
      availableClasses: json.metadata.class_list,
    },
  }))

  const edges: Edge[] = json.edges.map((e) => ({
    id: e.id,
    source: e.source,
    sourceHandle: e.source_port,
    target: e.target,
    targetHandle: e.target_port,
  }))

  return { nodes, edges, metadata: json.metadata }
}

/**
 * Parse a JSON string and import the pipeline.
 * Throws on parse error — caller should handle.
 */
export function importPipelineJson(jsonStr: string): {
  nodes: Node<NodeData>[]
  edges: Edge[]
  metadata: PipelineMetadata
} {
  const parsed = JSON.parse(jsonStr) as PipelineJSON
  return importPipeline(parsed)
}
