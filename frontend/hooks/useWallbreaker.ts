'use client'

import { useState, useRef, useCallback } from 'react'
import { Node, Edge, useNodesState, useEdgesState, MarkerType } from 'reactflow'
import dagre from 'dagre'

/* ══════════════════════════════════════════════════════════════
   自动布局 (dagre 树状)
   ══════════════════════════════════════════════════════════════ */
export const NODE_WIDTH = 180
export const NODE_HEIGHT = 60

export function layoutTopology(nodes: Node[], edges: Edge[]): { nodes: Node[]; edges: Edge[] } {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 80, ranksep: 120 })
  nodes.forEach((node) => dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT }))
  edges.forEach((edge) => dagreGraph.setEdge(edge.source, edge.target))
  dagre.layout(dagreGraph)
  const layoutedNodes = nodes.map((node) => {
    const pos = dagreGraph.node(node.id)
    return {
      ...node,
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 },
      sourcePosition: 'bottom' as const,
      targetPosition: 'top' as const,
    }
  })
  return { nodes: layoutedNodes, edges }
}

/* ══════════════════════════════════════════════════════════════
   节点类型颜色映射
   ══════════════════════════════════════════════════════════════ */
export const TYPE_STYLES: Record<string, { bg: string; glow: string; border: string; label: string }> = {
  core:       { bg: 'rgba(99,102,241,0.25)', glow: 'rgba(99,102,241,0.6)', border: '#6366f1', label: '🎯 核心' },
  risk:       { bg: 'rgba(239,68,68,0.25)', glow: 'rgba(239,68,68,0.5)', border: '#ef4444', label: '⚠️ 高危' },
  safe:       { bg: 'rgba(34,197,94,0.25)', glow: 'rgba(34,197,94,0.5)', border: '#22c55e', label: '🛡️ 安全' },
  social:     { bg: 'rgba(245,158,11,0.25)', glow: 'rgba(245,158,11,0.5)', border: '#f59e0b', label: '🏛️ 社会' },
  psychology: { bg: 'rgba(168,85,247,0.25)', glow: 'rgba(168,85,247,0.5)', border: '#a855f7', label: '🧠 心理' },
  future:     { bg: 'rgba(6,182,212,0.25)', glow: 'rgba(6,182,212,0.5)', border: '#06b6d4', label: '🔮 未来' },
}

function buildTopoNodes(rawNodes: any[]) {
  return rawNodes.map((n: any, i: number) => ({
    id: n.id, type: 'glowNode' as const,
    data: { label: n.label, description: n.description || '', nodeType: n.type || 'core' },
    position: { x: i * 200, y: i * 100 },
  }))
}

function buildTopoEdges(rawEdges: any[]) {
  return rawEdges.map((e: any, i: number) => ({
    id: `${e.source}-${e.target}-${i}`,
    source: e.source, target: e.target,
    label: e.label || '',
    markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b' },
    style: { stroke: '#334155', strokeWidth: 1.5 },
    labelStyle: { fill: '#64748b', fontSize: 10 },
  }))
}

/* ══════════════════════════════════════════════════════════════
   主 Hook
   ══════════════════════════════════════════════════════════════ */
export function useWallbreaker() {
  const [output, setOutput] = useState('')
  const [thinking, setThinking] = useState(false)
  const [error, setError] = useState('')
  const [loadingText, setLoadingText] = useState('')
  const [stats, setStats] = useState<{ length: number; elapsed_ms: number } | null>(null)
  const [topoNodes, setTopoNodes] = useNodesState([])
  const [topoEdges, setTopoEdges] = useEdgesState([])
  const [topoReady, setTopoReady] = useState(false)
  const [eventId, setEventId] = useState('')
  const abortRef = useRef<AbortController | null>(null)

  // ── V5.0 多智能体状态 ──
  const [v5Mode, setV5Mode] = useState(false)
  const [v5Agents, setV5Agents] = useState<Record<string, any>>({})
  const [v5Phase, setV5Phase] = useState('')

  const loadingMessages = [
    '🔍 检索历史决策记忆...',
    '🧠 激活认知破壁引擎...',
    '🔪 解剖心理防御与认知盲区...',
    '💰 追踪利益链条与收割逻辑...',
    '📊 计算阶层筹码与容错率...',
    '🎭 生成拓扑沙盘推演...',
  ]

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setOutput('')
    setThinking(false)
    setError('')
    setLoadingText('')
    setStats(null)
    setTopoNodes([])
    setTopoEdges([])
    setTopoReady(false)
    setEventId('')
    setV5Agents({})
    setV5Phase('')
  }, [])

  const simulate = useCallback(async (event: string, images: File[], endpoint: string = '/api/simulate', onEventId?: (id: string) => void) => {
    if (!event.trim() && images.length === 0) return
    reset()

    const controller = new AbortController()
    abortRef.current = controller
    setThinking(true)
    setOutput('')

    let msgIdx = 0
    setLoadingText(loadingMessages[0])
    const msgTimer = setInterval(() => {
      msgIdx = (msgIdx + 1) % loadingMessages.length
      setLoadingText(loadingMessages[msgIdx])
    }, 2500)

    try {
      const formData = new FormData()
      formData.append('event', event.trim())
      formData.append('user_id', 'default')
      images.forEach((file) => formData.append('images', file))

      const resp = await fetch(endpoint, { method: 'POST', body: formData, signal: controller.signal })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const reader = resp.body?.getReader()
      if (!reader) throw new Error('No response body')
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
              case 'thinking':
                setLoadingText(msg.text || loadingMessages[0])
                break
              case 'content_start':
                clearInterval(msgTimer); setThinking(false)
                break
              case 'content':
                setOutput((prev) => prev + (msg.text || ''))
                break
              case 'topology':
                if (msg.data?.nodes && msg.data?.edges) {
                  const { nodes, edges } = layoutTopology(buildTopoNodes(msg.data.nodes), buildTopoEdges(msg.data.edges))
                  setTopoNodes(nodes); setTopoEdges(edges); setTopoReady(true)
                }
                break
              case 'done':
                setStats({ length: msg.length || 0, elapsed_ms: msg.elapsed_ms || 0 })
                if (msg.event_id && onEventId) onEventId(msg.event_id)
                break
              case 'error':
                setError(msg.text || '未知错误')
                break
            }
          } catch { /* skip */ }
        }
      }
      clearInterval(msgTimer)
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== 'AbortError') setError(e.message)
      clearInterval(msgTimer)
    } finally {
      setThinking(false)
    }
  }, [reset])

  return {
    output, thinking, error, loadingText, stats,
    topoNodes, topoEdges, topoReady, setTopoNodes, setTopoEdges, setOutput, setTopoReady,
    simulate, reset, eventId,
    v5Mode, setV5Mode, v5Agents, v5Phase,
  }
}
