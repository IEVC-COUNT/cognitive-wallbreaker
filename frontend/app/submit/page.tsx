'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Loader2, CornerDownLeft, Zap, Trash2, Users } from 'lucide-react'
import { ImageUploader } from '@/components/ImageUploader'
import { MarkdownOutput } from '@/components/MarkdownOutput'
import { TopologyViewer } from '@/components/TopologyViewer'
import { ForumPanel } from '@/components/ForumPanel'
import { buildTopoNodes, buildTopoEdges } from '@/components/GlowNode'
import { layoutTopology, useWallbreaker } from '@/hooks/useWallbreaker'

const MODES = [
  { key: 'v4' as const, label: 'V4.0 五刀', desc: '快速推演', icon: '🔪' },
  { key: 'v5' as const, label: 'V5.0 论坛', desc: '7Agent辩论', icon: '😈' },
]

export default function SubmitPage() {
  const [input, setInput] = useState('')
  const [images, setImages] = useState<File[]>([])
  const [mode, setMode] = useState<'v4' | 'v5'>('v4')

  useEffect(() => {
    // 原生 URL 读取，避免 Next.js Suspense 依赖
    const q = new URLSearchParams(window.location.search).get('q')
    if (q) setInput(decodeURIComponent(q))
  }, [])
  const { output, thinking, error, stats, topoNodes, topoEdges, topoReady,
    setTopoNodes, setTopoEdges, setTopoReady, reset } = useWallbreaker()
  const [loadingText, setLoadingText] = useState('')
  const [v5Agents, setV5Agents] = useState<Record<string, any>>({})
  const abortRef = useRef<AbortController | null>(null)
  const router = useRouter()

  const getAnonymousId = () => {
    let id = localStorage.getItem('wallbreaker_uid')
    if (!id) { id = 'anon_' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36); localStorage.setItem('wallbreaker_uid', id) }
    return id
  }

  const handleSubmit = useCallback(async () => {
    if (!input.trim()) return
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    reset()
    setLoadingText('🔍 搜索背景信息...')
    setV5Agents({})

    const formData = new FormData()
    formData.append('event', input.trim())
    formData.append('mode', mode)
    formData.append('anonymous_id', getAnonymousId())
    images.forEach(f => formData.append('images', f))

    let mergedOutput = ''

    try {
      const resp = await fetch('/api/public/submit', { method: 'POST', body: formData, signal: controller.signal })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const reader = resp.body?.getReader()
      if (!reader) throw new Error('No response')
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const msg = JSON.parse(line.slice(6))
            switch (msg.type) {
              case 'phase':
                setLoadingText(msg.text || '')
                break
              case 'thinking':
                setLoadingText(msg.text || '')
                break
              case 'agent_done':
                setV5Agents((prev: any) => ({
                  ...prev,
                  [msg.agent]: { name: msg.name, emoji: msg.emoji, status: 'done', text: msg.text || '', elapsed_ms: msg.elapsed_ms }
                }))
                mergedOutput += `\n\n## ${msg.emoji} ${msg.name}\n${msg.text || ''}\n`
                break
              case 'content':
                mergedOutput += (msg.text || '')
                break
              case 'topology':
                if (msg.data?.nodes && msg.data?.edges) {
                  const { nodes, edges } = layoutTopology(buildTopoNodes(msg.data.nodes), buildTopoEdges(msg.data.edges))
                  setTopoNodes(nodes); setTopoEdges(edges); setTopoReady(true)
                }
                break
              case 'done':
                setTopoNodes([]); setTopoEdges([]); setTopoReady(false)
                if (mergedOutput) {
                  // 全量设置输出
                  setTopoNodes(topoNodes); setTopoEdges(topoEdges)
                }
                if (msg.event_id) setTimeout(() => router.push(`/event/${msg.event_id}`), 600)
                break
              case 'error':
                setLoadingText('')
                break
            }
          } catch { /* skip */ }
        }
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== 'AbortError') setLoadingText('')
    }
  }, [input, images, mode, reset, router])

  return (
    <div className="min-h-screen flex flex-col">
      <div className="flex-1 flex flex-col lg:flex-row">
        {/* Left: Input */}
        <div className="flex-1 flex flex-col items-center justify-center p-6 lg:p-12 border-r border-wall-border/50">
          <div className="w-full max-w-xl space-y-6">
            <div className="text-center space-y-2 mb-2">
              <h1 className="text-2xl font-bold"><span className="text-[#818cf8]">提交决策</span></h1>
              <p className="text-wall-muted text-xs font-mono">提交个人决策，多Agent公开推演，所有人可浏览</p>
            </div>

            {/* Mode Selector */}
            <div className="flex items-center justify-center gap-2">
              {MODES.map(m => (
                <button key={m.key} onClick={() => setMode(m.key)} disabled={!!loadingText}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl border text-sm transition-all ${
                    mode === m.key
                      ? 'border-purple-500/50 bg-purple-500/10 text-purple-400 shadow-[0_0_12px_rgba(168,85,247,0.15)]'
                      : 'border-wall-border text-wall-muted hover:text-wall-text hover:border-wall-accent/30'
                  } disabled:opacity-50`}>
                  <span>{m.icon}</span>
                  <span className="text-xs font-medium">{m.label}</span>
                  <span className="text-[10px] text-wall-dim hidden sm:inline">{m.desc}</span>
                </button>
              ))}
            </div>

            <div className="relative">
              <div className="absolute -inset-1 bg-[#818cf8]/5 rounded-2xl blur-xl" />
              <textarea value={input} onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit() } }}
                placeholder="告诉我你正在纠结的个人决策..." disabled={!!loadingText}
                className="relative w-full h-32 bg-wall-surface border border-wall-border rounded-xl p-5 text-wall-text placeholder-wall-muted/40 resize-none focus:outline-none focus:border-[#818cf8]/50 transition-colors disabled:opacity-50 text-sm leading-relaxed"
              />
            </div>
            <ImageUploader images={images} onAdd={(f) => setImages(p => [...p, ...f].slice(0, 5))}
              onRemove={(i) => setImages(p => p.filter((_, j) => j !== i))} disabled={!!loadingText} />
            <div className="flex gap-3 justify-center">
              <button onClick={handleSubmit}
                disabled={!input.trim() || !!loadingText}
                className="flex items-center gap-2 px-6 py-3 bg-[#818cf8]/10 border border-[#818cf8]/30 rounded-xl text-[#818cf8] hover:bg-[#818cf8]/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all text-sm font-medium">
                {loadingText ? <Loader2 size={16} className="animate-spin" /> : mode === 'v5' ? <Users size={16} /> : <Zap size={16} />}
                {loadingText ? '推演中...' : mode === 'v5' ? 'V5.0 论坛推演' : '开始推演'}
              </button>
              <button onClick={() => { reset(); setImages([]); setInput(''); setV5Agents({}); }}
                disabled={!output && !error}
                className="flex items-center gap-2 px-4 py-3 border border-wall-border rounded-xl text-wall-muted hover:text-wall-text hover:border-[#818cf8]/30 disabled:opacity-20 disabled:cursor-not-allowed transition-all text-sm">
                <Trash2 size={14} /> 重置
              </button>
            </div>
            <p className="text-center text-wall-dim text-xs">
              <CornerDownLeft size={10} className="inline mr-1" /> Enter 发送 · 推演完成自动跳转详情页
              {mode === 'v5' && <span className="ml-2 text-purple-400/60">· 7Agent 论坛辩论</span>}
            </p>
          </div>
        </div>

        {/* Right: Output */}
        <div className="flex-1 flex flex-col bg-wall-surface/30 min-h-[400px]">
          {mode === 'v5' && !!loadingText && (
            <ForumPanel agents={v5Agents} phase={loadingText} />
          )}

          <div className="flex items-center justify-between px-6 py-3 border-b border-wall-border">
            <span className="text-wall-muted text-xs font-mono tracking-wider">
              {loadingText ? loadingText : output ? `📜 推演结果 · ${stats ? `${stats.length}字` : ''}` : '等待提交...'}
            </span>
            {!!loadingText && <span className="flex items-center gap-2 text-[#818cf8]/60 text-xs"><span className="w-2 h-2 rounded-full bg-[#818cf8] animate-ping" /> 推演中</span>}
          </div>
          <MarkdownOutput
            output={output} thinking={!!loadingText} error={error} loadingText={loadingText}
            emptyText={mode === 'v5' ? '输入决策，七Agent论坛辩论...' : '输入你的决策，开始五刀推演...'}
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
