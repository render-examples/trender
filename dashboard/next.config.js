const path = require('path')
const dotenv = require('dotenv')

// Load .env from the root directory
dotenv.config({ path: path.resolve(__dirname, '../.env') })

/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
}

module.exports = nextConfig
