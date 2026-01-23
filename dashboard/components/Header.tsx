'use client'

import Image from 'next/image'
import './Header.css'

export default function Header() {
  return (
    <header className="app-header">
      <div className="header-content">
        <div className="header-left">
          <h1 className="trender-title">Trender</h1>
        </div>
        <div className="header-right">
          <a
            href="https://render.com"
            target="_blank"
            rel="noopener noreferrer"
            className="render-logo-link"
            aria-label="Visit Render.com"
          >
            <span className="render-powered-text" data-mobile-text="DEPLOYED ON">DEPLOYED ON</span>
            <Image
              src="/images/render-logo.png"
              alt="Render"
              width={88}
              height={22}
              className="render-logo"
            />
          </a>
        </div>
      </div>
    </header>
  )
}
