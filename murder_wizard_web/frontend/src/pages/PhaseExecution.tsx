import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import type { SSEEvent } from '../types/api'
const PHASE_LABELS = ['', '机制设计', '剧本创作', '视觉物料', '用户测试', '商业化', '印刷生产', '宣发内容', '社区运营']

type RunMode = 'phase' | 'expand' | 'audit'

export default function PhaseExecution() {
  const { name, stage } = useParams<{ name: string; stage: string }>()
  const navigate = useNavigate()
  const [running, setRunning] = useState(false)
  const [output, setOutput] = useState<Array<{ type: string; content: string }>>([])
  const [currentStep, setCurrentStep] = useState('')
  const [progress, setProgress] = useState(0)
  const [totalCost, setTotalCost] = useState(0)
  const [complete, setComplete] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [forceAudit, setForceAudit] = useState(false)
  const outputRef = useRef<HTMLDivElement>(null)
  const projectName = decodeURIComponent(name || '')
  const stageNum = parseInt(stage || '0')
  const mode: RunMode = stage === 'expand' ? 'expand' : stage === 'audit' ? 'audit' : 'phase'

  function appendOutput(type: string, content: string) {
    setOutput((prev) => {
      const next = [...prev, { type, content }]
      return next.length > 500 ? next.slice(-500) : next
    })
  }

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight
    }
  }, [output])

  async function startRun() {
    if (!projectName) return
    setRunning(true)
    setOutput([])
    setError(null)
    setComplete(false)
    setProgress(0)
    setCurrentStep('')
    setTotalCost(0)

    let url: string
    if (mode === 'expand') url = `/api/projects/${encodeURIComponent(projectName)}/expand`
    else if (mode === 'audit') url = `/api/projects/${encodeURIComponent(projectName)}/audit${forceAudit ? '?force=true' : ''}`
    else url = `/api/projects/${encodeURIComponent(projectName)}/phases/${stageNum}/run`

    const controller = new AbortController()
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
        signal: controller.signal,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }

      const reader = res.body?.getReader()
      if (!reader) throw new Error('No response body')
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.startsWith('event:') && !line.startsWith('data:')) continue
          const eventMatch = line.match(/^event: (\w+)/)
          const dataMatch = line.match(/^data: (.+)/)
          if (eventMatch && dataMatch) {
            handleEvent({ type: eventMatch[1], data: JSON.parse(dataMatch[1]) } as SSEEvent)
          }
        }
      }
    } catch (e: unknown) {
      if ((e as Error).name !== 'AbortError') {
        setError(e instanceof Error ? e.message : '运行失败')
      }
    } finally {
      setRunning(false)
      setComplete(true)
    }
  }

  function handleEvent(event: SSEEvent) {
    switch (event.type) {
      case 'start':
        appendOutput('system', `开始执行...`)
        break
      case 'progress':
        setCurrentStep(event.data.step as string)
        setProgress(event.data.percent as number)
        break
      case 'token':
        appendOutput('token', event.data.content as string)
        break
      case 'cost':
        setTotalCost(event.data.total_cost as number)
        break
      case 'artifact':
        appendOutput('system', `产物: ${event.data.filename}`)
        break
      case 'stage_complete':
        appendOutput('system', `阶段完成 · 消耗: $${(event.data.total_cost as number).toFixed(4)}`)
        setComplete(true)
        break
      case 'audit_complete':
        appendOutput('system', `审计完成 · 消耗: $${(event.data.total_cost as number).toFixed(4)}`)
        setComplete(true)
        break
      case 'expand_complete':
        appendOutput('system', `扩写完成 · 消耗: $${(event.data.total_cost as number).toFixed(4)}`)
        setComplete(true)
        break
      case 'error':
        appendOutput('error', `错误: ${event.data.message}`)
        setError(event.data.message as string)
        break
      case 'round_complete':
        appendOutput('system', `轮次完成 P0=${event.data.p0_count} P1=${event.data.p1_count}`)
        break
      case 'revision_complete':
        appendOutput('system', `已修复 P0=${event.data.fixed_p0} P1=${event.data.fixed_p1}`)
        break
      case 'end':
        break
    }
  }

  const title =
    mode === 'expand' ? '原型扩写' : mode === 'audit' ? '穿帮审计' : `阶段${stageNum}: ${PHASE_LABELS[stageNum] || ''}`

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-base)' }}>
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
          <h1
            style={{
              fontFamily: "'Playfair Display', serif",
              fontSize: '1.25rem',
              fontWeight: 500,
              color: 'var(--text-cream)',
              letterSpacing: '-0.01em',
            }}
          >
            {title}
          </h1>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          {mode === 'audit' && (
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontFamily: "'Crimson Pro', serif",
                fontSize: '13px',
                color: 'var(--text-muted)',
                cursor: 'pointer',
              }}
            >
              <input
                type="checkbox"
                checked={forceAudit}
                onChange={(e) => setForceAudit(e.target.checked)}
                style={{ accentColor: 'var(--accent-crimson)' }}
              />
              强制推进（忽略 P0）
            </label>
          )}
          {totalCost > 0 && (
            <span
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '12px',
                color: 'var(--text-faint)',
              }}
            >
              累计 ${totalCost.toFixed(4)}
            </span>
          )}
          {!running && !complete && (
            <button onClick={startRun} className="btn-primary" style={{ fontSize: '13px' }}>
              ▶ 开始执行
            </button>
          )}
          {running && (
            <span
              style={{
                fontFamily: "'Crimson Pro', serif",
                fontSize: '14px',
                color: 'var(--text-muted)',
                fontStyle: 'italic',
              }}
            >
              执行中...
            </span>
          )}
          {complete && !error && (
            <button onClick={startRun} className="btn-ghost" style={{ fontSize: '13px' }}>
              ↺ 重新运行
            </button>
          )}
        </div>
      </header>

      {/* Progress */}
      {(running || currentStep) && (
        <div
          style={{
            padding: '1rem 2rem',
            borderBottom: '1px solid var(--border-subtle)',
            background: 'var(--bg-raised)',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginBottom: '0.5rem',
              fontFamily: "'Crimson Pro', serif",
              fontSize: '13px',
              color: 'var(--text-faint)',
            }}
          >
            <span>{currentStep || '准备中...'}</span>
            <span>{progress}%</span>
          </div>
          <div
            style={{
              height: '2px',
              background: 'var(--border)',
              borderRadius: '1px',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                height: '100%',
                width: '100%',
                transform: `scaleX(${progress / 100})`,
                transformOrigin: 'left center',
                background: 'var(--accent-gold)',
                transition: 'transform 300ms ease-out',
              }}
            />
          </div>
        </div>
      )}

      {/* Output */}
      <div
        ref={outputRef}
        aria-live="polite"
        aria-atomic="false"
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '2rem',
          background: 'var(--bg-base)',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '13px',
          lineHeight: 1.75,
        }}
      >
        {!running && output.length === 0 && !complete && (
          <div style={{ textAlign: 'center', paddingTop: '4rem' }}>
            <div
              style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: '2.5rem',
                color: 'var(--border)',
                marginBottom: '1rem',
                lineHeight: 1,
              }}
            >
              ▸
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
              准备就绪
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
              点击「开始执行」运行 {title}
            </p>
            <button onClick={startRun} className="btn-primary">
              ▶ 开始执行
            </button>
          </div>
        )}

        {output.map((line, i) => (
          <div
            key={i}
            style={{
              color:
                line.type === 'error'
                  ? 'var(--output-error)'
                  : line.type === 'system'
                  ? 'var(--accent-gold)'
                  : 'var(--output-token)',
              marginBottom: '0.125rem',
              fontSize: line.type === 'system' ? '12px' : '13px',
            }}
          >
            {line.content}
          </div>
        ))}

        {running && output.length > 0 && (
          <span className="blink-cursor" style={{ color: 'var(--text-faint)' }}>
            ▌
          </span>
        )}
      </div>

      {/* Footer */}
      {complete && !error && (
        <div
          style={{
            padding: '1rem 2rem',
            borderTop: '1px solid var(--border)',
            background: 'var(--bg-raised)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span
            style={{
              fontFamily: "'Crimson Pro', serif",
              fontSize: '14px',
              color: 'var(--output-success)',
              fontStyle: 'italic',
            }}
          >
            ✓ 执行完成
          </span>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              onClick={() => navigate(`/projects/${encodeURIComponent(projectName)}/matrix`)}
              className="btn-ghost"
              style={{ fontSize: '13px' }}
            >
              信息矩阵
            </button>
            <button
              onClick={() => navigate(`/projects/${encodeURIComponent(projectName)}`)}
              className="btn-secondary"
              style={{ fontSize: '13px' }}
            >
              返回项目
            </button>
          </div>
        </div>
      )}

    </div>
  )
}
