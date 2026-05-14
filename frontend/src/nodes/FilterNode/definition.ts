import type { NodeDefinition } from '../types'
import { PortType } from '../types'
import { FilterNodeComponent } from './index'

export const FilterNodeDefinition: NodeDefinition = {
  type: 'filter',
  label: 'Filter',
  description: 'Filter Objects by class name and a numeric field comparison',
  inputPorts: [
    {
      name: 'input',
      portType: PortType.ObjectStream,
      label: 'Input',
      description: 'Incoming Object stream',
    },
  ],
  outputPorts: [
    {
      name: 'output',
      portType: PortType.ObjectStream,
      label: 'Passed',
      description: 'Objects passing the filter',
    },
    {
      name: 'rejected',
      portType: PortType.ObjectStream,
      label: 'Rejected',
      description: 'Objects failing the filter',
      optional: true,
    },
  ],
  defaultConfig: {
    conditions: [
      { className: '', field: 'confidence', operator: 'gt', threshold: 0.5 },
    ],
    logic: 'AND',
  },
  component: FilterNodeComponent,
}
