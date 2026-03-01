import { ReactFlowProvider } from 'reactflow'
import { FlowCanvas } from './canvas/FlowCanvas'

// Trigger node registration before anything renders
import './nodes/index'

export default function App() {
  return (
    <ReactFlowProvider>
      <FlowCanvas />
    </ReactFlowProvider>
  )
}
