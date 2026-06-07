'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Loader2, ArrowLeft, Clock, Eye, Heart, Share2, Send, Star, FileDown } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { TopologyViewer } from '@/components/TopologyViewer'
import { buildTopoNodes, buildTopoEdges } from '@/components/GlowNode'
import { layoutTopology } from '@/hooks/useWallbreaker'
import { Node, Edge } from 'reactflow'

export default function EventDetailPage() {
  const params = useParams()
  const router = useRouter()
  const eventId = params.id as string
  const [event, setEvent] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [topoNodes, setTopoNodes] = useState<Node[]>([])
  const [topoEdges, setTopoEdges] = useState<Edge[]>([])
  const [topoReady, setTopoReady] = useState(false)
  const [outcomeText, setOutcomeText] = useState('')
  const [accuracyScore, setAccuracyScore] = useState(3)
  const [submittingOutcome, setSubmittingOutcome] = useState(false)
  const [outcomeMsg, setOutcomeMsg] = useState('')

  const handlePrint = () => {
    window.print()
  }

  const submitOutcome = async () => {
    if (!outcomeText.trim()) return
    setSubmittingOutcome(true)
    const formData = new FormData()
    formData.append('outcome_text', outcomeText.trim())
    formData.append('accuracy_score', String(accuracyScore))
    const resp = await fetch(`/api/public/events/${eventId}/outcome`, { method: 'POST', body: formData })
    if (resp.ok) {
      setOutcomeMsg('✅ 现实反馈已提交，感谢你的贡献！')
      setOutcomeText('')
      setAccuracyScore(3)
      // 刷新事件数据
      const r = await fetch(`/api/public/events/${eventId}`)
      if (r.ok) setEvent(await r.json())
    } else {
      setOutcomeMsg('❌ 提交失败，请重试')
    }
    setSubmittingOutcome(false)
  }

  useEffect(() => {
    if (!eventId) return
    setLoading(true)
    fetch(`/api/public/events/${eventId}`)
      .then(res => res.ok ? res.json() : Promise.reject('not found'))
      .then(data => {
        setEvent(data)
        if (data.topology?.nodes && data.topology?.edges) {
          const rn = buildTopoNodes(data.topology.nodes)
          const re = buildTopoEdges(data.topology.edges)
          const { nodes, edges } = layoutTopology(rn, re)
          setTopoNodes(nodes); setTopoEdges(edges); setTopoReady(true)
        }
      })
      .catch(() => setError('事件不存在或已删除'))
      .finally(() => setLoading(false))
  }, [eventId])

  const timeStr = event?.created_at
    ? new Date(event.created_at).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : ''

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen">
      <Loader2 size={32} className="animate-spin text-wall-muted" />
    </div>
  )

  if (error) return (
    <div className="flex flex-col items-center justify-center min-h-screen space-y-4">
      <p className="text-wall-muted text-lg">{error}</p>
      <Link href="/" className="text-[#818cf8] text-sm hover:underline">← 返回决策广场</Link>
    </div>
  )

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="border-b border-wall-border/50 bg-wall-surface/30">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center gap-4 mb-3 justify-between">
            <Link href="/" className="flex items-center gap-1 text-wall-muted hover:text-wall-text text-xs transition-colors">
              <ArrowLeft size={14} /> 决策广场
            </Link>
            <button onClick={handlePrint}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-wall-border text-wall-muted hover:text-wall-text hover:border-[#818cf8]/30 transition-all text-xs no-print">
              <FileDown size={14} />
              <span className="hidden sm:inline">导出 PDF</span>
            </button>
          </div>
          <h1 className="text-xl font-bold text-wall-text mb-2">{event.title}</h1>
          <div className="flex items-center gap-3 text-wall-dim text-xs flex-wrap">
            <span className="flex items-center gap-1"><Clock size={12} />{timeStr}</span>
            <span className="flex items-center gap-1"><Eye size={12} />{event.view_count}</span>
            <span className="flex items-center gap-1"><Heart size={12} />{event.like_count}</span>
            <span className="px-2 py-0.5 rounded-md bg-[#818cf8]/10 text-[#818cf8] border border-[#818cf8]/20 font-mono text-[10px]">
              {event.mode === 'v5' ? 'V5.0' : event.mode === 'dual' ? '双路' : 'V4.0'}
            </span>
            {event.stats?.length > 0 && <span>{event.stats.length} 字</span>}
          </div>
          <blockquote className="mt-3 p-3 rounded-lg bg-wall-surface border-l-2 border-[#818cf8]/40 text-wall-muted text-sm italic">
            {event.query}
          </blockquote>
        </div>
      </div>

      {/* Result + Topology */}
      <div className="max-w-6xl mx-auto flex flex-col lg:flex-row min-h-[40vh]">
        <div className="flex-1 p-6 markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{event.result || ''}</ReactMarkdown>
        </div>
        {topoReady && (
          <div className="lg:w-[500px] h-[400px] lg:h-auto border-l border-wall-border/50">
            <TopologyViewer nodes={topoNodes} edges={topoEdges} ready={topoReady}
              onDrillDown={(label) => router.push(`/submit?q=${encodeURIComponent(`深入分析：${label}`)}`)} />
          </div>
        )}
      </div>

      {/* 现实结果反馈 */}
      <div className="max-w-6xl mx-auto px-6 pb-12">
        <div className="border-t border-wall-border/50 pt-8">
          <h2 className="text-lg font-semibold text-wall-text mb-2">🌍 现实结果验证</h2>
          <p className="text-wall-muted text-xs mb-6">
            这个决策在现实中后来怎样了？分享真实结果，帮助其他人看到 AI 推演和现实的差距。
          </p>

          {/* 已有反馈 */}
          {event.outcomes?.length > 0 && (
            <div className="space-y-3 mb-6">
              {event.outcomes.map((o: any) => (
                <div key={o.id} className="p-4 rounded-xl bg-green-500/5 border border-green-500/20">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-mono text-wall-dim">{new Date(o.created_at).toLocaleString('zh-CN')}</span>
                    <div className="flex items-center gap-0.5">
                      {[1,2,3,4,5].map(s => (
                        <Star key={s} size={12} className={s <= o.accuracy_score ? 'text-amber-400 fill-amber-400' : 'text-wall-dim'} />
                      ))}
                    </div>
                    <span className="text-[10px] text-wall-dim">AI准确度 {o.accuracy_score}/5</span>
                  </div>
                  <p className="text-wall-text text-sm leading-relaxed">{o.outcome_text}</p>
                </div>
              ))}
            </div>
          )}

          {/* 提交反馈 */}
          {outcomeMsg && <p className="text-xs text-wall-muted mb-3">{outcomeMsg}</p>}
          <div className="space-y-3">
            <textarea
              value={outcomeText}
              onChange={(e) => setOutcomeText(e.target.value)}
              placeholder="写下这个决策在现实中真实发生了什么..."
              className="w-full h-24 bg-wall-surface border border-wall-border rounded-xl p-4 text-wall-text placeholder-wall-muted/40 resize-none focus:outline-none focus:border-[#818cf8]/50 text-sm"
            />
            <div className="flex items-center gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-wall-dim text-xs">AI推演准确度：</span>
                {[1,2,3,4,5].map(s => (
                  <button key={s} onClick={() => setAccuracyScore(s)}
                    className={`transition-all ${s <= accuracyScore ? 'text-amber-400' : 'text-wall-dim hover:text-amber-400/50'}`}>
                    <Star size={16} className={s <= accuracyScore ? 'fill-amber-400' : ''} />
                  </button>
                ))}
              </div>
              <button onClick={submitOutcome} disabled={!outcomeText.trim() || submittingOutcome}
                className="flex items-center gap-2 px-4 py-2 bg-green-500/10 border border-green-500/30 rounded-xl text-green-400 hover:bg-green-500/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all text-sm">
                {submittingOutcome ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                提交现实反馈
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
