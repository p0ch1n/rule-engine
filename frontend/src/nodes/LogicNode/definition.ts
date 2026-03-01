import type { NodeDefinition } from '../types'
import { PortType } from '../types'
import { LogicNodeComponent } from './index'

export const LogicNodeDefinition: NodeDefinition = {
  type: 'logic',
  label: 'Logic',
  description: 'Existential condition check: AND/OR presence of classes in a Collection',
  inputPorts: [
    {
      name: 'input',
      portType: PortType.Collection,
      label: 'Collection',
      description: 'Merged BBox collection to evaluate',
    },
  ],
  outputPorts: [
    {
      name: 'signal',
      portType: PortType.LogicSignal,
      label: 'Signal',
      description: 'Boolean trigger with metadata',
    },
  ],
  defaultConfig: {
    operation: 'AND',
    conditions: [{ class_name: '', min_count: 1, negate: false }],
    trigger_label: '',
  },
  component: LogicNodeComponent,
}
