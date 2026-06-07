'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { Brain, Plus, Loader2, Search, Clock, Flame } from 'lucide-react'
import { EventCard } from '@/components/EventCard'

export default function Home() {
  const [events, setEvents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState('recent')

  const fetchEvents = useCallback(async (p: number, s: string) => {
    setLoading(true)
    try {
      const resp = await fetch(`/api/public/events?page=${p}&size=12&sort=${s}`)
      if (resp.ok) {
        const data = await resp.json()
        setEvents(data.events || [])
        setTotal(data.total || 0)
      }
    } catch { /* ignore */ }
    setLoading(false)
  }, [])

  useEffect(() => { fetchEvents(page, sort) }, [page, sort, fetchEvents])

  const totalPages = Math.ceil(total / 12)

  return (
    <div className="min-h-screen">
      {/* Hero */}
      <div className="relative overflow-hidden py-16 px-6 text-center border-b border-wall-border/50">
        <div className="absolute inset-0 bg-gradient-to-b from-[#818cf8]/5 to-transparent" />
        <div className="relative z-10 max-w-2xl mx-auto">
          <h1 className="text-4xl font-bold mb-3">
            <span className="text-[#818cf8]">认知破壁机</span>
          </h1>
          <p className="text-wall-muted text-sm mb-6 font-mono tracking-wider uppercase">Cognitive Wallbreaker V6.0</p>
          <p className="text-wall-dim text-sm mb-8">
            AI 多智能体对抗推演引擎 · 公开个人决策平台<br />
            提交你的决策，七 Agent 公开推演，所有人可浏览学习
          </p>
          <Link href="/submit"
            className="inline-flex items-center gap-2 px-8 py-3 bg-[#818cf8]/10 border border-[#818cf8]/30 rounded-xl text-[#818cf8] hover:bg-[#818cf8]/20 transition-all text-sm font-medium">
            <Plus size={18} />
            提交决策推演
          </Link>
        </div>
      </div>

      {/* Toolbar */}
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2 text-wall-muted text-xs">
          <Brain size={14} className="text-[#818cf8]" />
          <span className="font-mono">决策广场</span>
          <span className="text-wall-dim">· {total} 个推演案例</span>
        </div>
        <div className="flex items-center gap-1.5 border border-wall-border rounded-lg p-0.5">
          <button onClick={() => { setSort('recent'); setPage(1) }}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-xs transition-all ${sort === 'recent' ? 'bg-[#818cf8]/20 text-[#818cf8]' : 'text-wall-muted hover:text-wall-text'}`}>
            <Clock size={12} /> 最新
          </button>
          <button onClick={() => { setSort('hot'); setPage(1) }}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-xs transition-all ${sort === 'hot' ? 'bg-[#818cf8]/20 text-[#818cf8]' : 'text-wall-muted hover:text-wall-text'}`}>
            <Flame size={12} /> 最热
          </button>
        </div>
      </div>

      {/* Event Grid */}
      <div className="max-w-6xl mx-auto px-6 pb-16">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 size={24} className="animate-spin text-wall-muted" />
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-20 space-y-3">
            <Brain size={40} className="mx-auto text-wall-dim" />
            <p className="text-wall-muted text-sm">还没有推演案例</p>
            <Link href="/submit" className="text-[#818cf8] text-xs hover:underline">
              成为第一个提交决策的人 →
            </Link>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {events.map((event) => <EventCard key={event.id} {...event} />)}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-8">
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                  <button key={p} onClick={() => setPage(p)}
                    className={`w-8 h-8 rounded-lg text-xs transition-all ${p === page ? 'bg-[#818cf8]/20 text-[#818cf8] border border-[#818cf8]/30' : 'text-wall-muted border border-wall-border hover:border-[#818cf8]/30'}`}>
                    {p}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
