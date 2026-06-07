'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Loader2, ArrowLeft, Clock, Eye, Heart, Share2 } from 'lucide-react'
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
          <div className="flex items-center gap-4 mb-3">
            <Link href="/" className="flex items-center gap-1 text-wall-muted hover:text-wall-text text-xs transition-colors">
              <ArrowLeft size={14} /> 决策广场
            </Link>
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
      <div className="max-w-6xl mx-auto flex flex-col lg:flex-row min-h-[60vh]">
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
    </div>
  )
}
