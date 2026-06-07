'use client'

import { useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Loader2 } from 'lucide-react'

export function MarkdownOutput({ output, thinking, error, loadingText, emptyText }: {
  output: string; thinking: boolean; error: string; loadingText: string; emptyText: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => { if (ref.current) ref.current.scrollTop = ref.current.scrollHeight }, [output])

  return (
    <div ref={ref} className="overflow-y-auto p-6 scroll-smooth relative flex-1">
      {error && (
        <div className="flex items-start gap-3 p-4 bg-red-500/5 border border-red-500/20 rounded-xl mb-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}
      {thinking && !output && (
        <div className="flex flex-col items-center justify-center h-full space-y-4">
          <div className="w-8 h-8 rounded-full border-2 border-[#818cf8]/20 border-t-[#818cf8] animate-spin" />
          <p className="text-wall-muted text-sm">{loadingText}</p>
        </div>
      )}
      {output && (
        <div className="markdown-body animate-fade-in-up">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{output}</ReactMarkdown>
        </div>
      )}
      {!output && !thinking && (
        <div className="flex items-center justify-center h-full opacity-20">
          <p className="text-wall-muted text-sm font-mono">{emptyText}</p>
        </div>
      )}
    </div>
  )
}
