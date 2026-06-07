import type { Metadata } from 'next'
import Link from 'next/link'
import { Brain } from 'lucide-react'
import './globals.css'

export const metadata: Metadata = {
  title: '认知破壁机 V6.0 · 公共个人决策推演平台',
  description: 'AI多智能体对抗推演 — 提交你的个人决策，七Agent公开推演，所有人可浏览学习',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet" />
      </head>
      <body className="min-h-screen bg-wall-bg text-wall-text antialiased">
        {/* Navigation */}
        <nav className="sticky top-0 z-50 backdrop-blur border-b border-wall-border/50 bg-wall-bg/80">
          <div className="max-w-6xl mx-auto px-6 flex items-center justify-between h-12">
            <Link href="/" className="flex items-center gap-2 text-wall-text hover:text-[#818cf8] transition-colors">
              <Brain size={18} className="text-[#818cf8]" />
              <span className="text-sm font-semibold tracking-wide">
                <span className="text-[#818cf8]">认知破壁机</span>
                <span className="text-wall-dim text-[10px] ml-1 font-normal">V6.0</span>
              </span>
            </Link>
            <div className="flex items-center gap-1">
              <Link href="/" className="px-3 py-1.5 rounded-lg text-xs text-wall-muted hover:text-wall-text hover:bg-wall-surface transition-all">
                决策广场
              </Link>
              <Link href="/submit" className="px-3 py-1.5 rounded-lg text-xs bg-[#818cf8]/10 text-[#818cf8] border border-[#818cf8]/20 hover:bg-[#818cf8]/20 transition-all">
                + 提交决策
              </Link>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  )
}
