import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getMatrix, updateMatrixCell, initializeMatrix } from '../api/files'
import type { CharacterMatrix, CognitiveState } from '../types/api'

const STATE_COLORS: Record<string, string> = {
  '知': '#166534',
  '疑': '#854D0E',
  '昧': '#9A3412',
  '否': '#3F3F46',
  '误信': '#6B21A8',
  '隐瞒': '#991B1B',
}

const STATE_LABELS: Record<string, string> = {
  '知': '知道',
  '疑': '怀疑',
  '昧': '昧于事实',
  '否': '不知道',
  '误信': '误信',
  '隐瞒': '隐瞒',
}

export default function MatrixEditor() {
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const projectName = decodeURIComponent(name || '')

  const [matrix, setMatrix] = useState<CharacterMatrix | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingCell, setEditingCell] = useState<{ char: string; event: string } | null>(null)
  const [editState, setEditState] = useState<CognitiveState | null>(null)

  useEffect(() => {
    loadMatrix()
  }, [projectName])

  async function loadMatrix() {
    try {
      const data = await getMatrix(projectName)
      setMatrix(data)
    } catch (e: unknown) {
      if ((e as Error).message?.includes('404') || (e as Error).message?.includes('not found')) {
        try {
          await initializeMatrix(projectName, 6, 7, false)
          const data = await getMatrix(projectName)
          setMatrix(data)
        } catch {
          setError('矩阵未初始化，请先运行阶段2')
        }
      } else {
        setError(e instanceof Error ? e.message : '加载失败')
      }
    } finally {
      setLoading(false)
    }
  }

  async function handleCellClick(charId: string, eventId: string) {
    if (!matrix) return
    const cog = matrix.characters[charId]?.event_cognitions[eventId]
    setEditingCell({ char: charId, event: eventId })
    setEditState(cog || { state: '否', detail: '', evidence_refs: [] })
  }

  async function handleCellSave() {
    if (!editingCell || !editState || !matrix) return
    try {
      await updateMatrixCell(
        projectName,
        editingCell.char,
        editingCell.event,
        editState.state,
        editState.detail,
        editState.evidence_refs
      )
      const updated = { ...matrix }
      updated.characters[editingCell.char].event_cognitions[editingCell.event] = { ...editState }
      setMatrix(updated)
      setEditingCell(null)
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : '保存失败')
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <span style={{ color: 'var(--text-faint)', fontFamily: "'Crimson Pro', serif", fontStyle: 'italic' }}>
          加载中...
        </span>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: '3rem', maxWidth: '640px', margin: '0 auto' }}>
        <div
          style={{
            padding: '1.5rem',
            border: '1px solid var(--output-error-border)',
            background: 'var(--output-error-bg)',
            color: 'var(--output-error)',
            fontFamily: "'Crimson Pro', serif",
            marginBottom: '1rem',
          }}
        >
          {error}
        </div>
        <button
          onClick={() => navigate(`/projects/${encodeURIComponent(projectName)}/phase/2`)}
          className="btn-primary"
          style={{ fontSize: '13px' }}
        >
          运行阶段2初始化
        </button>
      </div>
    )
  }

  if (!matrix) return null

  const charIds = Object.keys(matrix.characters).sort()
  const eventIds: string[] = []
  for (let i = 1; i <= matrix.event_count; i++) {
    eventIds.push(`E${i}`)
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      {/* Header */}
      <header
        style={{
          padding: '1.5rem 2rem',
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
            <div className="label" style={{ marginBottom: '0.2rem', color: 'var(--accent-crimson)' }}>
              <span className="accent-rule" style={{ background: 'var(--accent-crimson)' }} />
              Information Matrix
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <h1
                style={{
                  fontFamily: "'Playfair Display', serif",
                  fontSize: '1.25rem',
                  fontWeight: 500,
                  color: 'var(--text-cream)',
                  letterSpacing: '-0.01em',
                }}
              >
                信息矩阵
              </h1>
              <span
                style={{
                  fontFamily: "'Crimson Pro', serif",
                  fontSize: '13px',
                  color: 'var(--text-faint)',
                }}
              >
                {matrix.char_count} 人 × {matrix.event_count} 事件
              </span>
              {matrix.is_prototype && (
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
          </div>
        </div>

        <button
          onClick={loadMatrix}
          className="btn-ghost"
          style={{ fontSize: '13px' }}
        >
          ↻ 刷新
        </button>
      </header>

      <div style={{ padding: '2rem', overflowX: 'auto' }}>
        {/* Table */}
        <div style={{ minWidth: 'fit-content' }}>
          <table
            style={{
              borderCollapse: 'collapse',
              width: '100%',
              fontFamily: "'Crimson Pro', serif",
            }}
          >
            <thead>
              <tr>
                <th
                  style={{
                    padding: '0.75rem 1rem',
                    textAlign: 'left',
                    fontSize: '11px',
                    fontFamily: "'Crimson Pro', serif",
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    color: 'var(--text-faint)',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-raised)',
                    position: 'sticky',
                    top: 0,
                    left: 0,
                    zIndex: 2,
                    whiteSpace: 'nowrap',
                  }}
                >
                  角色 / 事件
                </th>
                {eventIds.map((eid) => (
                  <th
                    key={eid}
                    style={{
                      padding: '0.75rem 0.5rem',
                      textAlign: 'center',
                      fontSize: '11px',
                      fontFamily: "'Crimson Pro', serif",
                      letterSpacing: '0.08em',
                      textTransform: 'uppercase',
                      color: 'var(--text-faint)',
                      border: '1px solid var(--border)',
                      background: 'var(--bg-raised)',
                      position: 'sticky',
                      top: 0,
                      zIndex: 1,
                      minWidth: '100px',
                    }}
                  >
                    {eid}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {charIds.map((cid) => {
                const char = matrix.characters[cid]
                return (
                  <tr key={cid}>
                    <td
                      style={{
                        padding: '0.75rem 1rem',
                        border: '1px solid var(--border)',
                        background: 'var(--bg-raised)',
                        position: 'sticky',
                        left: 0,
                        zIndex: 1,
                        whiteSpace: 'nowrap',
                      }}
                    >
                      <div
                        style={{
                          fontFamily: "'Crimson Pro', serif",
                          fontSize: '15px',
                          color: 'var(--text-cream)',
                          fontWeight: 500,
                        }}
                      >
                        {char.name || cid}
                      </div>
                      <div
                        style={{
                          fontFamily: "'Crimson Pro', serif",
                          fontSize: '12px',
                          color: 'var(--text-faint)',
                          fontStyle: 'italic',
                          marginTop: '2px',
                        }}
                      >
                        {char.role || ''}
                      </div>
                    </td>
                    {eventIds.map((eid) => {
                      const cog = char.event_cognitions[eid]
                      const state = cog?.state || '否'
                      const color = STATE_COLORS[state] || '#3F3F46'

                      return (
                        <td
                          key={eid}
                          onClick={() => handleCellClick(cid, eid)}
                          style={{
                            padding: '0.375rem',
                            border: '1px solid var(--border)',
                            cursor: 'pointer',
                            textAlign: 'center',
                            transition: 'all 150ms',
                            background: 'var(--bg-raised)',
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.outline = `1px solid var(--accent-gold)`
                            e.currentTarget.style.outlineOffset = '-1px'
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.outline = 'none'
                          }}
                          title={cog?.detail || state}
                        >
                          <div
                            style={{
                              display: 'inline-block',
                              padding: '0.25rem 0.5rem',
                              borderRadius: '2px',
                              background: color,
                              color: 'var(--text-cream)',
                              fontSize: '11px',
                              fontFamily: "'JetBrains Mono', monospace",
                              letterSpacing: '0.05em',
                              minWidth: '2rem',
                              textAlign: 'center',
                            }}
                          >
                            {state}
                          </div>
                          {cog?.detail && (
                            <div
                              style={{
                                fontSize: '10px',
                                color: 'var(--text-faint)',
                                marginTop: '2px',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                                maxWidth: '100px',
                                fontFamily: "'Crimson Pro', serif",
                              }}
                            >
                              {cog.detail.slice(0, 15)}
                            </div>
                          )}
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Legend */}
        <div
          style={{
            marginTop: '1.5rem',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '1rem',
          }}
        >
          {Object.entries(STATE_LABELS).map(([state, label]) => (
            <div key={state} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div
                style={{
                  width: '20px',
                  height: '20px',
                  borderRadius: '2px',
                  background: STATE_COLORS[state],
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--text-cream)',
                  fontSize: '10px',
                  fontFamily: "'JetBrains Mono', monospace",
                  fontWeight: 600,
                }}
              >
                {state}
              </div>
              <span
                style={{
                  fontFamily: "'Crimson Pro', serif",
                  fontSize: '13px',
                  color: 'var(--text-faint)',
                }}
              >
                {label}
              </span>
            </div>
          ))}
        </div>

        {/* Evidence chain */}
        {Object.keys(matrix.evidence).length > 0 && (
          <div style={{ marginTop: '2.5rem' }}>
            <div className="label" style={{ marginBottom: '1rem', color: 'var(--text-faint)' }}>
              证据链
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
              {Object.entries(matrix.evidence).map(([eid, ev]) => (
                <div
                  key={eid}
                  style={{
                    padding: '1rem 1.25rem',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-raised)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.375rem' }}>
                    <span
                      style={{
                        fontFamily: "'Playfair Display', serif",
                        fontSize: '15px',
                        color: 'var(--text-cream)',
                      }}
                    >
                      {ev.name}
                    </span>
                    <span
                      style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: '11px',
                        color: 'var(--text-faint)',
                      }}
                    >
                      {eid}
                    </span>
                    <span
                      style={{
                        fontFamily: "'Crimson Pro', serif",
                        fontSize: '11px',
                        color: 'var(--accent-gold)',
                        background: 'rgba(180,83,9,0.1)',
                        padding: '1px 6px',
                        borderRadius: '2px',
                        letterSpacing: '0.02em',
                      }}
                    >
                      {ev.chain_role}
                    </span>
                  </div>
                  <p
                    style={{
                      fontFamily: "'Crimson Pro', serif",
                      fontSize: '14px',
                      color: 'var(--text-muted)',
                      fontStyle: 'italic',
                      marginBottom: '0.5rem',
                    }}
                  >
                    {ev.description}
                  </p>
                  <div
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: '11px',
                      color: 'var(--text-faint)',
                    }}
                  >
                    来源: {ev.source_event} / {ev.source_character} → 指向: {ev.points_to}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Cell edit modal */}
      {editingCell && editState && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(18,17,15,0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 50,
          }}
          onClick={(e) => e.target === e.currentTarget && setEditingCell(null)}
        >
          <div
            style={{
              background: 'var(--bg-raised)',
              border: '1px solid var(--border)',
              width: '100%',
              maxWidth: '440px',
              padding: '2rem',
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
            }}
          >
            <div className="label" style={{ marginBottom: '0.5rem', color: 'var(--accent-crimson)' }}>
              <span className="accent-rule" style={{ background: 'var(--accent-crimson)' }} />
              编辑认知
            </div>
            <h2
              style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: '1.25rem',
                fontWeight: 500,
                color: 'var(--text-cream)',
                marginBottom: '1.5rem',
                letterSpacing: '-0.01em',
              }}
            >
              {editingCell.char} × {editingCell.event}
            </h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* State selector */}
              <div>
                <div className="label" style={{ marginBottom: '0.75rem', color: 'var(--text-faint)' }}>
                  认知状态
                </div>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: '0.375rem',
                  }}
                >
                  {Object.keys(STATE_LABELS).map((s) => (
                    <button
                      key={s}
                      onClick={() => setEditState({ ...editState, state: s as CognitiveState['state'] })}
                      style={{
                        padding: '0.5rem 0.25rem',
                        borderRadius: '2px',
                        fontSize: '12px',
                        fontFamily: "'JetBrains Mono', monospace",
                        cursor: 'pointer',
                        border: '1px solid',
                        borderColor:
                          editState.state === s ? STATE_COLORS[s] : 'var(--border)',
                        background: editState.state === s ? STATE_COLORS[s] : 'transparent',
                        color: editState.state === s ? 'var(--text-cream)' : 'var(--text-muted)',
                        transition: 'all 150ms',
                        letterSpacing: '0.03em',
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              {/* Detail */}
              <div>
                <div className="label" style={{ marginBottom: '0.5rem', color: 'var(--text-faint)' }}>
                  详情
                </div>
                <textarea
                  value={editState.detail}
                  onChange={(e) => setEditState({ ...editState, detail: e.target.value })}
                  style={{
                    width: '100%',
                    minHeight: '80px',
                    resize: 'none',
                    fontSize: '14px',
                    lineHeight: 1.6,
                  }}
                  placeholder="描述此角色对该事件的认知..."
                />
              </div>
            </div>

            <div
              style={{
                display: 'flex',
                gap: '0.625rem',
                marginTop: '1.75rem',
                paddingTop: '1.25rem',
                borderTop: '1px solid var(--border-subtle)',
              }}
            >
              <button onClick={handleCellSave} className="btn-primary" style={{ fontSize: '13px' }}>
                保存
              </button>
              <button
                onClick={() => setEditingCell(null)}
                className="btn-ghost"
                style={{ fontSize: '13px' }}
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
