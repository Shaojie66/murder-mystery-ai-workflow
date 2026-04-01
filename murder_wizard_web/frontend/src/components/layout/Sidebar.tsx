import { Link, useLocation } from 'react-router-dom'
import { useProjectStore } from '../../stores/projectStore'

const STAGE_LABELS: Record<string, string> = {
  stage_1_mechanism: '机制设计',
  stage_2_script: '剧本创作',
  stage_3_visual: '视觉物料',
  stage_4_test: '用户测试',
  stage_5_commercial: '商业化',
  stage_6_print: '印刷生产',
  stage_7_promo: '宣发内容',
  stage_8_community: '社区运营',
  idle: '未开始',
  unknown: '未知',
}

type SidebarProps = { onClose?: () => void }

export default function Sidebar({ onClose }: SidebarProps) {
  const location = useLocation()
  const { currentProject } = useProjectStore()
  const isProjectPage = location.pathname.startsWith('/projects/')

  return (
    <aside
      style={{
        width: 'var(--sidebar-width, 220px)',
        minWidth: 'var(--sidebar-width, 220px)',
        background: 'var(--bg-raised)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        position: 'sticky',
        top: 0,
      }}
    >
      {/* Masthead */}
      <div style={{ padding: '1.75rem 1.5rem 1.5rem', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
        <Link to="/" style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', flex: 1 }}>
          {/* Typographic logo mark */}
          <div
            style={{
              width: '32px',
              height: '32px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid var(--border)',
              fontSize: '11px',
              fontFamily: "'Playfair Display', serif",
              fontWeight: 600,
              color: 'var(--text-faint)',
              letterSpacing: '0.05em',
              flexShrink: 0,
              marginTop: '2px',
            }}
          >
            MW
          </div>
          <div>
            <div
              style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: '15px',
                fontWeight: 500,
                color: 'var(--text-cream)',
                letterSpacing: '-0.01em',
                lineHeight: 1.2,
              }}
            >
              Murder Wizard
            </div>
            <div
              style={{
                fontFamily: "'Crimson Pro', serif",
                fontSize: '11px',
                color: 'var(--text-faint)',
                marginTop: '2px',
                letterSpacing: '0.02em',
              }}
            >
              剧本杀创作工作流
            </div>
          </div>
        </Link>
        {onClose && (
          <button
            onClick={onClose}
            aria-label="关闭菜单"
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-faint)',
              cursor: 'pointer',
              padding: '2px 4px',
              lineHeight: 1,
              flexShrink: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              <line x1="4" y1="4" x2="12" y2="12" />
              <line x1="12" y1="4" x2="4" y2="12" />
            </svg>
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, padding: '1.5rem 0', overflowY: 'auto' }}>
        {/* Main section */}
        <div style={{ marginBottom: '1.5rem' }}>
          <div
            className="label"
            style={{ padding: '0 1.5rem', marginBottom: '0.5rem', color: 'var(--text-faint)' }}
          >
            工作台
          </div>

          <NavItem
            href="/"
            isActive={location.pathname === '/'}
            icon={
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                <rect x="1" y="1" width="5" height="5" rx="0.5" />
                <rect x="8" y="1" width="5" height="5" rx="0.5" />
                <rect x="1" y="8" width="5" height="5" rx="0.5" />
                <rect x="8" y="8" width="5" height="5" rx="0.5" />
              </svg>
            }
          >
            项目列表
          </NavItem>
        </div>

        {/* Project section */}
        {isProjectPage && currentProject && (
          <>
            <div style={{ marginBottom: '1.5rem' }}>
              <div
                className="label"
                style={{ padding: '0 1.5rem', marginBottom: '0.5rem', color: 'var(--text-faint)' }}
              >
                当前项目
              </div>

              <NavItem
                href={`/projects/${currentProject.name}`}
                isActive={location.pathname === `/projects/${currentProject.name}`}
                icon={
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M1 10.5V4a1 1 0 0 1 1-1h3l2-2h4a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1z" />
                  </svg>
                }
              >
                {currentProject.name}
                {currentProject.is_prototype && (
                  <span
                    style={{
                      marginLeft: 'auto',
                      fontSize: '9px',
                      fontFamily: "'Crimson Pro', serif",
                      letterSpacing: '0.08em',
                      textTransform: 'uppercase',
                      color: 'var(--accent-gold)',
                      background: 'rgba(180,83,9,0.12)',
                      padding: '1px 5px',
                      borderRadius: '2px',
                    }}
                  >
                    原型
                  </span>
                )}
              </NavItem>

              <NavItem
                href={`/projects/${currentProject.name}/phase/1`}
                isActive={location.pathname.includes('/phase/')}
                icon={
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <polygon points="4,1 12,7 4,13" />
                  </svg>
                }
              >
                运行阶段
              </NavItem>

              <NavItem
                href={`/projects/${currentProject.name}/matrix`}
                isActive={location.pathname.includes('/matrix')}
                icon={
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <rect x="1" y="1" width="12" height="12" rx="0.5" />
                    <line x1="5" y1="1" x2="5" y2="13" />
                    <line x1="9" y1="1" x2="9" y2="13" />
                    <line x1="1" y1="5" x2="13" y2="5" />
                    <line x1="1" y1="9" x2="13" y2="9" />
                  </svg>
                }
              >
                信息矩阵
              </NavItem>

              <NavItem
                href={`/projects/${currentProject.name}/audit`}
                isActive={location.pathname.includes('/audit')}
                icon={
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="7" cy="7" r="5.5" />
                    <path d="M4.5 7l1.5 1.5L9.5 5" />
                  </svg>
                }
              >
                穿帮审计
              </NavItem>

              <NavItem
                href={`/projects/${currentProject.name}/costs`}
                isActive={location.pathname.includes('/costs')}
                icon={
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="7" cy="7" r="5.5" />
                    <path d="M7 4v3.5l2 1.5" />
                  </svg>
                }
              >
                消耗统计
              </NavItem>
            </div>

            {/* Stage progress */}
            <div style={{ padding: '0 1.5rem' }}>
              <div
                className="label"
                style={{ marginBottom: '0.75rem', color: 'var(--text-faint)' }}
              >
                当前阶段
              </div>
              <div
                style={{
                  fontFamily: "'Crimson Pro', serif",
                  fontSize: '13px',
                  color: 'var(--text-muted)',
                  fontStyle: 'italic',
                  paddingLeft: '0',
                }}
              >
                {STAGE_LABELS[currentProject.current_stage] || currentProject.current_stage}
              </div>
            </div>
          </>
        )}
      </nav>

      {/* Footer */}
      <div
        style={{
          padding: '1rem 1.5rem',
          borderTop: '1px solid var(--border-subtle)',
        }}
      >
        <div
          style={{
            fontFamily: "'Crimson Pro', serif",
            fontSize: '11px',
            color: 'var(--text-faint)',
            letterSpacing: '0.03em',
          }}
        >
          v0.6.0 · Murder Wizard
        </div>
      </div>
    </aside>
  )
}

function NavItem({
  href,
  isActive,
  icon,
  children,
}: {
  href: string
  isActive: boolean
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <Link
      to={href}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.625rem',
        padding: '0.5rem 1.5rem',
        fontSize: '14px',
        fontFamily: "'Crimson Pro', serif",
        color: isActive ? 'var(--text-cream)' : 'var(--text-muted)',
        background: isActive ? 'var(--cream-subtle)' : 'transparent',
        borderLeft: isActive ? '2px solid var(--accent-crimson)' : '2px solid transparent',
        transition: 'all 150ms',
        textDecoration: 'none',
        letterSpacing: '0.01em',
      }}
      onMouseEnter={(e) => {
        if (!isActive) {
          e.currentTarget.style.color = 'var(--text-cream)'
          e.currentTarget.style.background = 'var(--cream-subtle)'
        }
      }}
      onMouseLeave={(e) => {
        if (!isActive) {
          e.currentTarget.style.color = 'var(--text-muted)'
          e.currentTarget.style.background = 'transparent'
        }
      }}
    >
      <span aria-hidden="true" style={{ color: isActive ? 'var(--accent-crimson)' : 'var(--text-faint)', flexShrink: 0 }}>
        {icon}
      </span>
      {children}
    </Link>
  )
}
