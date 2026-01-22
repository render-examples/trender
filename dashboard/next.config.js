const path = require('path')
const dotenv = require('dotenv')

// Load .env from the root directory
dotenv.config({ path: path.resolve(__dirname, '../.env') })

/** @type {import('next').NextConfig} */
const nextConfig = {
  // appDir is now stable in Next.js 14+, no need for experimental flag
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.resolve(__dirname, './')
    }
    return config
  }
}

module.exports = nextConfig
