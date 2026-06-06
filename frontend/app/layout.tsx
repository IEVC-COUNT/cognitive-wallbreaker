import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '认知破壁机 · Cognitive Wallbreaker',
  description: 'AI 深度决策推演 — 击碎隐性假设，穿透认知盲区',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet" />
      </head>
      <body className="min-h-screen bg-wall-bg text-wall-text antialiased">
        {children}
      </body>
    </html>
  )
}
