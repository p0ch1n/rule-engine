import type { NodeDefinition } from '../types'
import { PortType } from '../types'
import { RelationNodeComponent } from './index'

export const RelationNodeDefinition: NodeDefinition = {
  type: 'relation',
  label: 'Relation',
  description: 'Pairwise spatial relation detection (IoU / distance) — emits relation BBoxes',
  inputPorts: [
    {
      name: 'input',
      portType: PortType.BoxStream,
      label: 'Input A',
      description: 'Primary stream (self-join or cross-join A)',
    },
    {
      name: 'input_b',
      portType: PortType.BoxStream,
      label: 'Input B',
      description: 'Secondary stream for cross-join (optional)',
      optional: true,
    },
  ],
  outputPorts: [
    {
      name: 'output',
      portType: PortType.BoxStream,
      label: 'Relations',
      description: 'Relation BBoxes for qualifying pairs',
    },
  ],
  defaultConfig: {
    mode: 'self_join',
    relation_type: 'iou',
    threshold: 0.3,
    filter_class_a: '',
    filter_class_b: '',
    output_class_name: '',
    offset: { dx: 0, dy: 0, dw: 0, dh: 0 },
    scale: { sx: 1, sy: 1, sw: 1, sh: 1 },
  },
  component: RelationNodeComponent,
}
