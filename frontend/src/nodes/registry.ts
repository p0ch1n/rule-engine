/**
 * NodeRegistry — Registry Pattern for frontend node type management.
 *
 * Calling registerNodeType() during module load (from each node's index.ts)
 * is the only required step to make a node type available in the canvas.
 */

import type { NodeDefinition } from './types'

const nodeRegistry = new Map<string, NodeDefinition>()

/**
 * Register a node type definition. Throws if the type is already registered.
 */
export function registerNodeType(definition: NodeDefinition): void {
  if (nodeRegistry.has(definition.type)) {
    throw new Error(
      `Node type "${definition.type}" is already registered. ` +
        `Check for duplicate imports or conflicting definitions.`
    )
  }
  nodeRegistry.set(definition.type, definition)
}

/**
 * Retrieve all registered node definitions as a read-only map.
 */
export function getNodeTypes(): ReadonlyMap<string, NodeDefinition> {
  return nodeRegistry
}

/**
 * Retrieve a single node definition by type string.
 * Returns undefined if not found.
 */
export function getNodeDefinition(type: string): NodeDefinition | undefined {
  return nodeRegistry.get(type)
}

/**
 * Build the nodeTypes object expected by React Flow.
 * Keys are node type strings; values are the React components.
 * Cast to `any` is necessary because React Flow's NodeTypes expects NodeProps,
 * but we use our own narrower NodeComponentProps interface.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function buildReactFlowNodeTypes(): Record<string, any> {
  const result: Record<string, unknown> = {}
  for (const [type, def] of nodeRegistry) {
    result[type] = def.component
  }
  return result
}
