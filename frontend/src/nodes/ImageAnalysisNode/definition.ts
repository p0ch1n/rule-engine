import type { NodeDefinition } from '../types'
import { PortType } from '../types'
import { ImageAnalysisNodeComponent } from './index'

export const ImageAnalysisNodeDefinition: NodeDefinition = {
  type: 'image_analysis',
  label: 'Image Analysis',
  description: 'Filter annotated frames by measuring pixel statistics (intensity, RGB, HSV) inside BBox ROIs',
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
      description: 'Frames that have at least one surviving BBox',
    },
    {
      name: 'bboxes',
      portType: PortType.BoxStream,
      label: 'BBoxes',
      description: 'Surviving BBoxes, flattened — connects to Filter, Merge, Logic nodes',
      optional: true,
    },
  ],
  defaultConfig: {
    conditions: [
      { class_name: '', field: 'intensity', operator: 'gt', threshold: 100 },
    ],
    logic: 'AND',
  },
  component: ImageAnalysisNodeComponent,
}
