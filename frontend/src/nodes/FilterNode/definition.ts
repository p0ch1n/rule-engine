import type { NodeDefinition } from '../types'
import { PortType } from '../types'
import { FilterNodeComponent } from './index'

export const FilterNodeDefinition: NodeDefinition = {
  type: 'filter',
  label: 'Filter',
  description: 'Filter BBoxes by class name and a numeric field comparison',
  inputPorts: [
    {
      name: 'input',
      portType: PortType.BoxStream,
      label: 'Input',
      description: 'Incoming BBox stream',
    },
  ],
  outputPorts: [
    {
      name: 'output',
      portType: PortType.BoxStream,
      label: 'Passed',
      description: 'BBoxes passing the filter',
    },
    {
      name: 'rejected',
      portType: PortType.BoxStream,
      label: 'Rejected',
      description: 'BBoxes failing the filter',
      optional: true,
    },
  ],
  defaultConfig: {
    conditions: [
      { class_name: '', field: 'confidence', operator: 'gt', threshold: 0.5 },
    ],
    logic: 'AND',
  },
  component: FilterNodeComponent,
}
