'use client'

import { Clock, Eye, Heart } from 'lucide-react'
import Link from 'next/link'

interface EventCardProps {
  id: string
  title: string
  query_preview: string
  mode: string
  stats: { length?: number; elapsed_ms?: number; agents_count?: number }
  has_topology: boolean
  created_at: string
  view_count: number
  like_count: number
}

const MODE_LABELS: Record<string, string> = {
  v4: 'V4.0',
  v5: 'V5.0',
  dual: '双路',
}

export function EventCard({ id, title, query_preview, mode, stats, has_topology, created_at, view_count, like_count }: EventCardProps) {
  const timeAgo = (() => {
    const diff = Date.now() - new Date(created_at).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 60) return `${mins}分钟前`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}小时前`
    return `${Math.floor(hours / 24)}天前`
  })()

  return (
    <Link href={`/event/${id}`} className="block group">
      <div className="bg-wall-surface/50 border border-wall-border/50 rounded-2xl p-5 hover:border-[#818cf8]/30 hover:bg-wall-surface/80 transition-all duration-300 h-full flex flex-col">
        <h3 className="text-wall-text font-semibold text-base mb-2 line-clamp-2 group-hover:text-[#818cf8] transition-colors">
          {title}
        </h3>
        <p className="text-wall-muted text-xs leading-relaxed line-clamp-3 mb-3 flex-1">
          {query_preview}
        </p>
        <div className="flex items-center gap-2 flex-wrap mb-3">
          <span className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-[#818cf8]/10 text-[#818cf8] border border-[#818cf8]/20">
            {MODE_LABELS[mode] || mode}
          </span>
          {stats.length && <span className="text-wall-dim text-[10px]">{stats.length}字</span>}
          {has_topology && <span className="text-wall-dim text-[10px]">📊 拓扑</span>}
        </div>
        <div className="flex items-center gap-3 text-wall-dim text-[10px]">
          <span className="flex items-center gap-1"><Clock size={10} />{timeAgo}</span>
          <span className="flex items-center gap-1"><Eye size={10} />{view_count}</span>
          <span className="flex items-center gap-1"><Heart size={10} />{like_count}</span>
        </div>
      </div>
    </Link>
  )
}
