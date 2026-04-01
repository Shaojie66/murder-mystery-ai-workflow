import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getProject } from '../api/projects'
import { getFile } from '../api/files'
import { useProjectStore } from '../stores/projectStore'
import type { ProjectDetails } from '../types/api'
import VisualGallery from '../components/visual/VisualGallery'

const STAGE_LABELS: Record<string, { label: string; next: number | null }> = {
  idle: { label: '未开始', next: 1 },
  stage_1_mechanism: { label: '机制设计', next: 2 },
  stage_2_script: { label: '剧本创作', next: 3 },
  stage_3_visual: { label: '视觉物料', next: 4 },
  stage_4_test: { label: '用户测试', next: 5 },
  stage_5_commercial: { label: '商业化', next: 6 },
  stage_6_print: { label: '印刷生产', next: 7 },
  stage_7_promo: { label: '宣发内容', next: 8 },
  stage_8_community: { label: '社区运营', next: null },
}

const PHASE_LABELS = ['', '机制设计', '剧本创作', '视觉物料', '用户测试', '商业化', '印刷生产', '宣发内容', '社区运营']

export default function ProjectView() {
  const { name } = useParams<{ name: string }>()
  const { setCurrentProject } = useProjectStore()
  const [project, setProject] = useState<ProjectDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [imagePrompts, setImagePrompts] = useState<string | null>(null)

  useEffect(() => {
    if (!name) return
    setLoading(true)
    getProject(decodeURIComponent(name))
      .then((p) => { setProject(p); setCurrentProject(p) })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '加载失败'))
      .finally(() => setLoading(false))

    // Fetch image-prompts.md if it exists
    getFile(decodeURIComponent(name), 'image-prompts.md')
      .then((f) => setImagePrompts(f.content))
      .catch(() => setImagePrompts(null))
  }, [name])

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <span style={{ color: 'var(--text-faint)', fontFamily: "'Crimson Pro', serif", fontStyle: 'italic' }}>
          加载中...
        </span>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div style={{ padding: '3rem', maxWidth: '640px', margin: '0 auto' }}>
        <div
          style={{
            padding: '1.5rem',
            border: '1px solid var(--output-error-border)',
            background: 'var(--output-error-bg)',
            color: 'var(--output-error)',
            fontFamily: "'Crimson Pro', serif",
          }}
        >
          {error || '项目不存在'}
        </div>
      </div>
    )
  }

  const stageInfo = STAGE_LABELS[project.current_stage] || STAGE_LABELS['unknown']
  const nextStage = stageInfo.next

  // Parse current stage number
  const stageMatch = project.current_stage.match(/stage_(\d+)/)
  const currentPhaseNum = stageMatch ? parseInt(stageMatch[1]) : 0

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      {/* Page header */}
      <header
        style={{
          padding: '3rem 3rem 2rem',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-base)',
        }}
      >
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          {/* Breadcrumb */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              marginBottom: '1.5rem',
              fontFamily: "'Crimson Pro', serif",
              fontSize: '13px',
              color: 'var(--text-faint)',
            }}
          >
            <Link to="/" style={{ color: 'var(--text-faint)', textDecoration: 'none' }}>
              项目列表
            </Link>
            <span>→</span>
            <span style={{ color: 'var(--text-muted)' }}>{project.name}</span>
          </div>

          {/* Title block */}
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '2rem' }}>
            <div style={{ flex: 1 }}>
              <div className="label" style={{ marginBottom: '0.75rem', color: 'var(--accent-crimson)' }}>
                <span className="accent-rule" style={{ background: 'var(--accent-crimson)' }} />
                {project.story_type} · {project.is_prototype ? '原型模式' : '完整模式'}
              </div>
              <h1
                style={{
                  fontFamily: "'Playfair Display', serif",
                  fontSize: 'clamp(2rem, 4vw, 3rem)',
                  fontWeight: 500,
                  color: 'var(--text-cream)',
                  letterSpacing: '-0.02em',
                  lineHeight: 1.1,
                  marginBottom: '0.5rem',
                }}
              >
                {project.name}
              </h1>
              <p
                style={{
                  fontFamily: "'Crimson Pro', serif",
                  fontSize: '16px',
                  color: 'var(--text-muted)',
                  fontStyle: 'italic',
                }}
              >
                当前阶段：{stageInfo.label}
              </p>
            </div>

            {nextStage && (
              <Link
                to={`/projects/${encodeURIComponent(project.name)}/phase/${nextStage}`}
                className="btn-primary"
                style={{ flexShrink: 0, marginTop: '0.5rem' }}
              >
                ▶ {PHASE_LABELS[nextStage]}
              </Link>
            )}
          </div>
        </div>
      </header>

      <div style={{ maxWidth: '900px', margin: '0 auto', padding: '3rem' }}>
        {/* 8-Phase progress — editorial timeline */}
        <section style={{ marginBottom: '3rem' }}>
          <div className="label" style={{ marginBottom: '1.5rem', color: 'var(--text-faint)' }}>
            创作进度
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))',
              gap: '1px',
              background: 'var(--border-subtle)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            {PHASE_LABELS.slice(1).map((label, i) => {
              const phaseNum = i + 1
              const isDone = currentPhaseNum > phaseNum
              const isCurrent = currentPhaseNum === phaseNum

              return (
                <div
                  key={phaseNum}
                  style={{
                    padding: '1rem 0.75rem',
                    background: isDone
                      ? 'rgba(155,28,28,0.08)'
                      : isCurrent
                      ? 'rgba(180,83,9,0.1)'
                      : 'var(--bg-raised)',
                    textAlign: 'center',
                    position: 'relative',
                  }}
                >
                  <div
                    style={{
                      fontFamily: "'Playfair Display', serif",
                      fontSize: '11px',
                      color: isDone
                        ? 'var(--accent-crimson)'
                        : isCurrent
                        ? 'var(--accent-gold)'
                        : 'var(--text-faint)',
                      marginBottom: '0.25rem',
                      fontWeight: isCurrent ? 600 : 400,
                    }}
                  >
                    {isDone ? '✓' : isCurrent ? '→' : '·'}
                  </div>
                  <div
                    style={{
                      fontFamily: "'Crimson Pro', serif",
                      fontSize: '12px',
                      color: isDone
                        ? 'var(--accent-crimson)'
                        : isCurrent
                        ? 'var(--text-cream)'
                        : 'var(--text-faint)',
                      letterSpacing: '-0.01em',
                      lineHeight: 1.2,
                    }}
                  >
                    {label}
                  </div>
                  <div
                    style={{
                      fontFamily: "'Crimson Pro', serif",
                      fontSize: '10px',
                      color: 'var(--text-faint)',
                      marginTop: '2px',
                    }}
                  >
                    阶段{phaseNum}
                  </div>
                  {isCurrent && (
                    <div
                      style={{
                        position: 'absolute',
                        bottom: 0,
                        left: 0,
                        right: 0,
                        height: '2px',
                        background: 'var(--accent-gold)',
                      }}
                    />
                  )}
                </div>
              )
            })}
          </div>
        </section>

        {/* Two-column: artifacts + quick actions */}
        <div
          className="project-columns"
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 280px',
            gap: '3rem',
            alignItems: 'start',
          }}
        >
          {/* Artifact files */}
          <section>
            <div className="label" style={{ marginBottom: '1rem', color: 'var(--text-faint)' }}>
              产物文件
            </div>

            <div
              style={{
                border: '1px solid var(--border)',
                background: 'var(--bg-raised)',
              }}
            >
              {Object.entries(project.artifacts).map(([fname, info], idx) => (
                <div
                  key={fname}
                  style={{
                    padding: '0.875rem 1rem',
                    borderBottom: idx < Object.keys(project.artifacts).length - 1 ? '1px solid var(--border-subtle)' : 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '1rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: 0 }}>
                    <span
                      style={{
                        fontFamily: "'Crimson Pro', serif",
                        fontSize: '13px',
                        color: info.exists ? 'var(--text-muted)' : 'var(--text-faint)',
                        flexShrink: 0,
                      }}
                    >
                      {fname.endsWith('.md') ? '§' : fname.endsWith('.pdf') ? '◻' : '▤'}
                    </span>
                    <span
                      style={{
                        fontFamily: "'Crimson Pro', serif",
                        fontSize: '15px',
                        color: info.exists ? 'var(--text-cream)' : 'var(--text-faint)',
                        textDecoration: info.exists ? 'none' : 'line-through',
                      }}
                    >
                      {fname}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
                    {info.size && (
                      <span
                        style={{
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: '11px',
                          color: 'var(--text-faint)',
                        }}
                      >
                        {(info.size / 1024).toFixed(1)} KB
                      </span>
                    )}
                    {info.exists ? (
                      <Link
                        to={`/projects/${encodeURIComponent(project.name)}/files/${fname}`}
                        style={{
                          fontFamily: "'Crimson Pro', serif",
                          fontSize: '12px',
                          color: 'var(--accent-gold)',
                          textDecoration: 'none',
                        }}
                      >
                        查看 →
                      </Link>
                    ) : (
                      <span style={{ fontFamily: "'Crimson Pro', serif", fontSize: '12px', color: 'var(--text-faint)' }}>
                        未生成
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Quick actions */}
          <section>
            <div className="label" style={{ marginBottom: '1rem', color: 'var(--text-faint)' }}>
              快捷操作
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
              {[
                { to: `/projects/${encodeURIComponent(project.name)}/matrix`, label: '信息矩阵', icon: '□' },
                { to: `/projects/${encodeURIComponent(project.name)}/audit`, label: '穿帮审计', icon: '◻' },
                { to: `/projects/${encodeURIComponent(project.name)}/costs`, label: '消耗统计', icon: '◎' },
                { to: `/projects/${encodeURIComponent(project.name)}/phase/1`, label: '运行阶段', icon: '▸' },
              ].map(({ to, label, icon }) => (
                <Link
                  key={to}
                  to={to}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    padding: '0.875rem 1rem',
                    background: 'var(--bg-raised)',
                    border: '1px solid var(--border)',
                    textDecoration: 'none',
                    transition: 'all 150ms',
                    color: 'var(--text-muted)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--accent-gold-muted)'
                    e.currentTarget.style.color = 'var(--text-cream)'
                    e.currentTarget.style.paddingLeft = '1.25rem'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'var(--border)'
                    e.currentTarget.style.color = 'var(--text-muted)'
                    e.currentTarget.style.paddingLeft = '1rem'
                  }}
                >
                  <span
                    style={{
                      fontFamily: "'Crimson Pro', serif",
                      fontSize: '16px',
                      color: 'var(--accent-gold)',
                      width: '16px',
                      textAlign: 'center',
                    }}
                  >
                    {icon}
                  </span>
                  <span
                    style={{
                      fontFamily: "'Crimson Pro', serif",
                      fontSize: '15px',
                      letterSpacing: '0.01em',
                    }}
                  >
                    {label}
                  </span>
                </Link>
              ))}
            </div>

            {/* Expand prompt */}
            {project.can_expand && (
              <div
                style={{
                  marginTop: '1.5rem',
                  padding: '1.25rem',
                  border: '1px solid var(--accent-gold-muted)',
                  background: 'rgba(180,83,9,0.06)',
                }}
              >
                <div
                  style={{
                    fontFamily: "'Playfair Display', serif",
                    fontSize: '14px',
                    color: 'var(--accent-gold)',
                    marginBottom: '0.375rem',
                  }}
                >
                  原型扩写
                </div>
                <p
                  style={{
                    fontFamily: "'Crimson Pro', serif",
                    fontSize: '13px',
                    color: 'var(--text-muted)',
                    fontStyle: 'italic',
                    marginBottom: '1rem',
                    lineHeight: 1.5,
                  }}
                >
                  当前为原型模式（2人），可扩写为完整6人版本
                </p>
                <Link
                  to={`/projects/${encodeURIComponent(project.name)}/phase/expand`}
                  className="btn-secondary"
                  style={{ fontSize: '13px' }}
                >
                  扩写为完整版 →
                </Link>
              </div>
            )}
          </section>
        </div>

        {/* Visual Gallery - only show when phase >= 3 */}
        {currentPhaseNum >= 3 && (
          <section style={{ marginTop: '2rem' }}>
            <VisualGallery prompts={imagePrompts || undefined} />
          </section>
        )}
      </div>
    </div>
  )
}
