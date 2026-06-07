/** @type {import('next').NextConfig} */
const API_HOST = process.env.NEXT_API_HOST || '127.0.0.1'
const API_PORT = process.env.NEXT_API_PORT || '8922'

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `http://${API_HOST}:${API_PORT}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
