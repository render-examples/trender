import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import Header from '@/components/Header'
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
          <Header />

          {/* Main Content */}
          <main className="pt-28 pb-12 relative z-10">
            {children}
          </main>

          {/* Footer */}
          <footer className="app-footer">
            <p className="footer-links">
              <a 
                href="https://x.com/render" 
                target="_blank" 
                rel="noopener noreferrer"
                className="footer-link"
              >
                X
              </a>
              &nbsp; &nbsp; &nbsp; &nbsp;
              <a 
                href="https://www.linkedin.com/company/render-com" 
                target="_blank" 
                rel="noopener noreferrer"
                className="footer-link"
              >
                LinkedIn
              </a>
              &nbsp; &nbsp; &nbsp; &nbsp;
              <a 
                href="https://github.com/render-examples/trender" 
                target="_blank" 
                rel="noopener noreferrer"
                className="footer-link"
              >
                GitHub
              </a>
            </p>
            <p className="footer-copyright">
              © Render {new Date().getFullYear()}
            </p>
          </footer>
        </div>
      </body>
    </html>
  )
}
