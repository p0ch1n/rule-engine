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
      description: 'Merged Object collection to evaluate',
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
    conditions: [{ className: '', minCount: 1, negate: false }],
    triggerLabel: '',
  },
  component: LogicNodeComponent,
}
