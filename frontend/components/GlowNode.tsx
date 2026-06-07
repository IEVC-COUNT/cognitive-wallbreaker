'use client'

import { Position, Handle } from 'reactflow'
import { TYPE_STYLES, NODE_WIDTH } from '@/hooks/useWallbreaker'

// 全局回调，由 TopologyViewer 设置
let _onDrillDown: ((label: string, desc: string) => void) | null = null
export function setNodeDrillHandler(fn: ((label: string, desc: string) => void) | null) {
  _onDrillDown = fn
}

export function GlowNode({ data, selected }: { data: any; selected: boolean }) {
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
      <Handle type="target" position={Position.Top} style={{ background: style.border }} isConnectable={false} />
      <div className="text-xs font-semibold truncate" style={{ color: style.border }}>{data.label}</div>
      <div className="text-[10px] text-wall-muted mt-1 truncate">{data.description}</div>
      <div
        className="text-[9px] mt-1.5 px-2 py-0.5 rounded border border-white/10 text-white/40 hover:bg-white/10 hover:text-white/70 transition-colors text-center cursor-pointer"
        onClick={(e) => { e.stopPropagation(); _onDrillDown?.(data.label, data.description) }}
      >
        🔀 延伸推演
      </div>
      <Handle type="source" position={Position.Bottom} style={{ background: style.border }} isConnectable={false} />
    </div>
  )
}

export const nodeTypes = { glowNode: GlowNode }

export function buildTopoNodes(rawNodes: any[]) {
  return rawNodes.map((n: any, i: number) => ({
    id: n.id, type: 'glowNode' as const,
    data: { label: n.label, description: n.description || '', nodeType: n.type || 'core' },
    position: { x: i * 200, y: i * 100 },
  }))
}

export function buildTopoEdges(rawEdges: any[]) {
  return rawEdges.map((e: any, i: number) => ({
    id: `${e.source}-${e.target}-${i}`,
    source: e.source, target: e.target,
    label: e.label || '',
    markerEnd: { type: 'arrowclosed' as any, color: '#64748b' },
    style: { stroke: '#334155', strokeWidth: 1.5 },
    labelStyle: { fill: '#64748b', fontSize: 10 },
  }))
}
