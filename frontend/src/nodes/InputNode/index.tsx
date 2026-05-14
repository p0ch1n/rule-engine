import { Handle, Position } from 'reactflow'
import { useRef } from 'react'
import type { NodeComponentProps } from '../types'
import { PortType, PORT_TYPE_COLORS } from '../types'
import { usePipelineStore } from '@/store/pipelineStore'
import { NodeHelp } from '../NodeHelp'

const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp']
const ACCEPTED_VIDEO_TYPES = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska', 'video/webm']
const MAX_FILE_BYTES = 50 * 1024 * 1024  // 50 MB

const HELP_LINES = [
  'Images / Video: upload files for prototyping in the UI.',
  'External: no stored files — images are injected at runtime by Python code.',
  'Export the config and call pipeline.execute_frame(images=[...]) in your code.',
  'Frame step / Max frames apply to Video mode only.',
  'Right port (purple): ImageStream — connects to Detection input.',
]

interface InputFile {
  filename: string
  data: string
}

interface InputConfig {
  sourceType: 'images' | 'video' | 'external'
  files: InputFile[]
  frameStep: number
  maxFrames: number
}

const IMAGE_COLOR = PORT_TYPE_COLORS[PortType.ImageStream]  // '#7c3aed'

export function InputNodeComponent({ id, data, selected }: NodeComponentProps) {
  const updateNodeConfig = usePipelineStore((s) => s.updateNodeConfig)
  const config = data.config as unknown as InputConfig
  const fileInputRef = useRef<HTMLInputElement>(null)

  const setConfig = (patch: Partial<InputConfig>) =>
    updateNodeConfig(id, { ...config, ...patch } as Record<string, unknown>)

  const handleSourceTypeChange = (type: 'images' | 'video' | 'external') =>
    setConfig({ sourceType: type, files: [] })

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = Array.from(e.target.files ?? [])
    if (!fileList.length) return

    const accepted = config.sourceType === 'images' ? ACCEPTED_IMAGE_TYPES : ACCEPTED_VIDEO_TYPES
    const valid = fileList.filter((f) => accepted.includes(f.type) && f.size <= MAX_FILE_BYTES)

    const newFiles: InputFile[] = await Promise.all(
      valid.map(async (file) => ({ filename: file.name, data: await readAsDataURL(file) }))
    )

    if (config.sourceType === 'video') {
      setConfig({ files: newFiles.slice(0, 1) })
    } else {
      setConfig({ files: [...config.files, ...newFiles] })
    }

    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const removeFile = (i: number) =>
    setConfig({ files: config.files.filter((_, idx) => idx !== i) })

  const isExternal = config.sourceType === 'external'
  const isInvalid = !isExternal && config.files.length === 0
  const accepted = config.sourceType === 'images' ? ACCEPTED_IMAGE_TYPES.join(',') : ACCEPTED_VIDEO_TYPES.join(',')

  return (
    <div
      style={{
        background: '#f5f3ff',
        border: selected
          ? `2px solid ${IMAGE_COLOR}`
          : isInvalid
          ? '2px solid #f87171'
          : '2px solid #c4b5fd',
        borderRadius: 8,
        padding: '12px 16px',
        minWidth: 260,
        fontSize: 13,
        boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
      }}
    >
      {/* Header */}
      <div
        style={{
          fontWeight: 700,
          marginBottom: 8,
          color: '#6d28d9',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        Input
        {isInvalid && (
          <span style={{ color: '#dc2626', fontSize: 11, fontWeight: 400 }}>⚠ no files</span>
        )}
      </div>

      {/* Source type toggle */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
        {(['images', 'video', 'external'] as const).map((t) => (
          <button
            key={t}
            onClick={() => handleSourceTypeChange(t)}
            style={{
              flex: 1,
              padding: '4px 0',
              border: `1px solid ${config.sourceType === t ? IMAGE_COLOR : '#d1d5db'}`,
              borderRadius: 4,
              background: config.sourceType === t ? '#ede9fe' : 'white',
              color: config.sourceType === t ? '#6d28d9' : '#6b7280',
              fontWeight: config.sourceType === t ? 700 : 400,
              cursor: 'pointer',
              fontSize: 11,
            }}
          >
            {t === 'images' ? 'Images' : t === 'video' ? 'Video' : 'External'}
          </button>
        ))}
      </div>

      {/* External mode info */}
      {isExternal && (
        <div
          style={{
            background: '#ede9fe',
            border: '1px solid #c4b5fd',
            borderRadius: 6,
            padding: '8px 10px',
            fontSize: 11,
            color: '#5b21b6',
            marginBottom: 8,
            lineHeight: 1.5,
          }}
        >
          Images injected at runtime via
          <br />
          <code style={{ fontFamily: 'monospace', fontSize: 10 }}>
            execute_frame(images=[...])
          </code>
        </div>
      )}

      {/* Hidden file input */}
      {!isExternal && (
        <input
          ref={fileInputRef}
          type="file"
          multiple={config.sourceType === 'images'}
          accept={accepted}
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
      )}

      {/* Upload zone */}
      {!isExternal && (
        <button
          onClick={() => fileInputRef.current?.click()}
          style={{
            width: '100%',
            padding: '10px',
            border: '2px dashed #c4b5fd',
            borderRadius: 6,
            background: '#faf5ff',
            color: '#7c3aed',
            cursor: 'pointer',
            fontSize: 12,
            marginBottom: 8,
          }}
        >
          + {config.sourceType === 'images' ? 'Add images' : 'Select video'}
        </button>
      )}

      {/* File list */}
      {config.files.length > 0 && (
        <div style={{ maxHeight: 110, overflowY: 'auto', marginBottom: 6 }}>
          {config.files.map((f, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: '#ede9fe',
                borderRadius: 4,
                padding: '3px 8px',
                marginBottom: 3,
                fontSize: 11,
              }}
            >
              <span
                style={{
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  flex: 1,
                  color: '#5b21b6',
                }}
              >
                {f.filename}
              </span>
              <button
                onClick={() => removeFile(i)}
                title="Remove"
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#9ca3af',
                  marginLeft: 4,
                  fontSize: 11,
                  lineHeight: 1,
                }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Video-only options */}
      {config.sourceType === 'video' && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
          <label style={{ flex: 1 }}>
            Frame step
            <input
              type="number"
              min={1}
              value={config.frameStep}
              onChange={(e) => {
                const v = parseInt(e.target.value, 10)
                if (v >= 1) setConfig({ frameStep: v })
              }}
              style={{ display: 'block', width: '100%', marginTop: 2 }}
            />
          </label>
          <label style={{ flex: 1 }}>
            Max frames
            <input
              type="number"
              min={1}
              value={config.maxFrames}
              onChange={(e) => {
                const v = parseInt(e.target.value, 10)
                if (v >= 1) setConfig({ maxFrames: v })
              }}
              style={{ display: 'block', width: '100%', marginTop: 2 }}
            />
          </label>
        </div>
      )}

      <NodeHelp lines={HELP_LINES} accentColor="#7c3aed" />

      {/* Output label */}
      <div style={{ fontSize: 11, color: '#6b7280', textAlign: 'right', marginTop: 6 }}>
        Images ●
      </div>

      {/* ImageStream output handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        style={{ background: IMAGE_COLOR, width: 12, height: 12 }}
      />
    </div>
  )
}

function readAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(new Error(`Failed to read: ${file.name}`))
    reader.readAsDataURL(file)
  })
}
