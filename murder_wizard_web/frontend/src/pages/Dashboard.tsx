import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listProjects, createProject, deleteProject } from '../api/projects'
import { useProjectStore } from '../stores/projectStore'
import type { Project } from '../types/api'

const STORY_TYPE_LABELS: Record<string, string> = {
  emotion: '情感本',
  reasoning: '推理本',
  fun: '欢乐本',
  horror: '恐怖本',
  mechanic: '机制本',
}

const STORY_TYPE_DESCRIPTIONS: Record<string, string> = {
  emotion: '侧重角色情感、人物关系、沉浸式体验',
  reasoning: '侧重逻辑推理、线索链、公平性验证',
  fun: '侧重欢乐氛围、社交互动、游戏性',
  horror: '侧重恐怖氛围、悬疑营造、心理压迫',
  mechanic: '侧重游戏机制、策略对抗、阵营博弈',
}

const STAGE_SHORT: Record<string, string> = {
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

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newType, setNewType] = useState('mechanic')
  const [newPrototype, setNewPrototype] = useState(true)
  const [filterType, setFilterType] = useState('all')
  const [filterStage, setFilterStage] = useState('all')
  const navigate = useNavigate()
  const { setProjects: setStoreProjects } = useProjectStore()

  async function loadProjects() {
    try {
      setLoading(true)
      const data = await listProjects()
      setProjects(data.projects)
      setStoreProjects(data.projects)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadProjects() }, [])

  const filteredProjects = projects.filter((p) => {
    const typeMatch = filterType === 'all' || p.story_type === filterType
    const stageMatch = filterStage === 'all' || p.current_stage === filterStage
    return typeMatch && stageMatch
  })

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!newName.trim()) return
    try {
      await createProject({ name: newName.trim(), story_type: newType, is_prototype: newPrototype })
      setShowCreate(false)
      setNewName('')
      loadProjects()
      navigate(`/projects/${encodeURIComponent(newName.trim())}`)
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : '创建失败')
    }
  }

  async function handleDelete(name: string, e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm(`确定删除项目 "${name}" 吗？此操作不可撤销。`)) return
    try {
      await deleteProject(name)
      loadProjects()
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : '删除失败')
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      {/* Masthead */}
      <header
        style={{
          padding: '3rem 3rem 2rem',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-base)',
        }}
      >
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
          <div className="label" style={{ marginBottom: '1rem', color: 'var(--accent-crimson)' }}>
            <span className="accent-rule" style={{ background: 'var(--accent-crimson)' }} />
            Murder Wizard
          </div>
          <h1
            style={{
              fontFamily: "'Playfair Display', serif",
              fontSize: 'clamp(2rem, 4vw, 3rem)',
              fontWeight: 500,
              color: 'var(--text-cream)',
              letterSpacing: '-0.02em',
              lineHeight: 1.1,
              marginBottom: '0.75rem',
            }}
          >
            我的项目
          </h1>
          <p
            style={{
              fontFamily: "'Crimson Pro', serif",
              fontSize: '17px',
              color: 'var(--text-muted)',
              fontStyle: 'italic',
            }}
          >
            {filteredProjects.length > 0
              ? `${filteredProjects.length} 个项目`
              : projects.length > 0 ? '没有匹配的项目' : '开始你的第一个剧本杀创作'}
          </p>
        </div>
      </header>

      <div style={{ maxWidth: '800px', margin: '0 auto', padding: '0 3rem 4rem' }}>
        {/* Actions bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1.5rem 0',
            borderBottom: '1px solid var(--border-subtle)',
            marginBottom: '2rem',
            gap: '1rem',
            flexWrap: 'wrap',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flex: 1 }}>
            <div className="label" style={{ color: 'var(--text-faint)' }}>
              项目
            </div>
            {/* Type filter */}
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              style={{
                fontFamily: "'Crimson Pro', serif",
                fontSize: '13px',
                color: 'var(--text-muted)',
                background: 'var(--bg-raised)',
                border: '1px solid var(--border)',
                padding: '4px 8px',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              <option value="all">全部类型</option>
              <option value="emotion">情感本</option>
              <option value="reasoning">推理本</option>
              <option value="fun">欢乐本</option>
              <option value="horror">恐怖本</option>
              <option value="mechanic">机制本</option>
            </select>
            {/* Stage filter */}
            <select
              value={filterStage}
              onChange={(e) => setFilterStage(e.target.value)}
              style={{
                fontFamily: "'Crimson Pro', serif",
                fontSize: '13px',
                color: 'var(--text-muted)',
                background: 'var(--bg-raised)',
                border: '1px solid var(--border)',
                padding: '4px 8px',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              <option value="all">全部进度</option>
              <option value="idle">未开始</option>
              <option value="stage_1_mechanism">机制设计</option>
              <option value="stage_2_script">剧本创作</option>
              <option value="stage_3_visual">视觉物料</option>
              <option value="stage_4_test">用户测试</option>
              <option value="stage_5_commercial">商业化</option>
              <option value="stage_6_print">印刷生产</option>
              <option value="stage_7_promo">宣发内容</option>
              <option value="stage_8_community">社区运营</option>
            </select>
          </div>
          <button onClick={() => setShowCreate(true)} className="btn-primary" style={{ fontSize: '13px' }}>
            + 新建项目
          </button>
        </div>

        {/* Error */}
        {error && (
          <div
            style={{
              padding: '1rem 1.25rem',
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
        )}

        {/* Loading skeleton */}
        {loading && projects.length === 0 && (
          <div aria-busy="true" aria-label="加载项目中" style={{ padding: '2rem 0' }}>
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                style={{
                  height: '72px',
                  background: 'var(--bg-raised)',
                  border: '1px solid var(--border)',
                  marginBottom: '1px',
                  opacity: 1 - i * 0.2,
                }}
              />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && projects.length === 0 && !error && (
          <div style={{ textAlign: 'center', padding: '5rem 0' }}>
            <div
              style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: '4rem',
                color: 'var(--border)',
                marginBottom: '1.5rem',
                lineHeight: 1,
              }}
            >
              —
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
              还没有项目
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
              创建你的第一个剧本杀，开启创作之旅
            </p>
            <button onClick={() => setShowCreate(true)} className="btn-primary">
              创建第一个项目
            </button>
          </div>
        )}

        {/* Project list — editorial rows */}
        {filteredProjects.length > 0 && (
          <div>
            {filteredProjects.map((project) => (
              <div
                key={project.name}
                style={{
                  position: 'relative',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0', position: 'relative' }}>
                  <Link
                    to={`/projects/${encodeURIComponent(project.name)}`}
                    style={{
                      display: 'block',
                      flex: 1,
                      padding: '1.5rem 0',
                      paddingRight: '3rem',
                      borderBottom: '1px solid var(--border-subtle)',
                      textDecoration: 'none',
                      transition: 'all 150ms',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.paddingLeft = '0.75rem'
                      e.currentTarget.style.borderLeft = '2px solid var(--accent-crimson)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.paddingLeft = '0'
                      e.currentTarget.style.borderLeft = '2px solid transparent'
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        justifyContent: 'space-between',
                        gap: '2rem',
                      }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        {/* Row 1: name + meta */}
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'baseline',
                            gap: '1rem',
                            marginBottom: '0.375rem',
                          }}
                        >
                          <h3
                            style={{
                              fontFamily: "'Playfair Display', serif",
                              fontSize: '1.25rem',
                              fontWeight: 500,
                              color: 'var(--text-cream)',
                              letterSpacing: '-0.01em',
                              margin: 0,
                            }}
                          >
                            {project.name}
                          </h3>
                          <span
                            style={{
                              fontFamily: "'Crimson Pro', serif",
                              fontSize: '12px',
                              color: 'var(--text-faint)',
                              letterSpacing: '0.04em',
                            }}
                          >
                            {STORY_TYPE_LABELS[project.story_type] || project.story_type}
                          </span>
                          {project.is_prototype && (
                            <span
                              style={{
                                fontFamily: "'Crimson Pro', serif",
                                fontSize: '10px',
                                letterSpacing: '0.1em',
                                textTransform: 'uppercase',
                                color: 'var(--accent-gold)',
                                background: 'rgba(180,83,9,0.1)',
                                padding: '2px 6px',
                                borderRadius: '2px',
                              }}
                            >
                              原型
                            </span>
                          )}
                        </div>

                        {/* Row 2: stage */}
                        <div
                          style={{
                            fontFamily: "'Crimson Pro', serif",
                            fontSize: '14px',
                            color: 'var(--text-muted)',
                            fontStyle: 'italic',
                          }}
                        >
                          {STAGE_SHORT[project.current_stage] || project.current_stage}
                          <span style={{ color: 'var(--text-faint)', marginLeft: '0.5rem' }}>
                            · {project.artifact_count} 个产物
                          </span>
                        </div>
                      </div>

                      {/* Arrow */}
                      <div
                        style={{
                          color: 'var(--text-faint)',
                          fontSize: '18px',
                          flexShrink: 0,
                          paddingTop: '4px',
                        }}
                      >
                        →
                      </div>
                    </div>
                  </Link>

                  {/* Delete button — visually hidden until parent hover, keyboard accessible */}
                  <button
                    onClick={(e) => handleDelete(project.name, e)}
                    className="delete-btn"
                    aria-label={`删除项目 ${project.name}`}
                    style={{
                      position: 'absolute',
                      right: 0,
                      top: '1.5rem',
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      fontSize: '12px',
                      cursor: 'pointer',
                      padding: '4px 8px',
                      fontFamily: "'Crimson Pro', serif",
                    }}
                  >
                    删除
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create modal — editorial style */}
      {showCreate && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(18,17,15,0.85)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 50,
          }}
          onClick={(e) => e.target === e.currentTarget && setShowCreate(false)}
        >
          <div
            style={{
              background: 'var(--bg-raised)',
              border: '1px solid var(--border)',
              width: '100%',
              maxWidth: '480px',
              padding: '3rem',
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
            }}
          >
            <div className="label" style={{ marginBottom: '0.75rem', color: 'var(--accent-crimson)' }}>
              <span className="accent-rule" style={{ background: 'var(--accent-crimson)' }} />
              新建项目
            </div>
            <h2
              style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: '1.75rem',
                fontWeight: 500,
                color: 'var(--text-cream)',
                marginBottom: '2rem',
                letterSpacing: '-0.01em',
              }}
            >
              创建新项目
            </h2>

            <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div>
                <label
                  className="label"
                  style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-faint)' }}
                >
                  项目名称
                </label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="例如: 校园悬疑案"
                  autoFocus
                />
              </div>

              <div>
                <label
                  className="label"
                  style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-faint)' }}
                >
                  剧本类型
                </label>
                <select value={newType} onChange={(e) => setNewType(e.target.value)}>
                  <option value="emotion">情感本</option>
                  <option value="reasoning">推理本</option>
                  <option value="fun">欢乐本</option>
                  <option value="horror">恐怖本</option>
                  <option value="mechanic">机制本</option>
                </select>
                <div
                  style={{
                    fontFamily: "'Crimson Pro', serif",
                    fontSize: '13px',
                    color: 'var(--text-faint)',
                    fontStyle: 'italic',
                    marginTop: '0.375rem',
                  }}
                >
                  {STORY_TYPE_DESCRIPTIONS[newType]}
                </div>
              </div>

              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={newPrototype}
                    onChange={(e) => setNewPrototype(e.target.checked)}
                    style={{ width: '16px', height: '16px', accentColor: 'var(--accent-crimson)' }}
                  />
                  <div>
                    <div
                      style={{
                        fontFamily: "'Crimson Pro', serif",
                        fontSize: '15px',
                        color: 'var(--text-cream)',
                      }}
                    >
                      原型模式（2人快速验证）
                    </div>
                    <div
                      style={{
                        fontFamily: "'Crimson Pro', serif",
                        fontSize: '13px',
                        color: 'var(--text-faint)',
                        fontStyle: 'italic',
                        marginTop: '2px',
                      }}
                    >
                      先快速验证核心机制，再扩写为完整6人版本
                    </div>
                  </div>
                </label>
              </div>

              <div
                style={{
                  display: 'flex',
                  gap: '0.75rem',
                  paddingTop: '0.5rem',
                  borderTop: '1px solid var(--border-subtle)',
                }}
              >
                <button type="submit" disabled={!newName.trim()} className="btn-primary">
                  创建项目
                </button>
                <button type="button" onClick={() => setShowCreate(false)} className="btn-ghost">
                  取消
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
