import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        overflow: 'hidden',
        background: 'var(--bg-base)',
      }}
    >
      {/* Skip-to-content link */}
      <a
        href="#main-content"
        style={{
          position: 'absolute',
          left: '-9999px',
          top: 'auto',
          width: '1px',
          height: '1px',
          overflow: 'hidden',
          zIndex: 9999,
        }}
        onFocus={(e) => {
          e.currentTarget.style.position = 'fixed'
          e.currentTarget.style.left = '1rem'
          e.currentTarget.style.top = '1rem'
          e.currentTarget.style.width = 'auto'
          e.currentTarget.style.height = 'auto'
          e.currentTarget.style.padding = '0.5rem 1rem'
          e.currentTarget.style.background = 'var(--accent-crimson)'
          e.currentTarget.style.color = 'var(--text-cream)'
          e.currentTarget.style.borderRadius = '4px'
          e.currentTarget.style.fontFamily = "'Crimson Pro', serif"
          e.currentTarget.style.fontSize = '14px'
          e.currentTarget.style.textDecoration = 'none'
          e.currentTarget.style.zIndex = '9999'
        }}
        onBlur={(e) => {
          e.currentTarget.style.position = 'absolute'
          e.currentTarget.style.left = '-9999px'
          e.currentTarget.style.width = '1px'
          e.currentTarget.style.height = '1px'
        }}
      >
        跳到主要内容
      </a>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
          onKeyDown={(e) => e.key === 'Escape' && setSidebarOpen(false)}
          tabIndex={0}
          role="button"
          aria-label="关闭菜单"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(18,17,15,0.6)',
            zIndex: 40,
          }}
        />
      )}

      {/* Sidebar — desktop: sticky; mobile: drawer */}
      <div
        className="sidebar-drawer"
        style={{
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 50,
          transform: sidebarOpen ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 200ms ease-out',
        }}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Desktop sidebar always visible */}
      <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0, flex: 1 }}>
        {/* Mobile header with hamburger */}
        <div
          style={{
            display: 'none',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '0.875rem 1rem',
            borderBottom: '1px solid var(--border)',
            background: 'var(--bg-raised)',
          }}
          className="mobile-header"
        >
          <button
            onClick={() => setSidebarOpen(true)}
            aria-label="打开菜单"
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '4px',
              fontSize: '20px',
              lineHeight: 1,
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <span
            style={{
              fontFamily: "'Playfair Display', serif",
              fontSize: '14px',
              color: 'var(--text-cream)',
              fontWeight: 500,
            }}
          >
            Murder Wizard
          </span>
        </div>

        <main
          id="main-content"
          style={{
            flex: 1,
            overflowY: 'auto',
            background: 'var(--bg-base)',
          }}
        >
          <Outlet />
        </main>
      </div>

      <style>{`
        @media (max-width: 768px) {
          .mobile-header { display: flex !important; }
        }
        @media (min-width: 769px) {
          .sidebar-drawer { position: static !important; transform: none !important; }
          .sidebar-overlay { display: none !important; }
        }
      `}</style>
    </div>
  )
}
