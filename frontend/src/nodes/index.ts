/**
 * Unified node export — importing this module registers all node types
 * into the NodeRegistry as a side effect.
 */

import { registerNodeType } from './registry'
import { FilterNodeDefinition } from './FilterNode/definition'
import { MergeNodeDefinition } from './MergeNode/definition'
import { LogicNodeDefinition } from './LogicNode/definition'
import { RelationNodeDefinition } from './RelationNode/definition'

// Register all node types
registerNodeType(FilterNodeDefinition)
registerNodeType(MergeNodeDefinition)
registerNodeType(LogicNodeDefinition)
registerNodeType(RelationNodeDefinition)

// Re-export for convenience
export { FilterNodeDefinition } from './FilterNode/definition'
export { MergeNodeDefinition } from './MergeNode/definition'
export { LogicNodeDefinition } from './LogicNode/definition'
export { RelationNodeDefinition } from './RelationNode/definition'

export { registerNodeType, getNodeTypes, getNodeDefinition, buildReactFlowNodeTypes } from './registry'
export * from './types'
