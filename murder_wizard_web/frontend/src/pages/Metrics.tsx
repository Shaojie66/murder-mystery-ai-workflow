import { useState, useEffect, lazy } from 'react'

// Lazy load the entire Recharts module as a namespace
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const Recharts: any = lazy(() => import('recharts') as any)

interface AnalyticsSummary {
  total_events: number
  page_views: number
  email_submissions: number
  modal_opens: number
  cta_clicks: number
  scroll_50: number
  scroll_100: number
  variant_a: number
  variant_b: number
  avg_duration: number
  conversion_rate_a: number
  conversion_rate_b: number
}

interface RawEvent {
  event: string
  variant?: string
  url?: string
  duration?: number
  timestamp: string
  props?: Record<string, unknown>
}

interface EventsResponse {
  events: RawEvent[]
  total: number
  summary: AnalyticsSummary
}

async function fetchAnalytics(): Promise<EventsResponse> {
  const res = await fetch('/api/analytics/events?limit=100')
  if (!res.ok) throw new Error('获取分析数据失败')
  return res.json()
}

export default function Metrics() {
  const [data, setData] = useState<EventsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    fetchAnalytics()
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '加载失败'))
      .finally(() => setLoading(false))
  }, [refreshKey])

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

  if (!data) return null

  const s = data.summary
  const hasData = s.total_events > 0

  const conversionData = [
    { name: 'A (技术向)', rate: s.conversion_rate_a || 0, color: '#9B1C1C' },
    { name: 'B (引导式)', rate: s.conversion_rate_b || 0, color: '#B45309' },
  ]

  const eventFunnelData = [
    { name: '页面访问', count: s.page_views, color: '#78716C' },
    { name: '滚动50%', count: s.scroll_50, color: '#B45309' },
    { name: '滚动100%', count: s.scroll_100, color: '#92400E' },
    { name: '弹窗打开', count: s.modal_opens, color: '#C77A08' },
    { name: '邮箱提交', count: s.email_submissions, color: '#9B1C1C' },
  ]

  const variantData = [
    { name: 'A (技术向)', visitors: s.variant_a, color: '#9B1C1C' },
    { name: 'B (引导式)', visitors: s.variant_b, color: '#B45309' },
  ]

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
            A/B Test
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
            落地页统计
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
            /landing A vs /landing B 转化率对比
          </p>
        </div>

        <button
          onClick={() => setRefreshKey((k) => k + 1)}
          className="btn-ghost"
          style={{ fontSize: '13px' }}
        >
          刷新
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
                <rect x="3" y="12" width="4" height="9" rx="1"/>
                <rect x="10" y="8" width="4" height="13" rx="1"/>
                <rect x="17" y="4" width="4" height="17" rx="1"/>
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
              暂无统计数据
            </h2>
            <p
              style={{
                fontFamily: "'Crimson Pro', serif",
                fontSize: '16px',
                color: 'var(--text-muted)',
                fontStyle: 'italic',
              }}
            >
              访问落地页后将在此显示 A/B 测试数据
            </p>
          </div>
        )}

        {hasData && (
          <>
            {/* Key metrics */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: '1px',
                marginBottom: '3rem',
                border: '1px solid var(--border)',
                background: 'var(--border-subtle)',
              }}
            >
              {[
                { label: '页面访问', value: s.page_views, accent: 'var(--text-cream)' },
                { label: '邮箱提交', value: s.email_submissions, accent: 'var(--accent-crimson)' },
                { label: 'A 转化率', value: `${s.conversion_rate_a.toFixed(2)}%`, accent: '#9B1C1C' },
                { label: 'B 转化率', value: `${s.conversion_rate_b.toFixed(2)}%`, accent: '#B45309' },
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

            {/* Conversion rate comparison */}
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
              {/* Conversion bar chart */}
              <div style={{ padding: '1.75rem', background: 'var(--bg-raised)' }}>
                <div className="label" style={{ marginBottom: '1.25rem', color: 'var(--text-faint)' }}>
                  转化率对比
                </div>
                <Recharts.ResponsiveContainer width="100%" height={180}>
                  <Recharts.BarChart data={conversionData} layout="vertical">
                    <Recharts.XAxis type="number" stroke="var(--text-faint)" fontSize={11} tickFormatter={(v: number) => `${v.toFixed(1)}%`} />
                    <Recharts.YAxis dataKey="name" type="category" width={70} stroke="var(--text-faint)" fontSize={10} />
                    <Recharts.Tooltip
                      formatter={(v: number) => [`${v.toFixed(2)}%`, '转化率']}
                      contentStyle={{
                        backgroundColor: 'var(--bg-elevated)',
                        border: '1px solid var(--border)',
                        borderRadius: '2px',
                        fontFamily: "'Crimson Pro', serif",
                        fontSize: '13px',
                        color: 'var(--text-cream)',
                      }}
                    />
                    <Recharts.Bar dataKey="rate" radius={[0, 2, 2, 0]}>
                      {conversionData.map((entry, index) => (
                        <Recharts.Cell key={index} fill={entry.color} />
                      ))}
                    </Recharts.Bar>
                  </Recharts.BarChart>
                </Recharts.ResponsiveContainer>
              </div>

              {/* Variant distribution */}
              <div style={{ padding: '1.75rem', background: 'var(--bg-raised)' }}>
                <div className="label" style={{ marginBottom: '1.25rem', color: 'var(--text-faint)' }}>
                  访客分布
                </div>
                <Recharts.ResponsiveContainer width="100%" height={180}>
                  <Recharts.BarChart data={variantData} layout="vertical">
                    <Recharts.XAxis type="number" stroke="var(--text-faint)" fontSize={11} />
                    <Recharts.YAxis dataKey="name" type="category" width={70} stroke="var(--text-faint)" fontSize={10} />
                    <Recharts.Tooltip
                      formatter={(v: number) => [v, '访客']}
                      contentStyle={{
                        backgroundColor: 'var(--bg-elevated)',
                        border: '1px solid var(--border)',
                        borderRadius: '2px',
                        fontFamily: "'Crimson Pro', serif",
                        fontSize: '13px',
                        color: 'var(--text-cream)',
                      }}
                    />
                    <Recharts.Bar dataKey="visitors" radius={[0, 2, 2, 0]}>
                      {variantData.map((entry, index) => (
                        <Recharts.Cell key={index} fill={entry.color} />
                      ))}
                    </Recharts.Bar>
                  </Recharts.BarChart>
                </Recharts.ResponsiveContainer>
              </div>
            </div>

            {/* Event funnel */}
            <div
              style={{
                border: '1px solid var(--border)',
                background: 'var(--bg-raised)',
                marginBottom: '2rem',
              }}
            >
              <div
                style={{
                  padding: '1rem 1.5rem',
                  borderBottom: '1px solid var(--border-subtle)',
                }}
              >
                <div className="label" style={{ color: 'var(--text-faint)' }}>
                  事件漏斗
                </div>
              </div>

              <div style={{ padding: '1.5rem' }}>
                <Recharts.ResponsiveContainer width="100%" height={200}>
                  <Recharts.BarChart data={eventFunnelData}>
                    <Recharts.XAxis dataKey="name" stroke="var(--text-faint)" fontSize={11} />
                    <Recharts.YAxis stroke="var(--text-faint)" fontSize={11} />
                    <Recharts.Tooltip
                      formatter={(v: number) => [v, '次数']}
                      contentStyle={{
                        backgroundColor: 'var(--bg-elevated)',
                        border: '1px solid var(--border)',
                        borderRadius: '2px',
                        fontFamily: "'Crimson Pro', serif",
                        fontSize: '13px',
                        color: 'var(--text-cream)',
                      }}
                    />
                    <Recharts.Bar dataKey="count" radius={[2, 2, 0, 0]}>
                      {eventFunnelData.map((entry, index) => (
                        <Recharts.Cell key={index} fill={entry.color} />
                      ))}
                    </Recharts.Bar>
                  </Recharts.BarChart>
                </Recharts.ResponsiveContainer>
              </div>
            </div>

            {/* Recent events */}
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
                  最近事件 ({data.total} 条)
                </div>
              </div>

              <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                {data.events.slice().reverse().map((ev, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '1rem',
                      padding: '0.75rem 1.5rem',
                      borderBottom: '1px solid var(--border-subtle)',
                    }}
                  >
                    <span
                      style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: '10px',
                        color: 'var(--text-faint)',
                        minWidth: '140px',
                      }}
                    >
                      {new Date(ev.timestamp).toLocaleTimeString('zh-CN')}
                    </span>
                    <span
                      style={{
                        fontFamily: "'Crimson Pro', serif",
                        fontSize: '13px',
                        color: 'var(--text-cream)',
                        background: 'var(--accent-gold-subtle)',
                        padding: '2px 8px',
                        borderRadius: '2px',
                      }}
                    >
                      {ev.event}
                    </span>
                    {ev.variant && (
                      <span
                        style={{
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: '10px',
                          color: ev.variant === 'a' ? '#9B1C1C' : '#B45309',
                        }}
                      >
                        {ev.variant.toUpperCase()}
                      </span>
                    )}
                    <span
                      style={{
                        fontFamily: "'Crimson Pro', serif",
                        fontSize: '12px',
                        color: 'var(--text-faint)',
                        fontStyle: 'italic',
                      }}
                    >
                      {ev.url}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
