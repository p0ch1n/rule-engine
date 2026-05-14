import type { NodeDefinition } from '../types'
import { PortType } from '../types'
import { DetectionNodeComponent } from './index'

export const DetectionNodeDefinition: NodeDefinition = {
  type: 'detection',
  label: 'Detection',
  description: 'Run an object detection model on input images and output a Object stream',
  inputPorts: [
    {
      name: 'input',
      portType: PortType.ImageStream,
      label: 'Images',
      description: 'Input image frames (List[np.ndarray])',
    },
  ],
  outputPorts: [
    {
      name: 'output',
      portType: PortType.ObjectStream,
      label: 'Objects',
      description: 'Detected bounding boxes, flattened across all input frames',
    },
    {
      name: 'annotated',
      portType: PortType.AnnotatedStream,
      label: 'Annotated',
      description: 'Image + per-frame Object pairs — connect to ImageAnalysisNode',
      optional: true,
    },
  ],
  defaultConfig: {
    architecture: 'yolov12',
    modelName: '',
    confidenceThreshold: 0.5,
    nmsThreshold: 0.45,
    device: 'cpu',
  },
  component: DetectionNodeComponent,
}
