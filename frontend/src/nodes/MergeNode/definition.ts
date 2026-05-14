import type { NodeDefinition } from '../types'
import { PortType } from '../types'
import { MergeNodeComponent } from './index'

export const MergeNodeDefinition: NodeDefinition = {
  type: 'merge',
  label: 'Merge',
  description: 'Aggregate multiple ObjectStreams into a Collection with lineage tracking',
  inputPorts: [
    { name: 'input_0', portType: PortType.ObjectStream, label: 'In 0' },
    { name: 'input_1', portType: PortType.ObjectStream, label: 'In 1', optional: true },
    { name: 'input_2', portType: PortType.ObjectStream, label: 'In 2', optional: true },
    { name: 'input_3', portType: PortType.ObjectStream, label: 'In 3', optional: true },
  ],
  outputPorts: [
    {
      name: 'output',
      portType: PortType.Collection,
      label: 'Collection',
      description: 'Merged collection with lineage metadata',
    },
  ],
  defaultConfig: {
    topK: 1000,
  },
  component: MergeNodeComponent,
}
