import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getProject } from '../api/projects'
import { getFile } from '../api/files'
import { useProjectStore } from '../stores/projectStore'
import type { ProjectDetails } from '../types/api'
import VisualGallery from '../components/visual/VisualGallery'

// B1 Publication Classic — warm cream palette
const B1 = {
  bgPage: '#F8F4EE',
  bgRaised: '#FFFFFF',
  bgSection: '#F0EBE3',
  border: '#E5DDD3',
  textPrimary: '#1C1917',
  textMuted: '#78716C',
  textFaint: '#A8A29E',
  crimson: '#9B1C1C',
  gold: '#C77A08',
  goldSubtle: 'rgba(199,122,8,0.08)',
}

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
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: B1.bgPage }}>
        <span style={{ color: B1.textFaint, fontFamily: "'Crimson Pro', serif", fontStyle: 'italic', fontSize: '15px' }}>
          加载中...
        </span>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div style={{ padding: '3rem', maxWidth: '640px', margin: '0 auto', background: B1.bgPage, minHeight: '100vh' }}>
        <div
          style={{
            padding: '1.5rem',
            border: `1px solid ${B1.border}`,
            background: B1.bgRaised,
            color: B1.crimson,
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
    <div style={{ minHeight: '100vh', background: B1.bgPage }}>
      {/* Page header — B1 Publication Classic */}
      <header
        style={{
          padding: '2.5rem 3rem 2rem',
          borderBottom: `1px solid ${B1.border}`,
          background: B1.bgPage,
        }}
      >
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          {/* Breadcrumb */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              marginBottom: '1.75rem',
              fontFamily: "'Crimson Pro', serif",
              fontSize: '12px',
              color: B1.textFaint,
              letterSpacing: '0.03em',
            }}
          >
            <Link to="/" style={{ color: B1.textFaint, textDecoration: 'none' }}>
              项目列表
            </Link>
            <span style={{ color: B1.textFaint }}>→</span>
            <span style={{ color: B1.textMuted }}>{project.name}</span>
          </div>

          {/* Title block */}
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '2rem' }}>
            <div style={{ flex: 1 }}>
              {/* Story type badge */}
              <div
                style={{
                  fontFamily: "'Crimson Pro', serif",
                  fontSize: '12px',
                  color: B1.crimson,
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase',
                  marginBottom: '0.75rem',
                  fontWeight: 500,
                }}
              >
                {project.story_type} · {project.is_prototype ? '原型模式' : '完整模式'}
              </div>

              <h1
                style={{
                  fontFamily: "'Playfair Display', serif",
                  fontSize: 'clamp(2.2rem, 4vw, 3rem)',
                  fontWeight: 500,
                  color: B1.textPrimary,
                  letterSpacing: '-0.03em',
                  lineHeight: 1.1,
                  marginBottom: '0.5rem',
                }}
              >
                {project.name}
              </h1>
              <p
                style={{
                  fontFamily: "'Crimson Pro', serif",
                  fontSize: '15px',
                  color: B1.textMuted,
                  fontStyle: 'italic',
                  marginBottom: '0',
                }}
              >
                当前阶段：{stageInfo.label}
              </p>
            </div>

            {nextStage && (
              <Link
                to={`/projects/${encodeURIComponent(project.name)}/phase/${nextStage}`}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.5rem 1rem',
                  background: B1.crimson,
                  color: '#F5F0E8',
                  fontFamily: "'Crimson Pro', serif",
                  fontSize: '13px',
                  textDecoration: 'none',
                  flexShrink: 0,
                  marginTop: '0.25rem',
                  transition: 'background 150ms',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = '#7F1717')}
                onMouseLeave={(e) => (e.currentTarget.style.background = B1.crimson)}
              >
                ▶ {PHASE_LABELS[nextStage]}
              </Link>
            )}
          </div>
        </div>
      </header>

      <div style={{ maxWidth: '900px', margin: '0 auto', padding: '2.5rem 3rem' }}>
        {/* 8-Phase progress — B1 editorial timeline */}
        <section style={{ marginBottom: '3rem' }}>
          {/* Section label */}
          <div
            style={{
              fontFamily: "'Crimson Pro', serif",
              fontSize: '11px',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: B1.textFaint,
              marginBottom: '1rem',
            }}
          >
            创作进度
          </div>

          {/* Phase bar — B1: icon-based, equal segments, no grid lines */}
          <div
            style={{
              display: 'flex',
              gap: 0,
              border: `1px solid ${B1.border}`,
              background: B1.bgRaised,
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
                    flex: 1,
                    padding: '0.6rem 0.5rem',
                    textAlign: 'center',
                    borderRight: phaseNum < 8 ? `1px solid ${B1.border}` : 'none',
                    background: isDone
                      ? 'rgba(155,28,28,0.07)'
                      : isCurrent
                      ? 'rgba(199,122,8,0.09)'
                      : B1.bgRaised,
                  }}
                >
                  {/* Phase icon */}
                  <div
                    style={{
                      fontFamily: "'Playfair Display', serif",
                      fontSize: '13px',
                      color: isDone
                        ? B1.crimson
                        : isCurrent
                        ? B1.gold
                        : B1.border,
                      marginBottom: '2px',
                    }}
                  >
                    {isDone ? '✓' : isCurrent ? '→' : '·'}
                  </div>
                  {/* Phase label */}
                  <div
                    style={{
                      fontFamily: "'Crimson Pro', serif",
                      fontSize: '11px',
                      color: isDone
                        ? B1.crimson
                        : isCurrent
                        ? B1.textPrimary
                        : B1.textFaint,
                      letterSpacing: '-0.01em',
                      lineHeight: 1.2,
                    }}
                  >
                    {label}
                  </div>
                </div>
              )
            })}
          </div>
        </section>

        {/* Two-column: artifacts + quick actions */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 220px',
            gap: '2rem',
            alignItems: 'start',
          }}
        >
          {/* Artifact files */}
          <section>
            {/* Section label */}
            <div
              style={{
                fontFamily: "'Crimson Pro', serif",
                fontSize: '11px',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: B1.textFaint,
                marginBottom: '0.75rem',
              }}
            >
              产物文件
            </div>

            <div
              style={{
                border: `1px solid ${B1.border}`,
                background: B1.bgRaised,
              }}
            >
              {Object.entries(project.artifacts).map(([fname, info], idx) => (
                <div
                  key={fname}
                  style={{
                    padding: '0.65rem 0.875rem',
                    borderBottom: idx < Object.keys(project.artifacts).length - 1 ? `1px solid ${B1.border}` : 'none',
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
                        fontSize: '14px',
                        color: info.exists ? B1.textMuted : B1.textFaint,
                        flexShrink: 0,
                      }}
                    >
                      {fname.endsWith('.md') ? '§' : fname.endsWith('.pdf') ? '◻' : '▤'}
                    </span>
                    <span
                      style={{
                        fontFamily: "'Crimson Pro', serif",
                        fontSize: '14px',
                        color: info.exists ? B1.textPrimary : B1.textFaint,
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
                          fontSize: '10px',
                          color: B1.textFaint,
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
                          color: B1.gold,
                          textDecoration: 'none',
                        }}
                      >
                        查看 →
                      </Link>
                    ) : (
                      <span style={{ fontFamily: "'Crimson Pro', serif", fontSize: '12px', color: B1.textFaint }}>
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
            {/* Section label */}
            <div
              style={{
                fontFamily: "'Crimson Pro', serif",
                fontSize: '11px',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: B1.textFaint,
                marginBottom: '0.75rem',
              }}
            >
              快捷操作
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
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
                    gap: '0.625rem',
                    padding: '0.65rem 0.875rem',
                    background: B1.bgRaised,
                    border: `1px solid ${B1.border}`,
                    textDecoration: 'none',
                    transition: 'all 150ms',
                    color: B1.textMuted,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = B1.gold
                    e.currentTarget.style.color = B1.textPrimary
                    e.currentTarget.style.paddingLeft = '1.125rem'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = B1.border
                    e.currentTarget.style.color = B1.textMuted
                    e.currentTarget.style.paddingLeft = '0.875rem'
                  }}
                >
                  <span
                    style={{
                      fontFamily: "'Crimson Pro', serif",
                      fontSize: '15px',
                      color: B1.gold,
                      width: '16px',
                      textAlign: 'center',
                      flexShrink: 0,
                    }}
                  >
                    {icon}
                  </span>
                  <span
                    style={{
                      fontFamily: "'Crimson Pro', serif",
                      fontSize: '14px',
                      letterSpacing: '0.01em',
                    }}
                  >
                    {label}
                  </span>
                </Link>
              ))}
            </div>

            {/* Expand card */}
            {project.can_expand && (
              <div
                style={{
                  marginTop: '1rem',
                  padding: '1rem',
                  border: `1px solid ${B1.gold}`,
                  background: B1.goldSubtle,
                }}
              >
                <div
                  style={{
                    fontFamily: "'Playfair Display', serif",
                    fontSize: '13px',
                    color: B1.gold,
                    marginBottom: '0.25rem',
                  }}
                >
                  原型扩写
                </div>
                <p
                  style={{
                    fontFamily: "'Crimson Pro', serif",
                    fontSize: '12px',
                    color: B1.textMuted,
                    fontStyle: 'italic',
                    marginBottom: '0.75rem',
                    lineHeight: 1.4,
                  }}
                >
                  当前为原型模式（2人），可扩写为完整6人版本
                </p>
                <Link
                  to={`/projects/${encodeURIComponent(project.name)}/phase/expand`}
                  style={{
                    display: 'inline-block',
                    padding: '0.4rem 0.75rem',
                    border: `1px solid ${B1.gold}`,
                    color: B1.gold,
                    fontFamily: "'Crimson Pro', serif",
                    fontSize: '12px',
                    textDecoration: 'none',
                  }}
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
