import type { NodeDefinition } from '../types'
import { PortType } from '../types'
import { DetectionNodeComponent } from './index'

export const DetectionNodeDefinition: NodeDefinition = {
  type: 'detection',
  label: 'Detection',
  description: 'Run an object detection model on input images and output a BBox stream',
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
      portType: PortType.BoxStream,
      label: 'BBoxes',
      description: 'Detected bounding boxes, flattened across all input frames',
    },
    {
      name: 'annotated',
      portType: PortType.AnnotatedStream,
      label: 'Annotated',
      description: 'Image + per-frame BBox pairs — connect to ImageAnalysisNode',
      optional: true,
    },
  ],
  defaultConfig: {
    architecture: 'yolov12',
    model_name: '',
    confidence_threshold: 0.5,
    nms_threshold: 0.45,
    device: 'cpu',
  },
  component: DetectionNodeComponent,
}
