'use client'

import { useState, useRef, useEffect, useCallback, DragEvent, ChangeEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  Handle,
} from 'reactflow'
import 'reactflow/dist/style.css'
import dagre from 'dagre'
import {
  Brain, Loader2, CornerDownLeft, AlertCircle, X, Upload, Zap, Trash2, ChevronRight, Target, RotateCcw, Share2,
  History, Clock, FileText, ChevronLeft,
} from 'lucide-react'

/* ══════════════════════════════════════════════════════════════
   React Flow 自动布局 (dagre 树状)
   ══════════════════════════════════════════════════════════════ */
const NODE_WIDTH = 180
const NODE_HEIGHT = 60

function layoutTopology(nodes: Node[], edges: Edge[]): { nodes: Node[]; edges: Edge[] } {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 80, ranksep: 120 })

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  })

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  dagre.layout(dagreGraph)

  const layoutedNodes = nodes.map((node) => {
    const pos = dagreGraph.node(node.id)
    return {
      ...node,
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
    }
  })

  return { nodes: layoutedNodes, edges }
}

/* ══════════════════════════════════════════════════════════════
   节点类型颜色映射
   ══════════════════════════════════════════════════════════════ */
const TYPE_STYLES: Record<string, { bg: string; glow: string; border: string; label: string }> = {
  core:       { bg: 'rgba(99,102,241,0.25)', glow: 'rgba(99,102,241,0.6)', border: '#6366f1', label: '🎯 核心' },
  risk:       { bg: 'rgba(239,68,68,0.25)', glow: 'rgba(239,68,68,0.5)', border: '#ef4444', label: '⚠️ 高危' },
  safe:       { bg: 'rgba(34,197,94,0.25)', glow: 'rgba(34,197,94,0.5)', border: '#22c55e', label: '🛡️ 安全' },
  social:     { bg: 'rgba(245,158,11,0.25)', glow: 'rgba(245,158,11,0.5)', border: '#f59e0b', label: '🏛️ 社会' },
  psychology: { bg: 'rgba(168,85,247,0.25)', glow: 'rgba(168,85,247,0.5)', border: '#a855f7', label: '🧠 心理' },
  future:     { bg: 'rgba(6,182,212,0.25)', glow: 'rgba(6,182,212,0.5)', border: '#06b6d4', label: '🔮 未来' },
}

/* ══════════════════════════════════════════════════════════════
   自定义发光节点
   ══════════════════════════════════════════════════════════════ */
function GlowNode({ data, selected }: { data: any; selected: boolean }) {
  const style = TYPE_STYLES[data.nodeType] || TYPE_STYLES.core

  return (
    <div
      className="relative px-4 py-3 rounded-2xl cursor-pointer transition-all duration-300"
      style={{
        background: `radial-gradient(ellipse at center, ${style.bg} 0%, rgba(15,22,36,0.9) 100%)`,
        border: `1.5px solid ${selected ? style.glow : style.border}`,
        boxShadow: selected
          ? `0 0 25px ${style.glow}, 0 0 50px ${style.glow}40, inset 0 0 15px ${style.glow}20`
          : `0 0 8px ${style.glow}20`,
        width: NODE_WIDTH,
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: style.border }} />
      <div className="text-xs font-semibold truncate" style={{ color: style.border }}>
        {data.label}
      </div>
      <div className="text-[10px] text-wall-muted mt-1 truncate">{data.description}</div>
      <Handle type="source" position={Position.Bottom} style={{ background: style.border }} />
    </div>
  )
}

const nodeTypes = { glowNode: GlowNode }

/* ══════════════════════════════════════════════════════════════
   SSE Hook
   ══════════════════════════════════════════════════════════════ */
