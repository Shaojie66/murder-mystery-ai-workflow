import React, { useState, useEffect, lazy, Suspense } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getCosts } from '../api/files'
import type { CostSummary } from '../types/api'

// Lazy load named Recharts exports individually
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const makeLazy = (loader: () => Promise<unknown>) => lazy(loader as () => Promise<{ default: React.ComponentType<any> }>)

const LazyResponsiveContainer = makeLazy(() => import('recharts').then(m => ({ default: m.ResponsiveContainer })))
const LazyBarChart = makeLazy(() => import('recharts').then(m => ({ default: m.BarChart })))
const LazyXAxis = makeLazy(() => import('recharts').then(m => ({ default: m.XAxis })))
const LazyYAxis = makeLazy(() => import('recharts').then(m => ({ default: m.YAxis })))
const LazyTooltip = makeLazy(() => import('recharts').then(m => ({ default: m.Tooltip })))
const LazyBar = makeLazy(() => import('recharts').then(m => ({ default: m.Bar })))
const LazyPieChart = makeLazy(() => import('recharts').then(m => ({ default: m.PieChart })))
const LazyPie = makeLazy(() => import('recharts').then(m => ({ default: m.Pie })))
const LazyCell = makeLazy(() => import('recharts').then(m => ({ default: m.Cell })))

const ChartFallback = () => (
  <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-faint)', fontFamily: "'Crimson Pro', serif", fontStyle: 'italic' }}>加载图表...</div>
)

const COLORS = ['#9B1C1C', '#B45309', '#78716C', '#44403C', '#292524', '#A89F94']

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
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" style={{ color: 'var(--border)' }} aria-hidden="true">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 6v6l4 2"/>
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
              {/* By operation */}
              <div style={{ padding: '1.75rem', background: 'var(--bg-raised)' }}>
                <div className="label" style={{ marginBottom: '1.25rem', color: 'var(--text-faint)' }}>
                  各阶段消耗
                </div>
                {byOperationChart.length > 0 ? (
                  <Suspense fallback={<ChartFallback />}>
                    <LazyResponsiveContainer width="100%" height={200}>
                      <LazyBarChart data={byOperationChart} layout="vertical">
                        <LazyXAxis
                          type="number"
                          tickFormatter={(v: number) => `$${v.toFixed(2)}`}
                          stroke="var(--text-faint)"
                          fontSize={11}
                          tick={{ fontFamily: "'Crimson Pro', serif" }}
                        />
                        <LazyYAxis
                          dataKey="name"
                          type="category"
                          width={100}
                          stroke="var(--text-faint)"
                          fontSize={10}
                          tick={{ fontFamily: "'Crimson Pro', serif", fill: 'var(--text-muted)' }}
                        />
                        <LazyTooltip
                          formatter={(v: number) => [`$${v.toFixed(4)}`, '消耗']}
                          contentStyle={{
                            backgroundColor: 'var(--bg-elevated)',
                            border: '1px solid var(--border)',
                            borderRadius: '2px',
                            fontFamily: "'Crimson Pro', serif",
                            fontSize: '13px',
                            color: 'var(--text-cream)',
                          }}
                        />
                        <LazyBar dataKey="cost" fill="var(--accent-gold)" radius={[0, 2, 2, 0]} />
                      </LazyBarChart>
                    </LazyResponsiveContainer>
                  </Suspense>
                ) : (
                  <div style={{ color: 'var(--text-faint)', fontFamily: "'Crimson Pro', serif", fontStyle: 'italic', fontSize: '14px', paddingTop: '2rem', textAlign: 'center' }}>
                    暂无数据
                  </div>
                )}
              </div>

              {/* By model */}
              <div style={{ padding: '1.75rem', background: 'var(--bg-raised)' }}>
                <div className="label" style={{ marginBottom: '1.25rem', color: 'var(--text-faint)' }}>
                  各模型消耗
                </div>
                {byModelChart.length > 0 ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                    <Suspense fallback={<ChartFallback />}>
                      <LazyResponsiveContainer width={120} height={120}>
                        <LazyPieChart>
                          <LazyPie
                            data={byModelChart}
                            dataKey="cost"
                            nameKey="name"
                            cx="50%"
                            cy="50%"
                            innerRadius={32}
                          >
                            {byModelChart.map((_, i) => (
                              <LazyCell key={i} fill={COLORS[i % COLORS.length]} />
                            ))}
                          </LazyPie>
                        </LazyPieChart>
                      </LazyResponsiveContainer>
                    </Suspense>
                    <div style={{ flex: 1 }}>
                      {byModelChart.map((item, i) => (
                        <div
                          key={item.name}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            marginBottom: '0.5rem',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <div
                              style={{
                                width: '8px',
                                height: '8px',
                                borderRadius: '50%',
                                backgroundColor: COLORS[i % COLORS.length],
                                flexShrink: 0,
                              }}
                            />
                            <span
                              style={{
                                fontFamily: "'Crimson Pro', serif",
                                fontSize: '13px',
                                color: 'var(--text-muted)',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                                maxWidth: '120px',
                              }}
                            >
                              {item.name}
                            </span>
                          </div>
                          <span
                            style={{
                              fontFamily: "'JetBrains Mono', monospace",
                              fontSize: '11px',
                              color: 'var(--accent-gold)',
                            }}
                          >
                            {formatCost(item.cost)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-faint)', fontFamily: "'Crimson Pro', serif", fontStyle: 'italic', fontSize: '14px', paddingTop: '2rem', textAlign: 'center' }}>
                    暂无数据
                  </div>
                )}
              </div>
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
