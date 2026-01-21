const path = require('path')
const dotenv = require('dotenv')

// Load .env from the root directory
dotenv.config({ path: path.resolve(__dirname, '../.env') })

/** @type {import('next').NextConfig} */
const nextConfig = {
  // appDir is now stable in Next.js 14+, no need for experimental flag
}

module.exports = nextConfig