function useWallbreaker() {
  const [output, setOutput] = useState('')
  const [thinking, setThinking] = useState(false)
  const [error, setError] = useState('')
  const [loadingText, setLoadingText] = useState('')
  const [stats, setStats] = useState<{ length: number; elapsed_ms: number } | null>(null)
  const [topoNodes, setTopoNodes] = useNodesState([])
  const [topoEdges, setTopoEdges] = useEdgesState([])
  const [topoReady, setTopoReady] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  // ── 双路推演状态 ──
  const [dual, setDual] = useState({
    running: false, outputA: '', outputB: '',
    labels: { a: '路径 A', b: '路径 B' },
    topoNodesA: [] as Node[], topoEdgesA: [] as Edge[], topoReadyA: false,
    topoNodesB: [] as Node[], topoEdgesB: [] as Edge[], topoReadyB: false,
    statsA: null as { length: number; elapsed_ms: number } | null,
    statsB: null as { length: number; elapsed_ms: number } | null,
    error: '',
  })
  const dualAbortRef = useRef<AbortController | null>(null)

  const loadingMessages = [
    '🔍 检索历史决策记忆...',
    '🧠 激活认知破壁引擎 V4.0...',
    '🔪 解剖心理防御与认知盲区...',
    '💰 追踪利益链条与收割逻辑...',
    '📊 计算阶层筹码与容错率...',
    '🎭 生成拓扑沙盘推演...',
  ]

  // ── V5.0 多智能体状态 ──
  const [v5Mode, setV5Mode] = useState(false)
  const [v5Agents, setV5Agents] = useState<Record<string, { name: string; emoji: string; status: 'pending' | 'running' | 'done' | 'error'; text: string; elapsed_ms?: number }>>({})
  const [v5Phase, setV5Phase] = useState('')
  const [v5Topology, setV5Topology] = useState<any>(null)

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
    setV5Agents({})
    setV5Phase('')
    setV5Topology(null)
  }, [])

  const simulate = useCallback(async (event: string, images: File[], drillDownNode?: string, onSaved?: (id: string) => void) => {
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
      if (drillDownNode) {
        formData.append('user_id', 'default')
      }
      images.forEach((file) => formData.append('images', file))

      const resp = await fetch('/api/simulate', {
        method: 'POST', body: formData, signal: controller.signal,
      })
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
          if (line.startsWith('data: ')) {
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
                  // 收到拓扑沙盘数据 → 渲染到 ReactFlow
                  if (msg.data && msg.data.nodes && msg.data.edges) {
                    const rawNodes = msg.data.nodes.map((n: any, i: number) => ({
                      id: n.id, type: 'glowNode',
                      data: { label: n.label, description: n.description || '', nodeType: n.type || 'core' },
                      position: { x: i * 200, y: i * 100 }, // dagre will overwrite
                    }))
                    const rawEdges = msg.data.edges.map((e: any, i: number) => ({
                      id: `${e.source}-${e.target}-${i}`,
                      source: e.source, target: e.target,
                      label: e.label || '',
                      markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b' },
                      style: { stroke: '#334155', strokeWidth: 1.5 },
                      labelStyle: { fill: '#64748b', fontSize: 10 },
                    }))
                    const { nodes, edges } = layoutTopology(rawNodes, rawEdges)
                    setTopoNodes(nodes)
                    setTopoEdges(edges)
                    setTopoReady(true)
                  }
                  break
                case 'done':
                  setStats({ length: msg.length || 0, elapsed_ms: msg.elapsed_ms || 0 })
                  break
                case 'history_saved':
                  if (onSaved && msg.record_id) onSaved(msg.record_id)
                  break
                case 'error':
                  setError(msg.text || '未知错误')
                  break
              }
            } catch { /* skip parse errors */ }
          }
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

  // 沿分支继续推演 — 路径内延伸不替换主输出
  const [drillOutput, setDrillOutput] = useState('')
  const [drillThinking, setDrillThinking] = useState(false)
  const [drillTopoNodes, setDrillTopoNodes] = useNodesState([])
  const [drillTopoEdges, setDrillTopoEdges] = useEdgesState([])
  const [drillTopoReady, setDrillTopoReady] = useState(false)
  const drillAbortRef = useRef<AbortController | null>(null)

  const drillDown = useCallback(async (node: Node) => {
    const prompt = `基于之前的推演，我选择深入分析这个分支：「${node.data.label}」——${node.data.description}。请对此进行更深入的破壁推演。`
    drillAbortRef.current?.abort(); const c = new AbortController(); drillAbortRef.current = c
    setDrillOutput(''); setDrillThinking(true); setDrillTopoReady(false)
    const fd = new FormData(); fd.append('event', prompt); fd.append('user_id', 'default')
    try { const resp = await fetch('/api/simulate',{method:'POST',body:fd,signal:c.signal})
      if(!resp.ok) throw new Error('HTTP '+resp.status)
      const reader = resp.body?.getReader(); if(!reader) return
      const d = new TextDecoder(); let buf='',full=''
      while(true){const{ done,value }=await reader.read();if(done)break
        buf+=d.decode(value,{stream:true});const lines=buf.split('\n');buf=lines.pop()||''
        for(const l of lines){if(!l.startsWith('data: '))continue
          try{const m=JSON.parse(l.slice(6))
            if(m.type==='content'){full+=m.text||'';setDrillOutput(full)}
            else if(m.type==='topology'&&m.data?.nodes){
              const rn=m.data.nodes.map((n:any,i:number)=>({id:n.id,type:'glowNode',data:{label:n.label,description:n.description||'',nodeType:n.type||'core'},position:{x:i*200,y:i*100}}))
              const re=m.data.edges.map((e:any,i:number)=>({id:`${e.source}-${e.target}-${i}`,source:e.source,target:e.target,label:e.label||'',markerEnd:{type:MarkerType.ArrowClosed,color:'#64748b'},style:{stroke:'#334155',strokeWidth:1.5},labelStyle:{fill:'#64748b',fontSize:10}}))
              const{nodes,edges}=layoutTopology(rn,re);setDrillTopoNodes(nodes);setDrillTopoEdges(edges);setDrillTopoReady(true)
            }
          }catch{}
        }
      }
    }catch(e:any){if(e.name!=='AbortError')setDrillOutput('延伸失败: '+e.message)}
    setDrillThinking(false)
  }, [])

  // ── V5.0 多智能体推演 ──
  const simulateV5 = useCallback(async (event: string, images: File[], fastMode: boolean = false) => {
    if (!event.trim() && images.length === 0) return
    reset()
    abortRef.current = new AbortController()
    const controller = abortRef.current
    setThinking(true)
    setOutput('')

    // 初始化所有 Agent 为 pending
    const agentKeys = fastMode
      ? ['psychology', 'interest', 'judge']
      : ['psychology', 'interest', 'class', 'game', 'soul', 'devil', 'judge']
    const initial: Record<string, any> = {}
    agentKeys.forEach(k => { initial[k] = { name: k, emoji: '⚙️', status: 'pending', text: '' } })
    setV5Agents(initial)

    try {
      const formData = new FormData()
      formData.append('event', event.trim())
      formData.append('user_id', 'default')
      images.forEach((file) => formData.append('images', file))

      const endpoint = fastMode ? '/api/simulate/v5/fast' : '/api/simulate/v5'
      const resp = await fetch(endpoint, {
        method: 'POST', body: formData, signal: controller.signal,
      })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const reader = resp.body?.getReader()
      if (!reader) throw new Error('No response body')
      const decoder = new TextDecoder()
      let buffer = ''
      let mergedOutput = ''

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
                setV5Phase(msg.text || '')
                setThinking(true)
                break
              case 'agent_done':
                setV5Agents(prev => ({
                  ...prev,
                  [msg.agent]: {
                    name: msg.name,
                    emoji: msg.emoji,
                    status: 'done',
                    text: msg.text || '',
                    elapsed_ms: msg.elapsed_ms,
                  }
                }))
                // 合并到主输出
                if (msg.text) {
                  mergedOutput += `\n\n---\n## ${msg.emoji} ${msg.name}\n${msg.text}\n`
                }
                break
              case 'agent_error':
                setV5Agents(prev => ({
                  ...prev,
                  [msg.agent]: {
                    name: msg.name,
                    emoji: '⚠️',
                    status: 'error',
                    text: msg.error || '',
                  }
                }))
                break
              case 'topology':
                setV5Topology(msg.data)
                if (msg.data?.nodes && msg.data?.edges) {
                  const rawNodes = msg.data.nodes.map((n: any, i: number) => ({
                    id: n.id, type: 'glowNode',
                    data: { label: n.label, description: n.description || '', nodeType: n.type || 'core' },
                    position: { x: i * 200, y: i * 100 },
                  }))
                  const rawEdges = msg.data.edges.map((e: any, i: number) => ({
                    id: `${e.source}-${e.target}-${i}`,
                    source: e.source, target: e.target,
                    label: e.label || '',
                    markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b' },
                    style: { stroke: '#334155', strokeWidth: 1.5 },
                    labelStyle: { fill: '#64748b', fontSize: 10 },
                  }))
                  const { nodes, edges } = layoutTopology(rawNodes, rawEdges)
                  setTopoNodes(nodes)
                  setTopoEdges(edges)
                  setTopoReady(true)
                }
                break
              case 'done':
                setOutput(mergedOutput)
                setThinking(false)
                setStats({ length: msg.elapsed_ms ? Math.round(msg.elapsed_ms / 100) : mergedOutput.length, elapsed_ms: msg.elapsed_ms || 0 })
                break
              case 'error':
                setError(msg.text || '未知错误')
                setThinking(false)
                break
            }
          } catch { /* skip */ }
        }
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== 'AbortError') setError(e.message)
    } finally {
      setThinking(false)
    }
  }, [reset])

  // ── 双路推演 ──
  const resetDual = useCallback(() => {
    dualAbortRef.current?.abort()
    setDual({
      running: false, outputA: '', outputB: '',
      labels: { a: '路径 A', b: '路径 B' },
      topoNodesA: [], topoEdgesA: [], topoReadyA: false,
      topoNodesB: [], topoEdgesB: [], topoReadyB: false,
      statsA: null, statsB: null, error: '',
    })
  }, [])

  const simulateDual = useCallback(async (event: string, images: File[]) => {
    if (!event.trim() && images.length === 0) return
    resetDual()
    const controller = new AbortController()
    dualAbortRef.current = controller
    setDual(d => ({ ...d, running: true }))
    try {
      const formData = new FormData()
      formData.append('event', event.trim())
      formData.append('user_id', 'default')
      images.forEach(f => formData.append('images', f))
      const resp = await fetch('/api/simulate/dual', { method: 'POST', body: formData, signal: controller.signal })
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
            const p = msg.path as string
            switch (msg.type) {
              case 'meta':
                setDual(d => ({ ...d, labels: { a: msg.path_a_label, b: msg.path_b_label }}))
                break
              case 'content':
                if (p === 'a') setDual(d => ({ ...d, outputA: d.outputA + (msg.text || '') }))
                else if (p === 'b') setDual(d => ({ ...d, outputB: d.outputB + (msg.text || '') }))
                break
              case 'done':
                if (p === 'a') setDual(d => ({ ...d, statsA: { length: msg.length, elapsed_ms: msg.elapsed_ms }}))
                else setDual(d => ({ ...d, statsB: { length: msg.length, elapsed_ms: msg.elapsed_ms }}))
                break
              case 'topology':
                if (msg.data?.nodes && msg.data?.edges) {
                  const rawNodes = msg.data.nodes.map((n: any, i: number) => ({
                    id: n.id, type: 'glowNode',
                    data: { label: n.label, description: n.description || '', nodeType: n.type || 'core' },
                    position: { x: i * 200, y: i * 100 },
                  }))
                  const rawEdges = msg.data.edges.map((e: any, i: number) => ({
                    id: `${e.source}-${e.target}-${i}`, source: e.source, target: e.target,
                    label: e.label || '',
                    markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b' },
                    style: { stroke: '#334155', strokeWidth: 1.5 },
                    labelStyle: { fill: '#64748b', fontSize: 10 },
                  }))
                  const { nodes, edges } = layoutTopology(rawNodes, rawEdges)
                  if (p === 'a') setDual(d => ({ ...d, topoNodesA: nodes, topoEdgesA: edges, topoReadyA: true }))
                  else setDual(d => ({ ...d, topoNodesB: nodes, topoEdgesB: edges, topoReadyB: true }))
                }
                break
              case 'error':
                setDual(d => ({ ...d, error: msg.text || '未知错误' }))
                break
            }
          } catch { /* skip */ }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') setDual(d => ({ ...d, error: e.message, running: false }))
    } finally {
      setDual(d => ({ ...d, running: false }))
    }
  }, [resetDual])

  return { output, thinking, error, loadingText, stats, topoNodes, topoEdges, topoReady, setTopoNodes, setTopoEdges, setOutput, setTopoReady, simulate, simulateV5, reset, drillDown, dual, simulateDual, resetDual, v5Mode, setV5Mode, v5Agents, v5Phase, v5Topology, drillOutput, drillThinking, drillTopoNodes, drillTopoEdges, drillTopoReady }
}

