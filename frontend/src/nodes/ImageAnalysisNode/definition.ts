import type { NodeDefinition } from '../types'
import { PortType } from '../types'
import { ImageAnalysisNodeComponent } from './index'

export const ImageAnalysisNodeDefinition: NodeDefinition = {
  type: 'image_analysis',
  label: 'Image Analysis',
  description: 'Filter annotated frames by measuring pixel statistics (intensity, RGB, HSV) inside Object ROIs',
  inputPorts: [
    {
      name: 'input',
      portType: PortType.AnnotatedStream,
      label: 'Annotated',
      description: 'Annotated image frames (from DetectionNode or another ImageAnalysisNode)',
    },
  ],
  outputPorts: [
    {
      name: 'output',
      portType: PortType.AnnotatedStream,
      label: 'Annotated',
      description: 'Frames that have at least one surviving Object',
    },
    {
      name: 'objects',
      portType: PortType.ObjectStream,
      label: 'Objects',
      description: 'Surviving Objects, flattened — connects to Filter, Merge, Logic nodes',
      optional: true,
    },
  ],
  defaultConfig: {
    conditions: [
      { className: '', field: 'intensity', operator: 'gt', threshold: 100 },
    ],
    logic: 'AND',
  },
  component: ImageAnalysisNodeComponent,
}
