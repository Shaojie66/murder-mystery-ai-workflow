import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getCosts } from '../api/files'
import type { CostSummary } from '../types/api'
import React from 'react'

const Charts = React.lazy(() => import('./Charts'))

const OPERATION_LABELS: Record<string, string> = {
  stage_1_mechanism: '阶段1: 机制设计',
  stage_2_matrix: '阶段2: 信息矩阵',
  stage_2_characters: '阶段2: 角色剧本',
  expand_phase1: '扩写: 事件扩展',
  expand_phase2: '扩写: 新角色',
  audit_round1: '审计: 第1轮',
  audit_round2: '审计: 第2轮',
  audit_round3: '审计: 第3轮',
  consistency_check: '一致性检查',
}

function formatCost(cost: number): string {
  if (cost < 0.01) return `$${cost.toFixed(4)}`
  if (cost < 1) return `$${cost.toFixed(3)}`
  return `$${cost.toFixed(2)}`
}

function formatTokens(tokens: number): string {
  if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(1)}M`
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}K`
  return String(tokens)
}

export default function CostPage() {
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const projectName = decodeURIComponent(name || '')
  const [costs, setCosts] = useState<CostSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!projectName) return
    getCosts(projectName)
      .then(setCosts)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '加载失败'))
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
          }}
        >
          {error}
        </div>
      </div>
    )
  }

  if (!costs) return null

  const hasData = costs.total_cost > 0

  const byOperationChart = costs.by_operation
    .filter((op) => op.cost > 0)
    .map((op) => ({
      name: OPERATION_LABELS[op.operation] || op.operation,
      cost: op.cost,
      tokens: op.tokens,
      count: op.count,
    }))
    .sort((a, b) => b.cost - a.cost)

  const byModelChart = Object.values(costs.by_model)
    .filter((m) => m.cost > 0)
    .map((m) => ({ name: m.model, cost: m.cost }))

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
        <div>
          <div className="label" style={{ marginBottom: '0.5rem', color: 'var(--accent-crimson)' }}>
            <span className="accent-rule" style={{ background: 'var(--accent-crimson)' }} />
            Cost Analysis
          </div>
          <h1
            style={{
              fontFamily: "'Playfair Display', serif",
              fontSize: '1.75rem',
              fontWeight: 500,
              color: 'var(--text-cream)',
              letterSpacing: '-0.02em',
            }}
          >
            消耗统计
          </h1>
          <p
            style={{
              fontFamily: "'Crimson Pro', serif",
              fontSize: '15px',
              color: 'var(--text-muted)',
              fontStyle: 'italic',
              marginTop: '0.25rem',
            }}
          >
            {projectName}
          </p>
        </div>

        <button
          onClick={() => navigate(`/projects/${encodeURIComponent(projectName)}`)}
          className="btn-ghost"
          style={{ fontSize: '13px' }}
        >
          ← 返回项目
        </button>
      </header>

      <div style={{ maxWidth: '900px', margin: '0 auto', padding: '3rem' }}>
        {!hasData && (
          <div style={{ textAlign: 'center', padding: '5rem 0' }}>
            <div
              style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: '4rem',
                color: 'var(--border)',
                marginBottom: '1rem',
                lineHeight: 1,
              }}
            >
              $
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
              暂无消耗记录
            </h2>
            <p
              style={{
                fontFamily: "'Crimson Pro', serif",
                fontSize: '16px',
                color: 'var(--text-muted)',
                fontStyle: 'italic',
              }}
            >
              运行阶段后将在此显示 API 消耗统计
            </p>
          </div>
        )}

        {hasData && (
          <>
            {/* Summary metrics */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '1px',
                marginBottom: '3rem',
                border: '1px solid var(--border)',
                background: 'var(--border-subtle)',
              }}
            >
              {[
                { label: '总消耗', value: formatCost(costs.total_cost), accent: 'var(--accent-crimson)' },
                { label: 'Token 总数', value: formatTokens(costs.total_tokens), accent: 'var(--text-cream)' },
                {
                  label: '操作次数',
                  value: String(costs.by_operation.reduce((s, op) => s + op.count, 0)),
                  accent: 'var(--text-cream)',
                },
              ].map(({ label, value, accent }) => (
                <div
                  key={label}
                  style={{
                    padding: '1.75rem 1.5rem',
                    background: 'var(--bg-raised)',
                    textAlign: 'center',
                  }}
                >
                  <div
                    className="label"
                    style={{ marginBottom: '0.5rem', color: 'var(--text-faint)', textAlign: 'center' }}
                  >
                    {label}
                  </div>
                  <div
                    style={{
                      fontFamily: "'Playfair Display', serif",
                      fontSize: '2rem',
                      fontWeight: 500,
                      color: accent,
                      letterSpacing: '-0.02em',
                      lineHeight: 1,
                    }}
                  >
                    {value}
                  </div>
                </div>
              ))}
            </div>

            {/* Charts row */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '1px',
                marginBottom: '2rem',
                border: '1px solid var(--border)',
                background: 'var(--border-subtle)',
              }}
            >
              <React.Suspense
                fallback={
                  <>
                    <div style={{ padding: '1.75rem', background: 'var(--bg-raised)' }}>
                      <div className="label" style={{ marginBottom: '1.25rem', color: 'var(--text-faint)' }}>各阶段消耗</div>
                      <div style={{ height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <span style={{ color: 'var(--text-faint)', fontFamily: "'Crimson Pro', serif", fontStyle: 'italic' }}>加载中...</span>
                      </div>
                    </div>
                    <div style={{ padding: '1.75rem', background: 'var(--bg-raised)' }}>
                      <div className="label" style={{ marginBottom: '1.25rem', color: 'var(--text-faint)' }}>各模型消耗</div>
                      <div style={{ height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <span style={{ color: 'var(--text-faint)', fontFamily: "'Crimson Pro', serif", fontStyle: 'italic' }}>加载中...</span>
                      </div>
                    </div>
                  </>
                }
              >
                <Charts
                  byOperationChart={byOperationChart}
                  byModelChart={byModelChart}
                  formatCost={formatCost}
                />
              </React.Suspense>
            </div>

            {/* Detailed table */}
            <div
              style={{
                border: '1px solid var(--border)',
                background: 'var(--bg-raised)',
              }}
            >
              <div
                style={{
                  padding: '1rem 1.5rem',
                  borderBottom: '1px solid var(--border-subtle)',
                }}
              >
                <div className="label" style={{ color: 'var(--text-faint)' }}>
                  详细记录
                </div>
              </div>

              {/* Table header */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 80px 80px 100px',
                  gap: '0',
                  padding: '0.625rem 1.5rem',
                  borderBottom: '1px solid var(--border-subtle)',
                  background: 'var(--bg-elevated)',
                }}
              >
                {['操作', '次数', 'Tokens', '消耗'].map((h, i) => (
                  <div
                    key={h}
                    className="label"
                    style={{
                      color: 'var(--text-faint)',
                      textAlign: i > 0 ? 'right' : 'left',
                    }}
                  >
                    {h}
                  </div>
                ))}
              </div>

              {byOperationChart.map((op) => (
                <div
                  key={op.name}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 80px 80px 100px',
                    gap: '0',
                    padding: '0.875rem 1.5rem',
                    borderBottom: '1px solid var(--border-subtle)',
                    transition: 'background 150ms',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--cream-subtle)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <div
                    style={{
                      fontFamily: "'Crimson Pro', serif",
                      fontSize: '15px',
                      color: 'var(--text-cream)',
                    }}
                  >
                    {op.name}
                  </div>
                  <div
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: '12px',
                      color: 'var(--text-muted)',
                      textAlign: 'right',
                    }}
                  >
                    {op.count}
                  </div>
                  <div
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: '12px',
                      color: 'var(--text-muted)',
                      textAlign: 'right',
                    }}
                  >
                    {formatTokens(op.tokens)}
                  </div>
                  <div
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: '12px',
                      color: 'var(--accent-gold)',
                      textAlign: 'right',
                    }}
                  >
                    {formatCost(op.cost)}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
