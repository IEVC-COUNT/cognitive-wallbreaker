'use client'

import { useState, useRef, DragEvent } from 'react'
import { Upload, X } from 'lucide-react'

export function ImageUploader({ images, onAdd, onRemove, disabled }: {
  images: File[]; onAdd: (f: File[]) => void; onRemove: (i: number) => void; disabled: boolean
}) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = (e: DragEvent) => {
    e.preventDefault(); setDragging(false)
    const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'))
    if (files.length) onAdd(files.slice(0, 5 - images.length))
  }

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-all ${
          dragging ? 'border-[#818cf8] bg-[#818cf8]/10 scale-[1.02]' : 'border-wall-border hover:border-[#818cf8]/50'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input ref={inputRef} type="file" accept="image/*" multiple onChange={(e) => {
          const files = Array.from(e.target.files || [])
          if (files.length) onAdd(files.slice(0, 5 - images.length))
          if (inputRef.current) inputRef.current.value = ''
        }} className="hidden" disabled={disabled} title="上传图片" aria-label="上传图片文件" />
        <Upload size={20} className="mx-auto mb-1 text-wall-muted" />
        <p className="text-wall-muted text-xs">拖拽图片或点击上传</p>
        <p className="text-wall-dim text-[10px] mt-1">PNG/JPEG/WebP · 最多5张</p>
      </div>
      {images.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {images.map((file, idx) => (
            <div key={idx} className="relative group w-16 h-16 rounded-lg overflow-hidden border border-wall-border">
              <img src={URL.createObjectURL(file)} alt="" className="w-full h-full object-cover" />
              <button onClick={() => onRemove(idx)} disabled={disabled} title="移除图片" aria-label="移除图片"
                className="absolute top-0.5 right-0.5 p-0.5 rounded-full bg-black/60 text-red-400 opacity-0 group-hover:opacity-100 transition-opacity">
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
