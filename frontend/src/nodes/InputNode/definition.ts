import type { NodeDefinition } from '../types'
import { PortType } from '../types'
import { InputNodeComponent } from './index'

export const InputNodeDefinition: NodeDefinition = {
  type: 'input',
  label: 'Input',
  description: 'Upload images or a video to feed into a DetectionNode',
  inputPorts: [],
  outputPorts: [
    {
      name: 'output',
      portType: PortType.ImageStream,
      label: 'Images',
      description: 'Decoded image frames — connect to Detection node input',
    },
  ],
  defaultConfig: {
    sourceType: 'images',
    files: [],
    frameStep: 1,
    maxFrames: 100,
  },
  component: InputNodeComponent,
}
