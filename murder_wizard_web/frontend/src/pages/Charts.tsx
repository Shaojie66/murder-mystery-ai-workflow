import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

const COLORS = ['#9B1C1C', '#B45309', '#78716C', '#44403C', '#292524', '#A89F94']

interface OpChart {
  name: string
  cost: number
  tokens: number
  count: number
}

interface ModelChart {
  name: string
  cost: number
}

interface ChartsProps {
  byOperationChart: OpChart[]
  byModelChart: ModelChart[]
  formatCost: (c: number) => string
}

export default function Charts({ byOperationChart, byModelChart, formatCost }: ChartsProps) {
  return (
    <>
      {/* By operation */}
      <div style={{ padding: '1.75rem', background: 'var(--bg-raised)' }}>
        <div className="label" style={{ marginBottom: '1.25rem', color: 'var(--text-faint)' }}>
          各阶段消耗
        </div>
        {byOperationChart.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={byOperationChart} layout="vertical">
              <XAxis
                type="number"
                tickFormatter={(v) => `$${v.toFixed(2)}`}
                stroke="var(--text-faint)"
                fontSize={11}
                tick={{ fontFamily: "'Crimson Pro', serif" }}
              />
              <YAxis
                dataKey="name"
                type="category"
                width={100}
                stroke="var(--text-faint)"
                fontSize={10}
                tick={{ fontFamily: "'Crimson Pro', serif", fill: 'var(--text-muted)' }}
              />
              <Tooltip
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
              <Bar dataKey="cost" fill="var(--accent-gold)" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
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
            <ResponsiveContainer width={120} height={120}>
              <PieChart>
                <Pie
                  data={byModelChart}
                  dataKey="cost"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={32}
                >
                  {byModelChart.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
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
    </>
  )
}
