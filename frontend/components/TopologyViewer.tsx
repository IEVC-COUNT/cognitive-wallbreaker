'use client'

import { useState } from 'react'
import ReactFlow, { Background, Controls, MiniMap, Node, Edge } from 'reactflow'
import 'reactflow/dist/style.css'
import { X, Share2 } from 'lucide-react'
import { layoutTopology, TYPE_STYLES } from '@/hooks/useWallbreaker'
import { nodeTypes } from './GlowNode'

export function TopologyViewer({ nodes, edges, ready, onDrillDown }: {
  nodes: Node[]; edges: Edge[]; ready: boolean
  onDrillDown?: (label: string, desc: string) => void
}) {
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)

  if (!ready) return null

  return (
    <div className="flex-1 relative min-h-[300px]">
      <ReactFlow
        nodes={nodes} edges={edges} nodeTypes={nodeTypes}
        onNodeClick={(_, node) => setSelectedNode(node)}
        fitView fitViewOptions={{ padding: 0.3 }}
        minZoom={0.3} maxZoom={2} nodesDraggable={false} nodesConnectable={false}
        elementsSelectable={false}
        defaultEdgeOptions={{ type: 'smoothstep', animated: true, style: { stroke: '#475569', strokeWidth: 1.5, strokeDasharray: '6 3' } }}
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
        决策拓扑沙盘 · 点击光点查看详情
      </div>
      {selectedNode && (
        <div className="absolute bottom-4 right-4 w-72 bg-wall-surface/95 backdrop-blur border border-wall-border rounded-2xl p-5 z-10 shadow-2xl">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold" style={{ color: TYPE_STYLES[(selectedNode.data as any)?.nodeType]?.border || '#6366f1' }}>
              {TYPE_STYLES[(selectedNode.data as any)?.nodeType]?.label || '节点'}
            </span>
            <button onClick={() => setSelectedNode(null)} title="关闭" aria-label="关闭" className="text-wall-muted hover:text-wall-text"><X size={14} /></button>
          </div>
          <p className="text-wall-text font-semibold text-sm mb-1">{(selectedNode.data as any)?.label}</p>
          <p className="text-wall-muted text-xs mb-4">{(selectedNode.data as any)?.description}</p>
          {onDrillDown && (
            <button onClick={() => { onDrillDown((selectedNode.data as any)?.label, (selectedNode.data as any)?.description); setSelectedNode(null) }}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-[#818cf8]/10 border border-[#818cf8]/30 rounded-xl text-[#818cf8] text-xs hover:bg-[#818cf8]/20 transition-all">
              <Share2 size={12} /> 沿此分支继续推演 (What-If)
            </button>
          )}
        </div>
      )}
    </div>
  )
}
