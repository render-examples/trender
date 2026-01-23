import type { Metadata } from 'next'
import Header from '@/components/Header'
import './globals.css'

export const metadata: Metadata = {
  title: 'Trender - GitHub Trending Analytics',
  description: 'Discover trending GitHub repositories powered by Render Workflows',
  icons: {
    icon: '/images/trend.png',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
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
            <p className="text-xs text-zinc-500 mt-2">
              <a 
                href="https://www.flaticon.com/free-icons/python" 
                title="python icons"
                target="_blank" 
                rel="noopener noreferrer"
                className="hover:text-zinc-400 transition-colors"
              >
                Python icons created by Freepik - Flaticon
              </a>
              {' • '}
              <a 
                href="https://www.flaticon.com/free-icons/typescript" 
                title="typescript icons"
                target="_blank" 
                rel="noopener noreferrer"
                className="hover:text-zinc-400 transition-colors"
              >
                Typescript icons created by Freepik - Flaticon
              </a>
              {' • '}
              <a 
                href="https://www.flaticon.com/free-icons/trend" 
                title="trend icons"
                target="_blank" 
                rel="noopener noreferrer"
                className="hover:text-zinc-400 transition-colors"
              >
                Trend icons created by Ferdinand - Flaticon
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
