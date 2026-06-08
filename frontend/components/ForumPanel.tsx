'use client'

import { Loader2, MessageCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'

interface AgentMessage {
  agent: string
  name: string
  emoji: string
  status: 'pending' | 'running' | 'done' | 'error'
  text: string
  elapsed_ms?: number
}

const AGENT_ORDER = ['crisis', 'psychology', 'interest', 'class', 'game', 'soul', 'devil', 'judge']

export function ForumPanel({ agents, phase }: { agents: Record<string, AgentMessage>; phase: string }) {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)

  const activeAgents = Object.entries(agents).filter(([_, a]) => a.status !== 'pending')
  if (activeAgents.length === 0) return null

  return (
    <div className="border-b border-wall-border/30 bg-purple-500/[0.02] overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2">
        <MessageCircle size={14} className="text-purple-400" />
        <span className="text-wall-dim text-[10px] font-mono tracking-wider">
          {phase || '🔪 多Agent对抗推演论坛'}
        </span>
        <span className="flex-1 h-px bg-gradient-to-r from-purple-500/30 to-transparent" />
        <span className="flex items-center gap-1 text-purple-400/60 text-[9px]">
          <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
          实时对话
        </span>
      </div>

      {/* Agent Thread */}
      <div className="px-3 pb-3 space-y-1.5 max-h-[400px] overflow-y-auto">
        {AGENT_ORDER.map(key => {
          const agent = agents[key]
          if (!agent || agent.status === 'pending') return null

          const isExpanded = expandedAgent === key
          const isRunning = agent.status === 'running'
          const isDone = agent.status === 'done'
          const isError = agent.status === 'error'

          const borderColor = isDone ? 'border-green-500/30' : isRunning ? 'border-yellow-500/30' : 'border-red-500/30'
          const bgColor = isDone ? 'bg-green-500/5' : isRunning ? 'bg-yellow-500/5' : 'bg-red-500/5'
          const statusIcon = isDone ? '✅' : isRunning ? '🔄' : '❌'

          return (
            <div key={key} className={`rounded-lg border ${borderColor} ${bgColor} overflow-hidden transition-all`}>
              <button
                onClick={() => setExpandedAgent(isExpanded ? null : key)}
                className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/[0.02] transition-colors"
              >
                <span className="text-sm">{agent.emoji}</span>
                <span className={`text-xs font-medium flex-1 ${isDone ? 'text-green-300' : isRunning ? 'text-yellow-300' : 'text-red-300'}`}>
                  {agent.name}
                </span>
                {isRunning && <Loader2 size={12} className="animate-spin text-yellow-400" />}
                <span className="text-[10px] text-wall-dim">{statusIcon}</span>
                {isExpanded ? <ChevronUp size={12} className="text-wall-dim" /> : <ChevronDown size={12} className="text-wall-dim" />}
              </button>

              {/* Expanded Content */}
              {isExpanded && agent.text && (
                <div className="px-3 pb-3 pt-0 border-t border-white/[0.05]">
                  <div className="text-wall-text text-xs leading-relaxed whitespace-pre-wrap max-h-[300px] overflow-y-auto p-2 rounded bg-black/20">
                    {agent.text}
                  </div>
                  {agent.elapsed_ms && (
                    <div className="text-wall-dim text-[9px] mt-1">
                      {agent.name} 耗时 {(agent.elapsed_ms / 1000).toFixed(1)}s
                    </div>
                  )}
                </div>
              )}

              {isExpanded && isRunning && (
                <div className="px-3 pb-3 flex items-center gap-2">
                  <div className="flex gap-1">
                    <div className="w-1 h-1 rounded-full bg-yellow-400 animate-pulse" style={{ animationDelay: '0s' }} />
                    <div className="w-1 h-1 rounded-full bg-yellow-400 animate-pulse" style={{ animationDelay: '0.2s' }} />
                    <div className="w-1 h-1 rounded-full bg-yellow-400 animate-pulse" style={{ animationDelay: '0.4s' }} />
                  </div>
                  <span className="text-wall-dim text-[10px]">思考中...</span>
                </div>
              )}

              {isExpanded && isError && (
                <div className="px-3 pb-2 text-red-400/70 text-[10px]">
                  {agent.text || '该Agent运行异常'}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
