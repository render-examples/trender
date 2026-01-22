/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
        },
      },
      fontFamily: {
        sans: ['SF Mono', 'Menlo', 'Monaco', 'Consolas', 'Courier New', 'monospace'],
        mono: ['SF Mono', 'Menlo', 'Monaco', 'Consolas', 'Courier New', 'monospace'],
      },
      letterSpacing: {
        'code': '0.4px',
      },
    },
  },
  plugins: [],
}
