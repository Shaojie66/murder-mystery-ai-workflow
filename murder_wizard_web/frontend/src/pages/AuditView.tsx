import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getProject } from '../api/projects'
import { request } from '../api/client'
import type { ProjectDetails } from '../types/api'

export default function AuditView() {
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const projectName = decodeURIComponent(name || '')
  const [report, setReport] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [project, setProject] = useState<ProjectDetails | null>(null)

  useEffect(() => {
    if (!projectName) return
    Promise.all([
      request<{ content: string }>(`/projects/${encodeURIComponent(projectName)}/audit/report`),
      getProject(projectName),
    ])
      .then(([reportData, projectData]) => {
        setReport(reportData.content)
        setProject(projectData)
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : '加载失败')
      })
      .finally(() => setLoading(false))
  }, [projectName])

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <span style={{ color: 'var(--text-faint)', fontFamily: "'Crimson Pro', serif", fontStyle: 'italic' }}>
          加载中...
        </span>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      {/* Header */}
      <header
        style={{
          padding: '2rem 3rem',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-raised)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            onClick={() => navigate(`/projects/${encodeURIComponent(projectName)}`)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-faint)',
              cursor: 'pointer',
              fontFamily: "'Crimson Pro', serif",
              fontSize: '14px',
              padding: 0,
              transition: 'color 150ms',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-cream)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-faint)')}
          >
            ← 返回
          </button>
          <span style={{ color: 'var(--border)', fontSize: '12px' }}>/</span>
          <div>
            <div className="label" style={{ marginBottom: '0.25rem', color: 'var(--accent-crimson)' }}>
              <span className="accent-rule" style={{ background: 'var(--accent-crimson)' }} />
              Audit Report
            </div>
            <h1
              style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: '1.5rem',
                fontWeight: 500,
                color: 'var(--text-cream)',
                letterSpacing: '-0.01em',
              }}
            >
              穿帮审计报告
            </h1>
          </div>
        </div>

        <Link
          to={`/projects/${encodeURIComponent(projectName)}/phase/audit`}
          className="btn-primary"
          style={{ fontSize: '13px' }}
          aria-label="重新运行审计"
        >
          ↻ 重新运行审计
        </Link>
      </header>

      {/* Content */}
      <div style={{ maxWidth: '760px', margin: '0 auto', padding: '3rem' }}>
        {error ? (
          <div>
            <div
              style={{
                padding: '1.5rem',
                border: '1px solid var(--output-error-border)',
                background: 'var(--output-error-bg)',
                color: 'var(--output-error)',
                fontFamily: "'Crimson Pro', serif",
                fontSize: '15px',
                marginBottom: '1.5rem',
              }}
            >
              {error}
            </div>
            {project?.can_audit ? (
              <Link to={`/projects/${encodeURIComponent(projectName)}/phase/audit`} className="btn-primary" aria-label="运行审计">
                运行审计
              </Link>
            ) : (
              <p
                style={{
                  fontFamily: "'Crimson Pro', serif",
                  fontSize: '15px',
                  color: 'var(--text-muted)',
                  fontStyle: 'italic',
                }}
              >
                请先运行阶段2（剧本创作）生成角色剧本后再进行审计
              </p>
            )}
          </div>
        ) : report ? (
          <pre
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '13px',
              lineHeight: 1.8,
              color: 'var(--text-muted)',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              background: 'var(--bg-raised)',
              border: '1px solid var(--border)',
              padding: '2rem',
            }}
          >
            {report}
          </pre>
        ) : (
          <div style={{ textAlign: 'center', paddingTop: '5rem' }}>
            <div
              style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: '3rem',
                color: 'var(--border)',
                marginBottom: '1rem',
                lineHeight: 1,
              }}
            >
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" style={{ color: 'var(--border)' }} aria-hidden="true">
                <path d="M9 12l2 2 4-4"/>
                <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            </div>
            <h2
              style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: '1.5rem',
                fontWeight: 500,
                color: 'var(--text-cream)',
                marginBottom: '0.5rem',
              }}
            >
              暂无审计报告
            </h2>
            <p
              style={{
                fontFamily: "'Crimson Pro', serif",
                fontSize: '16px',
                color: 'var(--text-muted)',
                fontStyle: 'italic',
                marginBottom: '2rem',
              }}
            >
              运行穿帮审计来检查剧本的一致性
            </p>
            <Link to={`/projects/${encodeURIComponent(projectName)}/phase/audit`} className="btn-primary">
              运行审计
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