/* ══════════════════════════════════════════════════════════════
   图片上传组件
   ══════════════════════════════════════════════════════════════ */
function ImageUploader({ images, onAdd, onRemove, disabled }: {
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
          dragging ? 'border-wall-accent bg-wall-accent/10 scale-[1.02]' : 'border-wall-border hover:border-wall-accent/50'
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

/* ══════════════════════════════════════════════════════════════
   双路推演 — 单列输出组件
   ══════════════════════════════════════════════════════════════ */
function DualColumn({ label, output, thinking, stats, topoNodes, topoEdges, topoReady, error, borderColor }: {
  label: string; output: string; thinking: boolean
  stats: { length: number; elapsed_ms: number } | null
  topoNodes: Node[]; topoEdges: Edge[]; topoReady: boolean
  error: string; borderColor: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [drillOutput, setDrillOutput] = useState('')
  const [drillThinking, setDrillThinking] = useState(false)
  const [drillTopoNodes, setDrillTopoNodes] = useState<Node[]>([])
  const [drillTopoEdges, setDrillTopoEdges] = useState<Edge[]>([])
  const [drillTopoReady, setDrillTopoReady] = useState(false)
  const drillAbortRef = useRef<AbortController | null>(null)
  useEffect(() => { if (ref.current) ref.current.scrollTop = ref.current.scrollHeight }, [output, drillOutput])

  const handleDrillDown = async (node: Node) => {
    const query = `基于之前的推演，我选择深入分析这个分支：「${(node.data as any)?.label}」——${(node.data as any)?.description}。请对此进行更深入的破壁推演。`
    drillAbortRef.current?.abort()
    const controller = new AbortController()
    drillAbortRef.current = controller
    setDrillOutput('')
    setDrillThinking(true)
    setDrillTopoReady(false)
    const formData = new FormData(); formData.append('event', query); formData.append('user_id', 'default')
    try {
      const resp = await fetch('/api/simulate', { method: 'POST', body: formData, signal: controller.signal })
      if (!resp.ok) throw new Error('HTTP ' + resp.status)
      const reader = resp.body?.getReader(); if (!reader) return
      const decoder = new TextDecoder(); let buffer = ''; let full = ''
      while (true) {
        const { done, value } = await reader.read(); if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n'); buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try { const msg = JSON.parse(line.slice(6))
            if (msg.type === 'content') { full += msg.text || ''; setDrillOutput(full) }
            else if (msg.type === 'topology' && msg.data?.nodes) {
              const rn = msg.data.nodes.map((n: any, i: number) => ({ id: n.id, type: 'glowNode', data: { label: n.label, description: n.description || '', nodeType: n.type || 'core' }, position: { x: i * 200, y: i * 100 } }))
              const re = msg.data.edges.map((e: any, i: number) => ({ id: `${e.source}-${e.target}-${i}`, source: e.source, target: e.target, label: e.label || '', markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b' }, style: { stroke: '#334155', strokeWidth: 1.5 }, labelStyle: { fill: '#64748b', fontSize: 10 } }))
              const { nodes, edges } = layoutTopology(rn, re)
              setDrillTopoNodes(nodes); setDrillTopoEdges(edges); setDrillTopoReady(true)
            }
          } catch { }
        }
      }
    } catch (e: any) { if (e.name !== 'AbortError') setDrillOutput(`延伸失败: ${e.message}`) }
    setDrillThinking(false)
  }
  return (
    <div className="w-1/2 flex flex-col min-w-0 flex-shrink-0">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-wall-border/30 shrink-0" style={{ borderLeft: `3px solid ${borderColor}` }}>
        <span className="text-xs font-semibold text-wall-text truncate">{label}</span>
        {thinking && !output && <Loader2 size={12} className="animate-spin text-wall-muted ml-auto" />}
        {stats && <span className="text-[10px] text-wall-dim ml-auto">{stats.length}字 · {stats.elapsed_ms > 0 ? `${(stats.elapsed_ms / 1000).toFixed(1)}s` : ''}</span>}
      </div>
      <div ref={ref} className="flex-1 overflow-y-auto p-4 scroll-smooth">
        {error && <div className="flex items-center gap-2 p-3 bg-red-500/5 border border-red-500/20 rounded-lg"><AlertCircle size={14} className="text-red-400 shrink-0" /><p className="text-red-400 text-xs">{error}</p></div>}
        {thinking && !output && (
          <div className="flex flex-col items-center justify-center h-full space-y-3 opacity-40">
            <div className="w-8 h-8 rounded-full border-2 border-wall-accent/20 border-t-wall-accent animate-spin" />
            <p className="text-wall-muted text-xs">推演中...</p>
          </div>
        )}
        {output && <div className="markdown-body text-xs leading-relaxed"><ReactMarkdown remarkPlugins={[remarkGfm]}>{output}</ReactMarkdown></div>}
        {!output && !thinking && !error && (
          <div className="flex items-center justify-center h-full opacity-15"><p className="text-wall-muted text-xs">等待推演...</p></div>
        )}
      </div>
      {topoReady && (
        <div className="h-56 relative border-t border-wall-border/30 shrink-0 overflow-hidden" style={{ minWidth: 0 }}>
          <ReactFlow nodes={topoNodes} edges={topoEdges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.2 }}
            minZoom={0.2} maxZoom={1.2} nodesDraggable={false} nodesConnectable={false}
            onNodeClick={(_, node) => setSelectedNode(node)}
            defaultEdgeOptions={{ type: 'smoothstep', animated: true, style: { stroke: '#334155', strokeWidth: 1 } }}
            proOptions={{ hideAttribution: true }}>
            <Background color="#1e2a3a" gap={16} />
          </ReactFlow>
          <div className="absolute top-2 left-2 bg-wall-surface/80 backdrop-blur border border-wall-border rounded px-2 py-0.5 text-wall-dim text-[10px] z-10 pointer-events-none">拓扑 · 点光查看详情</div>
          {selectedNode && (
            <div className="absolute bottom-4 left-4 right-4 bg-wall-surface/95 backdrop-blur border border-wall-border rounded-2xl p-4 z-10 shadow-2xl">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold" style={{ color: TYPE_STYLES[(selectedNode.data as any)?.nodeType]?.border || '#6366f1' }}>
                  {TYPE_STYLES[(selectedNode.data as any)?.nodeType]?.label || '节点'}
                </span>
                <button onClick={() => setSelectedNode(null)} className="text-wall-muted hover:text-wall-text"><X size={14} /></button>
              </div>
              <p className="text-wall-text font-semibold text-sm mb-1">{(selectedNode.data as any)?.label}</p>
              <p className="text-wall-muted text-xs mb-3">{(selectedNode.data as any)?.description}</p>
              <button onClick={() => { handleDrillDown(selectedNode); setSelectedNode(null) }}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-[#818cf8]/10 border border-[#818cf8]/30 rounded-xl text-[#818cf8] text-xs hover:bg-[#818cf8]/20 transition-all">
                <Share2 size={12} /> 在此路径内延伸推演
              </button>
            </div>
          )}
        </div>
      )}
      {/* 路径内延伸推演结果 */}
      {(drillOutput || drillThinking) && (
        <div className="border-t-2 border-purple-500/30 shrink-0 max-h-[300px] overflow-y-auto">
          <div className="flex items-center gap-2 px-3 py-2 bg-purple-500/[0.05]">
            <span className="text-[10px] text-purple-400 font-mono">🔀 分支延伸</span>
            {drillThinking && <Loader2 size={10} className="animate-spin text-purple-400" />}
          </div>
          {drillOutput && <div className="p-3 markdown-body text-xs leading-relaxed"><ReactMarkdown remarkPlugins={[remarkGfm]}>{drillOutput}</ReactMarkdown></div>}
          {drillTopoReady && (
            <div className="h-48 relative border-t border-wall-border/30">
              <ReactFlow nodes={drillTopoNodes} edges={drillTopoEdges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.2 }}
                minZoom={0.2} maxZoom={1.2} nodesDraggable={false} nodesConnectable={false}
                onNodeClick={(_, node) => setSelectedNode(node)}
                defaultEdgeOptions={{ type: 'smoothstep', animated: true, style: { stroke: '#334155', strokeWidth: 1 } }}
                proOptions={{ hideAttribution: true }}>
                <Background color="#1e2a3a" gap={16} />
              </ReactFlow>
            </div>
          )}
        </div>
      )}
    </div>
  )
}


/* ══════════════════════════════════════════════════════════════
   主页面
   ══════════════════════════════════════════════════════════════ */
export default function Home() {
  const [input, setInput] = useState('')
  const [images, setImages] = useState<File[]>([])
  const { output, thinking, error, loadingText, stats, topoNodes, topoEdges, topoReady,
    setTopoNodes, setTopoEdges, setOutput, setTopoReady, simulate, simulateV5, reset, drillDown, dual, simulateDual, resetDual,
    v5Mode, setV5Mode, v5Agents, v5Phase, drillOutput, drillThinking, drillTopoNodes, drillTopoEdges, drillTopoReady } = useWallbreaker()
  const outputRef = useRef<HTMLDivElement>(null)
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [showTopo, setShowTopo] = useState(true)
  const [mode, setMode] = useState<'single' | 'dual'>('single')

  // ── 历史记录状态 ──
  const [showHistory, setShowHistory] = useState(false)
  const [historyRecords, setHistoryRecords] = useState<any[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)

  // 拉取历史列表
  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true)
    try {
      const resp = await fetch('/api/history/list?user_id=default')
      if (resp.ok) {
        const data = await resp.json()
        setHistoryRecords(data.records || [])
      }
    } catch { /* ignore */ }
    setHistoryLoading(false)
  }, [])

  // 初始加载
  useEffect(() => { fetchHistory() }, [fetchHistory])

  // 加载一条历史记录到主视图
  const loadHistoryRecord = useCallback(async (recordId: string) => {
    try {
      const resp = await fetch(`/api/history/${recordId}?user_id=default`)
      if (!resp.ok) return
      const record = await resp.json()

      // 填充文本
      reset()
      setInput(record.query || '')
      setTimeout(() => {
        // 模拟逐字输出效果 — 直接全量设置
        setOutput(record.result || '')
        if (record.stats) {
          // @ts-ignore - setStats via internal path
          document.dispatchEvent(new CustomEvent('loadHistoryStats', { detail: record.stats }))
        }
        // 设置拓扑
        if (record.topology && record.topology.nodes && record.topology.edges) {
          const rawNodes = record.topology.nodes.map((n: any, i: number) => ({
            id: n.id, type: 'glowNode' as const,
            data: { label: n.label, description: n.description || '', nodeType: n.type || 'core' },
            position: { x: i * 200, y: i * 100 },
          }))
          const rawEdges = record.topology.edges.map((e: any, i: number) => ({
            id: `${e.source}-${e.target}-${i}`,
            source: e.source, target: e.target,
            label: e.label || '',
            markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b' },
            style: { stroke: '#334155', strokeWidth: 1.5 },
            labelStyle: { fill: '#64748b', fontSize: 10 },
          }))
          const { nodes, edges } = layoutTopology(rawNodes, rawEdges)
          setTopoNodes(nodes)
          setTopoEdges(edges)
          setTopoReady(true)
        }

        // 关闭历史面板
        setShowHistory(false)
      }, 50)
    } catch { /* ignore */ }
  }, [reset, setTopoNodes, setTopoEdges, setInput])

  // 删除一条记录
  const deleteHistoryRecord = useCallback(async (recordId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      const resp = await fetch(`/api/history/${recordId}?user_id=default`, { method: 'DELETE' })
      if (resp.ok) {
        setHistoryRecords((prev) => prev.filter((r) => r.id !== recordId))
      }
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    if (outputRef.current) outputRef.current.scrollTop = outputRef.current.scrollHeight
  }, [output])

  const handleSubmit = () => {
    if ((!input.trim() && images.length === 0)) return
    if (mode === 'single' && thinking) return
    if (mode === 'dual' && dual.running) return
    if (mode === 'dual') {
      simulateDual(input.trim(), images)
    } else if (v5Mode) {
      simulateV5(input.trim(), images, false)
    } else {
      simulate(input.trim(), images, undefined, () => fetchHistory())
    }
  }

  const onNodeClick = (_: any, node: Node) => setSelectedNode(node)

  return (
    <div className="flex flex-col h-screen">
      {/* ── 顶部栏 ── */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-wall-border/50 bg-wall-surface/50">
        <div className="flex items-center gap-3">
          <button
            onClick={() => { setShowHistory(!showHistory); if (!showHistory) fetchHistory() }}
            title={showHistory ? '关闭历史记录' : '查看历史记录'} aria-label={showHistory ? '关闭历史记录' : '查看历史记录'}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs transition-all ${
              showHistory
                ? 'border-wall-accent/50 bg-wall-accent/10 text-wall-accent'
                : 'border-wall-border text-wall-muted hover:text-wall-text hover:border-wall-accent/30'
            }`}
          >
            <History size={14} />
            <span>历史记录</span>
            {historyRecords.length > 0 && (
              <span className="px-1.5 py-0.5 rounded-full bg-wall-accent/20 text-wall-accent text-[10px] font-mono">
                {historyRecords.length}
              </span>
            )}
          </button>
          <div className="flex items-center gap-0.5 border border-wall-border rounded-lg p-0.5">
            <button onClick={() => { setMode('single'); reset() }} title="单路推演模式" aria-label="单路推演模式"
              className={`px-2.5 py-1 rounded-md text-xs transition-all ${mode === 'single' ? 'bg-wall-accent/20 text-wall-accent' : 'text-wall-muted hover:text-wall-text'}`}>单路</button>
            <button onClick={() => { setMode('dual'); reset(); resetDual() }} title="双路对比推演模式" aria-label="双路对比推演模式"
              className={`px-2.5 py-1 rounded-md text-xs transition-all ${mode === 'dual' ? 'bg-wall-accent/20 text-wall-accent' : 'text-wall-muted hover:text-wall-text'}`}>双路</button>
          </div>
          {/* V5.0 切换 */}
          <button
            onClick={() => { setV5Mode(!v5Mode); reset() }}
            title={v5Mode ? '切换回 V4.0 单引擎模式' : '切换到 V5.0 多智能体对抗模式'} aria-label={v5Mode ? '切换回 V4.0 单引擎模式' : '切换到 V5.0 多智能体对抗模式'}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs transition-all ${
              v5Mode
                ? 'border-purple-500/50 bg-purple-500/10 text-purple-400 shadow-[0_0_12px_rgba(168,85,247,0.15)]'
                : 'border-wall-border text-wall-muted hover:text-wall-text hover:border-wall-accent/30'
            }`}
            title={v5Mode ? 'V5.0 多智能体对抗模式' : '切换到 V5.0 多智能体模式'}
          >
            <span className="text-xs">{v5Mode ? '😈' : '🧠'}</span>
            <span>{v5Mode ? 'V5.0 多Agent' : 'V4.0'}</span>
          </button>
          <h1 className="text-sm font-semibold tracking-wide">
            <span className="text-wall-accent">认知破壁机</span>
            <span className={`ml-2 text-xs font-normal ${v5Mode ? 'text-purple-400' : 'text-wall-muted'}`}>
              {v5Mode ? 'V5.0 多Agent' : 'V4.0'}
            </span>
          </h1>
        </div>
        <p className="text-wall-dim text-[10px] hidden sm:block">
          {mode === 'dual' ? '双路对比推演' : v5Mode ? 'V5.0 多智能体对抗 · 魔鬼代言人挑刺' : '现实主义博弈引擎 · 拓扑沙盘推演'}
        </p>
      </div>

      {/* ── 主内容：历史面板 + 左右两栏 ── */}
      <div className="flex flex-1 min-h-0 relative">
        {/* 历史记录侧边栏 */}
        <div className={`border-r border-wall-border/50 bg-wall-surface/30 overflow-y-auto transition-all duration-300 ${
          showHistory ? 'w-80 min-w-[320px]' : 'w-0 min-w-0 border-r-0'
        }`}>
          <div className="w-80 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock size={14} className="text-wall-muted" />
                <span className="text-wall-muted text-xs font-mono tracking-wider">推演历史</span>
              </div>
              <button onClick={() => setShowHistory(false)} title="关闭历史面板" aria-label="关闭历史面板" className="text-wall-dim hover:text-wall-text transition-colors">
                <ChevronLeft size={16} />
              </button>
            </div>
            {historyLoading && historyRecords.length === 0 && (
              <div className="flex items-center justify-center py-12">
                <Loader2 size={20} className="animate-spin text-wall-muted" />
              </div>
            )}
            {!historyLoading && historyRecords.length === 0 && (
              <div className="text-center py-12 space-y-2">
                <FileText size={24} className="mx-auto text-wall-dim" />
                <p className="text-wall-dim text-xs">暂无历史记录</p>
                <p className="text-wall-dim text-[10px]">完成一次推演后将自动保存</p>
              </div>
            )}
            {historyRecords.map((record) => (
              <div
                key={record.id}
                onClick={() => loadHistoryRecord(record.id)}
                className="group p-3 rounded-xl border border-wall-border/50 bg-wall-surface/50 hover:border-wall-accent/30 hover:bg-wall-surface/80 cursor-pointer transition-all"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-wall-text text-xs font-medium line-clamp-2 flex-1">
                    {record.query || '(无输入)'}
                  </p>
                  <button
                    onClick={(e) => deleteHistoryRecord(record.id, e)}
                    className="shrink-0 p-1 rounded-md text-wall-dim hover:text-red-400 hover:bg-red-400/10 opacity-0 group-hover:opacity-100 transition-all"
                    title="删除此记录" aria-label="删除此记录"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
                <div className="flex items-center gap-3 mt-2 text-[10px] text-wall-dim">
                  <span className="flex items-center gap-1">
                    <Clock size={10} />
                    {record.created_at ? new Date(record.created_at).toLocaleString('zh-CN', {
                      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                    }) : ''}
                  </span>
                  {record.stats?.length > 0 && (
                    <span>{record.stats.length}字</span>
                  )}
                  {record.has_topology && (
                    <span className="text-wall-accent/70">📊 拓扑</span>
                  )}
                  {record.images_count > 0 && (
                    <span>📷×{record.images_count}</span>
                  )}
                </div>
                {record.preview && (
                  <p className="text-wall-dim/60 text-[10px] mt-2 line-clamp-2 leading-relaxed">
                    {record.preview}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 左栏：输入 */}
        <div className="flex-1 flex flex-col items-center justify-center p-6 lg:p-12 relative border-r border-wall-border/50">
          <div className="w-full max-w-xl space-y-6">
            {/* 标题 */}
            <div className="text-center space-y-2">
              <h1 className="text-3xl lg:text-4xl font-bold tracking-tight">
                <span className="text-wall-accent">认知破壁机</span>
              </h1>
              <p className="text-wall-muted text-sm font-medium tracking-widest uppercase">Cognitive Wallbreaker</p>
              <div className="flex items-center justify-center gap-2 mt-1">
                <span className={`px-2 py-0.5 rounded-md border text-xs font-mono transition-all ${
                  v5Mode
                    ? 'bg-purple-500/10 border-purple-500/20 text-purple-400'
                    : 'bg-wall-accent/10 border-wall-accent/20 text-wall-accent'
                }`}>{v5Mode ? 'V5.0' : 'V4.0'}</span>
                <span className="text-wall-dim text-xs">
                  {v5Mode ? '多智能体对抗引擎 · 七Agent辩论' : '现实主义博弈引擎 · 拓扑沙盘推演'}
                </span>
              </div>
            </div>
            <div className="relative">
              <div className="absolute -inset-1 bg-wall-glow/10 rounded-2xl blur-xl animate-breathe" />
              <textarea value={input} onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit() } }}
                placeholder="告诉我你正在纠结的决策..." disabled={thinking}
                className="relative w-full h-36 lg:h-44 bg-wall-surface border border-wall-border rounded-xl p-5 text-wall-text placeholder-wall-muted/40 resize-none focus:outline-none focus:border-wall-accent/50 transition-colors disabled:opacity-50 font-sans text-sm leading-relaxed"
              />
            </div>
            <ImageUploader images={images} onAdd={(f) => setImages(p => [...p, ...f].slice(0,5))}
              onRemove={(i) => setImages(p => p.filter((_,j) => j !== i))} disabled={thinking} />
            <div className="flex gap-3 justify-center">
              <button onClick={handleSubmit}
                disabled={(!input.trim() && images.length === 0) || thinking}
                className="flex items-center gap-2 px-6 py-3 bg-wall-accent/10 border border-wall-accent/30 rounded-xl text-wall-accent hover:bg-wall-accent/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all text-sm font-medium">
                {thinking ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
                {thinking ? '推演中...' : '开始推演'}
              </button>
              <button onClick={() => { reset(); setImages([]) }}
                disabled={!output && !error}
                className="flex items-center gap-2 px-4 py-3 border border-wall-border rounded-xl text-wall-muted hover:text-wall-text hover:border-wall-accent/30 disabled:opacity-20 disabled:cursor-not-allowed transition-all text-sm">
                <Trash2 size={14} /> 重置
              </button>
            </div>
            <p className="text-center text-wall-dim text-xs">
              <CornerDownLeft size={10} className="inline mr-1" /> Enter 发送 · 支持拖拽上传图片
            </p>
          </div>
        </div>

        {/* 右栏：输出 + 拓扑 */}
        <div className="flex-1 flex flex-col bg-wall-surface/30">
          {mode === 'single' ? (<>
          {/* 输出 Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-wall-border">
            <span className="text-wall-muted text-xs font-mono tracking-wider">
              {v5Mode && v5Phase ? v5Phase : thinking ? loadingText : output ? `📜 推演结果 · ${stats ? `${stats.length}字` : ''}` : '等待输入...'}
            </span>
            <div className="flex gap-2 items-center">
              {thinking && (
                <span className="flex items-center gap-2 text-wall-accent/60 text-xs">
                  <span className="w-2 h-2 rounded-full bg-wall-accent animate-ping" /> {v5Mode ? '多Agent运行中' : '流式'}
                </span>
              )}
              {topoReady && (
                <button onClick={() => setShowTopo(!showTopo)} title={showTopo ? '隐藏拓扑图' : '显示拓扑图'} aria-label={showTopo ? '隐藏拓扑图' : '显示拓扑图'}
                  className={`text-xs px-2 py-1 rounded-lg border transition-all ${
                    showTopo ? 'border-wall-accent/50 bg-wall-accent/10 text-wall-accent'
                            : 'border-wall-border text-wall-muted'
                  }`}>
                  {showTopo ? '📊 拓扑开' : '📊 拓扑关'}
                </button>
              )}
            </div>
          </div>

          {/* ── V5.0 多智能体状态面板 ── */}
          {v5Mode && thinking && Object.keys(v5Agents).length > 0 && (
            <div className="px-4 py-3 border-b border-wall-border/30 bg-purple-500/[0.02] relative overflow-hidden">
              {/* 扫描线 */}
              <div className="scan-overlay opacity-30" />
              <div className="flex items-center gap-2 mb-3">
                <span className="text-wall-dim text-[10px] font-mono tracking-wider">🔪 多智能体对抗推演</span>
                <span className="flex-1 h-px bg-gradient-to-r from-purple-500/30 to-transparent" />
                <span className="flex items-center gap-1 text-purple-400/60 text-[9px]">
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
                  进行中
                </span>
              </div>
              <div className="grid grid-cols-4 gap-2">
                {Object.entries(v5Agents).map(([key, agent], idx) => {
                  const isDevil = key === 'devil'
                  const isJudge = key === 'judge'
                  const isRunning = agent.status === 'running'
                  const isDone = agent.status === 'done'
                  const isError = agent.status === 'error'
                  const isPending = agent.status === 'pending'

                  let borderAnim = ''
                  let extraAnim = ''
                  if (isPending) borderAnim = 'animate-border-pending'
                  else if (isRunning) borderAnim = 'animate-border-running'
                  else if (isDone && isJudge) borderAnim = 'animate-border-rainbow'
                  else if (isDone && isDevil) { borderAnim = 'animate-border-done'; extraAnim = 'animate-devil-shake' }
                  else if (isDone) borderAnim = 'animate-border-done'
                  else if (isError) borderAnim = 'animate-border-error'

                  const bgClass = isDone
                    ? 'bg-green-500/8'
                    : isRunning
                    ? 'bg-yellow-500/8'
                    : isError
                    ? 'bg-red-500/8'
                    : isPending
                    ? 'bg-wall-surface/20'
                    : 'bg-wall-surface/20'

                  const textClass = isDone
                    ? 'text-green-300'
                    : isRunning
                    ? 'text-yellow-300'
                    : isError
                    ? 'text-red-300'
                    : 'text-wall-dim'

                  const statusIcon = isDone ? '✅' : isRunning ? '🔄' : isError ? '❌' : '⏳'

                  return (
                    <div
                      key={key}
                      className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg border-2 text-[10px] ${bgClass} ${textClass} ${borderAnim} ${extraAnim}`}
                      style={{ animationDelay: `${idx * 60}ms` }}
                    >
                      <span className={`text-xs ${isRunning ? 'animate-pulse' : ''}`}>{agent.emoji}</span>
                      <span className="truncate flex-1">{agent.name}</span>
                      <span className="text-[9px]">{statusIcon}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* 输出内容区 */}
          <div className="flex-1 flex flex-col min-h-0">
            {/* 文本输出 */}
            <div ref={outputRef} className={`overflow-y-auto p-6 lg:p-10 scroll-smooth relative ${showTopo && topoReady ? 'flex-1 border-b border-wall-border' : 'flex-1'}`}>
              {thinking && <div className="scan-overlay opacity-20" />}
              {error && (
                <div className="flex items-start gap-3 p-4 bg-red-500/5 border border-red-500/20 rounded-xl">
                  <AlertCircle size={16} className="text-red-400 mt-0.5 shrink-0" />
                  <div><p className="text-red-400 text-sm font-medium">推演出错</p><p className="text-red-400/70 text-xs mt-1">{error}</p></div>
                </div>
              )}
              {thinking && !output && (
                <div className="flex flex-col items-center justify-center h-full space-y-6">
                  {/* 多层旋转光环 */}
                  <div className="relative w-24 h-24">
                    <div className="absolute inset-0 rounded-full border border-wall-accent/10 animate-spin" style={{ animationDuration: '3s' }} />
                    <div className="absolute inset-2 rounded-full border-2 border-wall-accent/20 border-t-wall-accent animate-spin" style={{ animationDuration: '1.5s' }} />
                    <div className="absolute inset-4 rounded-full border border-purple-500/15 border-t-purple-400/40 animate-spin" style={{ animationDuration: '2s', animationDirection: 'reverse' }} />
                    <Brain size={28} className="absolute inset-0 m-auto text-wall-accent/50 animate-pulse-slow" />
                  </div>
                  <p className="text-wall-muted text-sm animate-scan">{loadingText}</p>
                  {/* 能量粒子线 */}
                  <div className="flex gap-1 items-center">
                    {[0, 1, 2].map(i => (
                      <div key={i} className="w-1 h-1 rounded-full bg-wall-accent/40 animate-pulse"
                        style={{ animationDelay: `${i * 0.3}s`, animationDuration: '1.5s' }} />
                    ))}
                  </div>
                </div>
              )}
              {output && (
                <div className={`markdown-body ${v5Mode ? 'animate-judge-reveal' : 'animate-fade-in-up'}`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{output}</ReactMarkdown>
                </div>
              )}
              {!output && !thinking && !error && (
                <div className="flex flex-col items-center justify-center h-full space-y-4 opacity-20">
                  <div className="relative">
                    <div className="w-16 h-16 rounded-full border border-wall-accent/10 animate-spin" style={{ animationDuration: '6s' }} />
                    <Brain size={32} className="absolute inset-0 m-auto text-wall-accent/40" />
                  </div>
                  <p className="text-wall-muted text-sm font-mono tracking-wider">
                    {v5Mode ? '🔪 七Agent对抗推演待命' : '输入决策，开始五刀推演...'}
                  </p>
                </div>
              )}
            </div>

            {/* 拓扑沙盘 */}
            {showTopo && topoReady && (
              <div className="flex-1 relative min-h-[300px]">
                <ReactFlow
                  nodes={topoNodes}
                  edges={topoEdges}
                  nodeTypes={nodeTypes}
                  onNodeClick={onNodeClick}
                  fitView
                  fitViewOptions={{ padding: 0.3 }}
                  minZoom={0.3}
                  maxZoom={2}
                  defaultEdgeOptions={{
                    type: 'smoothstep',
                    animated: true,
                    style: { stroke: '#475569', strokeWidth: 1.5, strokeDasharray: '6 3' },
                  }}
                  proOptions={{ hideAttribution: true }}
                >
                  <Background color="#1e2a3a" gap={24} />
                  <Controls className="!bg-wall-surface !border-wall-border !rounded-xl" />
                  <MiniMap
                    style={{ background: '#0f1624', border: '1px solid #1e2a3a' }}
                    maskColor="rgba(8,12,20,0.7)"
                    nodeColor={(n) => TYPE_STYLES[(n.data as any)?.nodeType]?.border || '#6366f1'}
                  />
                </ReactFlow>
                <div className="absolute top-3 left-3 bg-wall-surface/90 backdrop-blur border border-wall-border rounded-lg px-3 py-1.5 text-wall-muted text-xs z-10">
                  🔗 决策拓扑沙盘 · 点击光点查看详情
                </div>
                {/* 选中节点详情卡 */}
                {selectedNode && (
                  <div className="absolute bottom-4 right-4 w-72 bg-wall-surface/95 backdrop-blur border border-wall-border rounded-2xl p-5 z-10 shadow-2xl">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold" style={{
                        color: TYPE_STYLES[(selectedNode.data as any)?.nodeType]?.border || '#6366f1'
                      }}>
                        {TYPE_STYLES[(selectedNode.data as any)?.nodeType]?.label || '节点'}
                      </span>
                      <button onClick={() => setSelectedNode(null)} title="关闭节点详情" aria-label="关闭节点详情" className="text-wall-muted hover:text-wall-text">
                        <X size={14} />
                      </button>
                    </div>
                    <p className="text-wall-text font-semibold text-sm mb-1">
                      {(selectedNode.data as any)?.label}
                    </p>
                    <p className="text-wall-muted text-xs mb-4">
                      {(selectedNode.data as any)?.description}
                    </p>
                    <button
                      onClick={() => { drillDown(selectedNode); setSelectedNode(null) }}
                      title="沿此分支深入推演" aria-label="沿此分支深入推演"
                      className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-wall-accent/10 border border-wall-accent/30 rounded-xl text-wall-accent text-xs hover:bg-wall-accent/20 transition-all"
                    >
                      <Share2 size={12} /> 沿此分支继续推演 (What-If)
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
                  {/* 单路路径内延伸推演 */}
          {(drillOutput || drillThinking) && (
            <div className="border-t-2 border-purple-500/30 bg-purple-500/[0.02]">
              <div className="flex items-center gap-2 px-6 py-2">
                <span className="text-xs text-purple-400 font-mono">延伸推演</span>
                {drillThinking && <Loader2 size={12} className="animate-spin text-purple-400" />}
              </div>
              <div className="px-6 pb-4 max-h-[400px] overflow-y-auto markdown-body">
                {drillOutput && <ReactMarkdown remarkPlugins={[remarkGfm]}>{drillOutput}</ReactMarkdown>}
              </div>
              {drillTopoReady && (
                <div className="h-[350px] relative border-t border-wall-border/30 mx-6 mb-4 rounded-xl overflow-hidden">
                  <ReactFlow nodes={drillTopoNodes} edges={drillTopoEdges} nodeTypes={nodeTypes} fitView fitViewOptions={{padding:0.3}}
                    minZoom={0.3} maxZoom={2} nodesDraggable={false} nodesConnectable={false}
                    defaultEdgeOptions={{type:'smoothstep',animated:true,style:{stroke:'#334155',strokeWidth:1.5,strokeDasharray:'6 3'}}}
                    proOptions={{hideAttribution:true}}>
                    <Background color="#1e2a3a" gap={24} />
                  </ReactFlow>
                </div>
              )}
            </div>
          )}
        
        </>) : (<>
          {/* 双路 Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-wall-border">
            <span className="text-wall-muted text-xs font-mono tracking-wider">
              {dual.running ? '⏳ 双路推演中...' : (dual.outputA || dual.outputB) ? '📜 双路对比' : '等待输入...'}
            </span>
            <div className="flex gap-2 items-center">
              {dual.running && (
                <span className="flex items-center gap-2 text-wall-accent/60 text-xs">
                  <span className="w-2 h-2 rounded-full bg-wall-accent animate-ping" /> 流式
                </span>
              )}
            </div>
          </div>
          {/* 双栏输出 */}
          <div className="flex-1 flex min-h-0 min-w-0">
            <DualColumn label={dual.labels.a} output={dual.outputA} thinking={dual.running && !dual.outputA}
              stats={dual.statsA} topoNodes={dual.topoNodesA} topoEdges={dual.topoEdgesA}
              topoReady={dual.topoReadyA} error={dual.error} borderColor="#6366f1"
 />
            <div className="w-px bg-wall-border/50" />
            <DualColumn label={dual.labels.b} output={dual.outputB} thinking={dual.running && !dual.outputB}
              stats={dual.statsB} topoNodes={dual.topoNodesB} topoEdges={dual.topoEdgesB}
              topoReady={dual.topoReadyB} error="" borderColor="#f59e0b"
 />
          </div>
        </>)}
        </div>
      </div>
    </div>
  )
}
