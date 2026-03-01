/**
 * Port type validation for React Flow connections.
 *
 * Called by React Flow's isValidConnection prop to enforce the wire
 * type compatibility rules defined in PortType.
 */

import type { Connection } from 'reactflow'
import type { Edge, Node } from 'reactflow'
import { getNodeDefinition } from '@/nodes/registry'
import { PORT_TYPE_COMPATIBILITY, PortType } from '@/nodes/types'
import type { NodeData } from '@/nodes/types'

/**
 * Extract port type for a given node + port handle combo.
 */
function getPortType(
  nodeId: string,
  handleId: string | null,
  handleType: 'source' | 'target',
  nodes: Node<NodeData>[]
): PortType | null {
  const node = nodes.find((n) => n.id === nodeId)
  if (!node) return null

  const definition = getNodeDefinition(node.type ?? '')
  if (!definition) return null

  const ports =
    handleType === 'source' ? definition.outputPorts : definition.inputPorts

  // React Flow v11 passes handleId=null for nodes that have only one handle
  // of a given type. Fall back to the first port so the connection is not
  // incorrectly rejected.
  const port =
    handleId != null ? ports.find((p) => p.name === handleId) : ports[0]
  return port?.portType ?? null
}

/**
 * React Flow isValidConnection callback.
 *
 * Rules enforced:
 * 1. No self-loops.
 * 2. Target port already has an incoming connection → reject.
 * 3. Source and target port types must be compatible.
 */
export function isValidConnection(
  connection: Connection,
  nodes: Node<NodeData>[],
  edges: Edge[]
): boolean {
  const { source, sourceHandle, target, targetHandle } = connection

  if (!source || !target) return false

  // Prevent self-loops
  if (source === target) return false

  // Each target (input) port accepts at most one incoming connection
  const targetPortOccupied = edges.some(
    (e) => e.target === target && e.targetHandle === targetHandle
  )
  if (targetPortOccupied) return false

  // Type compatibility check
  const sourceType = getPortType(source, sourceHandle, 'source', nodes)
  const targetType = getPortType(target, targetHandle, 'target', nodes)

  if (!sourceType || !targetType) return false

  const compatible = PORT_TYPE_COMPATIBILITY[sourceType]
  return compatible.includes(targetType)
}
