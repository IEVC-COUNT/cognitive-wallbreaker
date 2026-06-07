import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './hooks/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        wall: {
          bg: '#080c14',
          surface: '#0f1624',
          border: '#1e2a3a',
          accent: '#64748b',
          glow: '#818cf8',
          text: '#e2e8f0',
          muted: '#64748b',
          dim: '#334155',
        }
      },
      fontFamily: {
        sans: ['Inter', 'Noto Sans SC', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'breathe': 'breathe 4s ease-in-out infinite',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'scan': 'scan 2s ease-in-out infinite',
      },
      keyframes: {
        breathe: {
          '0%, 100%': { boxShadow: '0 0 15px rgba(129, 140, 248, 0.15)' },
          '50%': { boxShadow: '0 0 30px rgba(129, 140, 248, 0.35), 0 0 60px rgba(129, 140, 248, 0.1)' },
        },
        scan: {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}

export default config
