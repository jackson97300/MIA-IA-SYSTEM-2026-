/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ['localhost'],
    unoptimized: true, // Pour Cloudflare Pages
  },
  output: 'export', // Static export pour Cloudflare Pages
  trailingSlash: true,
}

module.exports = nextConfig
