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
            ☰
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
