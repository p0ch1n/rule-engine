/**
 * Class inferencer — recursively derive available class_list for a given node
 * by traversing upstream nodes in the DAG.
 *
 * Strategy:
 * 1. Start at the target node.
 * 2. Walk upstream via edges (BFS/DFS).
 * 3. If we reach a FilterNode, add its configured class_name.
 * 4. If we reach a source (no upstream edges), use the global class_list.
 * 5. Return deduplicated union of all discovered classes.
 */

import type { Edge, Node } from 'reactflow'
import type { NodeData } from '@/nodes/types'

/**
 * Infer available class labels for `targetNodeId` by walking the upstream DAG.
 *
 * @param targetNodeId  The node whose available classes we want to determine.
 * @param nodes         All nodes in the pipeline.
 * @param edges         All edges in the pipeline.
 * @param globalClasses The camera-level class_list (fallback for source nodes).
 * @param maxDepth      Cycle guard — stops recursion beyond this depth.
 */
export function inferAvailableClasses(
  targetNodeId: string,
  nodes: Node<NodeData>[],
  edges: Edge[],
  globalClasses: string[],
  maxDepth = 20
): string[] {
  const visited = new Set<string>()
  const classes = new Set<string>()

  function walk(nodeId: string, depth: number): void {
    if (depth > maxDepth || visited.has(nodeId)) return
    visited.add(nodeId)

    // Find edges that feed INTO this node
    const incomingEdges = edges.filter((e) => e.target === nodeId)

    if (incomingEdges.length === 0) {
      // Source node — contribute global class list
      globalClasses.forEach((cls) => classes.add(cls))
      return
    }

    for (const edge of incomingEdges) {
      const sourceNode = nodes.find((n) => n.id === edge.source)
      if (!sourceNode) continue

      // If the upstream node is a filter, it contributes its filtered class
      if (sourceNode.type === 'filter') {
        const filterClass = sourceNode.data.config.class_name as string | undefined
        if (filterClass) classes.add(filterClass)
        // Continue walking further upstream
        walk(edge.source, depth + 1)
      } else {
        // Non-filter nodes: walk upstream to find what feeds them
        walk(edge.source, depth + 1)
      }
    }
  }

  walk(targetNodeId, 0)

  return Array.from(classes).sort()
}

/**
 * Compute and inject availableClasses into all node data objects.
 * Returns new node array (immutable pattern).
 */
export function enrichNodesWithClasses(
  nodes: Node<NodeData>[],
  edges: Edge[],
  globalClasses: string[]
): Node<NodeData>[] {
  return nodes.map((node) => {
    const available = inferAvailableClasses(
      node.id,
      nodes,
      edges,
      globalClasses
    )
    const current = [...(node.data.availableClasses ?? [])].sort()
    if (
      available.length === current.length &&
      available.every((v, i) => v === current[i])
    ) {
      return node // no change — avoid unnecessary re-render
    }
    return {
      ...node,
      data: { ...node.data, availableClasses: available },
    }
  })
}
