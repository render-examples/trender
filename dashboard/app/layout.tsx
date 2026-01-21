import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Trender - GitHub Trending Analytics',
  description: 'Discover trending GitHub repositories powered by Render Workflows',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-black relative">
          {/* Fixed top bar with solid background */}
          <div className="fixed top-0 left-0 right-0 z-50 bg-black border-b border-zinc-800">
            <div className="px-8 py-6">
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                Trender
              </h1>
            </div>
          </div>

          {/* Main Content */}
          <main className="pt-24 pb-12 relative z-10">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
