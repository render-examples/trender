import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Link from 'next/link'

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
        <div className="min-h-screen bg-gray-50">
          {/* Navigation */}
          <nav className="bg-white shadow-sm border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16">
                <div className="flex">
                  <Link href="/" className="flex items-center">
                    <span className="text-2xl font-bold text-blue-600">Trender</span>
                  </Link>
                  <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                    <Link
                      href="/"
                      className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 hover:text-blue-600"
                    >
                      Home
                    </Link>
                    <Link
                      href="/render"
                      className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-blue-600"
                    >
                      Render Showcase
                    </Link>
                    <Link
                      href="/language/Python"
                      className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-blue-600"
                    >
                      Languages
                    </Link>
                    <Link
                      href="/meta"
                      className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-blue-600"
                    >
                      Performance
                    </Link>
                    <Link
                      href="/for-marketing"
                      className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-blue-600"
                    >
                      Marketing
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </nav>

          {/* Main Content */}
          <main>{children}</main>

          {/* Footer */}
          <footer className="bg-white border-t border-gray-200 mt-12">
            <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
              <p className="text-center text-sm text-gray-500">
                Powered by{' '}
                <a
                  href="https://render.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800"
                >
                  Render Workflows
                </a>
              </p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  )
}
