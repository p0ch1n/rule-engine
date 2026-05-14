import type { NodeDefinition } from '../types'
import { PortType } from '../types'
import { RelationNodeComponent } from './index'

export const RelationNodeDefinition: NodeDefinition = {
  type: 'relation',
  label: 'Relation',
  description: 'Pairwise spatial relation detection (IoU / distance) — emits relation Objects',
  inputPorts: [
    {
      name: 'input',
      portType: PortType.ObjectStream,
      label: 'Input A',
      description: 'Primary stream (self-join or cross-join A)',
    },
    {
      name: 'input_b',
      portType: PortType.ObjectStream,
      label: 'Input B',
      description: 'Secondary stream for cross-join (optional)',
      optional: true,
    },
  ],
  outputPorts: [
    {
      name: 'output',
      portType: PortType.ObjectStream,
      label: 'Relations',
      description: 'Relation Objects for qualifying pairs',
    },
  ],
  defaultConfig: {
    mode: 'self_join',
    relationType: 'iou',
    threshold: 0.3,
    filterClassA: '',
    filterClassB: '',
    outputClassName: '',
    offset: { dx: 0, dy: 0, dw: 0, dh: 0 },
    scale: { sx: 1, sy: 1, sw: 1, sh: 1 },
  },
  component: RelationNodeComponent,
}
