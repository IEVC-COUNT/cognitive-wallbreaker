'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Loader2, CornerDownLeft, Zap, Trash2, Brain } from 'lucide-react'
import { ImageUploader } from '@/components/ImageUploader'
import { MarkdownOutput } from '@/components/MarkdownOutput'
import { TopologyViewer } from '@/components/TopologyViewer'
import { useWallbreaker } from '@/hooks/useWallbreaker'

export default function SubmitPage() {
  const [input, setInput] = useState('')
  const [images, setImages] = useState<File[]>([])
  const { output, thinking, error, loadingText, stats, topoNodes, topoEdges, topoReady,
    setTopoNodes, setTopoEdges, setOutput, setTopoReady, simulate, reset, eventId, v5Agents } = useWallbreaker()
  const router = useRouter()

  const handleSubmit = useCallback(async () => {
    if (!input.trim()) return
    await simulate(input.trim(), images, '/api/public/submit', (id) => {
      setTimeout(() => router.push(`/event/${id}`), 500)
    })
  }, [input, images, simulate, router])

  return (
    <div className="min-h-screen flex flex-col">
      <div className="flex-1 flex flex-col lg:flex-row">
        {/* Left: Input */}
        <div className="flex-1 flex flex-col items-center justify-center p-6 lg:p-12 border-r border-wall-border/50">
          <div className="w-full max-w-xl space-y-6">
            <div className="text-center space-y-2 mb-2">
              <h1 className="text-2xl font-bold"><span className="text-[#818cf8]">提交决策</span></h1>
              <p className="text-wall-muted text-xs font-mono">提交个人决策，七Agent公开推演，所有人可浏览</p>
            </div>
            <div className="relative">
              <div className="absolute -inset-1 bg-[#818cf8]/5 rounded-2xl blur-xl" />
              <textarea value={input} onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit() } }}
                placeholder="告诉我你正在纠结的个人决策..." disabled={thinking}
                className="relative w-full h-32 bg-wall-surface border border-wall-border rounded-xl p-5 text-wall-text placeholder-wall-muted/40 resize-none focus:outline-none focus:border-[#818cf8]/50 transition-colors disabled:opacity-50 text-sm leading-relaxed"
              />
            </div>
            <ImageUploader images={images} onAdd={(f) => setImages(p => [...p, ...f].slice(0, 5))}
              onRemove={(i) => setImages(p => p.filter((_, j) => j !== i))} disabled={thinking} />
            <div className="flex gap-3 justify-center">
              <button onClick={handleSubmit}
                disabled={!input.trim() || thinking}
                className="flex items-center gap-2 px-6 py-3 bg-[#818cf8]/10 border border-[#818cf8]/30 rounded-xl text-[#818cf8] hover:bg-[#818cf8]/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all text-sm font-medium">
                {thinking ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
                {thinking ? '推演中...' : '开始推演'}
              </button>
              <button onClick={() => { reset(); setImages([]); setInput('') }}
                disabled={!output && !error}
                className="flex items-center gap-2 px-4 py-3 border border-wall-border rounded-xl text-wall-muted hover:text-wall-text hover:border-[#818cf8]/30 disabled:opacity-20 disabled:cursor-not-allowed transition-all text-sm">
                <Trash2 size={14} /> 重置
              </button>
            </div>
            <p className="text-center text-wall-dim text-xs">
              <CornerDownLeft size={10} className="inline mr-1" /> Enter 发送 · 推演完成自动跳转详情页
            </p>
          </div>
        </div>

        {/* Right: Output */}
        <div className="flex-1 flex flex-col bg-wall-surface/30 min-h-[400px]">
          <div className="flex items-center justify-between px-6 py-3 border-b border-wall-border">
            <span className="text-wall-muted text-xs font-mono tracking-wider">
              {thinking ? loadingText : output ? `📜 推演结果 · ${stats ? `${stats.length}字` : ''}` : '等待提交...'}
            </span>
            {thinking && <span className="flex items-center gap-2 text-[#818cf8]/60 text-xs"><span className="w-2 h-2 rounded-full bg-[#818cf8] animate-ping" /> 流式推演中</span>}
          </div>
          <MarkdownOutput
            output={output} thinking={thinking} error={error} loadingText={loadingText}
            emptyText="输入你的决策，开始五刀推演..."
          />
          <TopologyViewer nodes={topoNodes} edges={topoEdges} ready={topoReady}
            onDrillDown={(label, desc) => {
              setInput(`深入分析：${label} — ${desc}`)
              window.scrollTo(0, 0)
            }} />
        </div>
      </div>
    </div>
  )
}
