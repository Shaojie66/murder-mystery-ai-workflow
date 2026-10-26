import { useState, useEffect, useMemo } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { request } from '../api/client'
import { useProjectWorkbenchContext } from '../components/layout/ProjectWorkbenchLayout'
import { parseAuditReport } from './auditReport'
import type { AuditIssue, ParsedAudit } from './auditReport'

const STATUS_TONE: Record<string, { color: string; glyph: string }> = {
  blocked: { color: 'var(--output-error)', glyph: '●' },
  incomplete: { color: 'var(--accent-gold)', glyph: '◐' },
  waived: { color: 'var(--accent-gold)', glyph: '◑' },
  passed: { color: 'var(--green-status)', glyph: '○' },
}

const ROUND_WORD: Record<string, string> = {
  ok: '已完成', truncated: '被截断', parse_error: '无法解析', call_failed: '调用失败', render_failed: '渲染失败', not_run: '未运行',
}

function CopyKey({ line }: { line: string }) {
  const [done, setDone] = useState(false)
  return (
    <button
      type="button"
      className="audit-copy"
      aria-label="复制 .known_p0 豁免行"
      onClick={() => {
        navigator.clipboard?.writeText(line).then(() => {
          setDone(true)
          window.setTimeout(() => setDone(false), 1800)
        })
      }}
    >
      {done ? '已复制' : '复制豁免行'}
    </button>
  )
}

function IssueRow({ issue }: { issue: AuditIssue }) {
  return (
    <li className="audit-issue" data-waived={issue.waived || undefined}>
      <div className="audit-issue-id">
        <span className="audit-sev">{issue.severity}</span>
        <span className="audit-ref">{issue.ref}</span>
      </div>
      <div className="audit-issue-body">
        <p className="audit-issue-title">
          {issue.dimension}
          {issue.waived && <span className="audit-tag">已豁免</span>}
        </p>
        <p className="audit-issue-problem">{issue.problem}</p>
        {issue.quote && <blockquote className="audit-quote">“{issue.quote}”</blockquote>}
        <p className="audit-issue-meta">
          {issue.location}
          {issue.verify && issue.verify !== 'verified' && <span className="audit-tag audit-tag-warn">定位未能校验：{issue.verify}</span>}
          {(issue.characters !== '-' || issue.events !== '-') && (
            <span> · 角色 {issue.characters} · 事件 {issue.events}</span>
          )}
        </p>
        {issue.suggestion && issue.suggestion !== '-' && <p className="audit-issue-fix">建议：{issue.suggestion}</p>}
        {issue.waived && issue.waiverNote && <p className="audit-issue-fix">豁免依据：{issue.waiverNote}</p>}
        <div className="audit-issue-actions">
          <code className="audit-key">{issue.key}</code>
          {!issue.waived && issue.waiverLine && <CopyKey line={issue.waiverLine} />}
        </div>
      </div>
    </li>
  )
}

function Verdict({ a }: { a: ParsedAudit }) {
  const tone = STATUS_TONE[a.status]
  const counts = a.groups.reduce<Record<string, number>>((m, g) => ({ ...m, [g.title]: g.issues.length }), {})
  return (
    <section className="audit-verdict" aria-labelledby="audit-verdict-title">
      <div>
        <p className="label" style={{ marginBottom: '0.5rem' }}>审计结论</p>
        <h2 id="audit-verdict-title" className="audit-verdict-word" style={{ color: tone.color }}>
          <span aria-hidden="true">{tone.glyph}</span> {a.statusLabel}
        </h2>
        <p className="audit-verdict-line">{a.conclusion}</p>
        {a.caveat && <p className="audit-caveat">{a.caveat}</p>}
      </div>
      <dl className="audit-meta">
        <div><dt>未豁免 P0</dt><dd>{counts['未豁免 P0'] ?? 0}</dd></div>
        <div><dt>已豁免 P0</dt><dd>{counts['已豁免 P0'] ?? 0}</dd></div>
        <div><dt>P1 / P2</dt><dd>{counts['P1'] ?? 0} / {counts['P2'] ?? 0}</dd></div>
        <div><dt>作品状态</dt><dd>{a.workState || '—'}</dd></div>
        <div><dt>模型</dt><dd>{a.model || '—'}</dd></div>
        <div><dt>生成时间</dt><dd>{a.generatedAt || '—'}</dd></div>
      </dl>
    </section>
  )
}

function AuditReportView({ a, raw }: { a: ParsedAudit; raw: string }) {
  const byTitle = (t: string) => a.groups.find((g) => g.title === t)?.issues ?? []
  const open = [...byTitle('未豁免 P0'), ...byTitle('已豁免 P0')]
  const minor = [...byTitle('P1'), ...byTitle('P2')]
  return (
    <div className="audit-page">
      <Verdict a={a} />

      {a.problems.length > 0 && (
        <section className="audit-block">
          <h3 className="audit-h">没能开始审计的原因</h3>
          <ul className="audit-plain">{a.problems.map((p) => <li key={p}>{p}</li>)}</ul>
        </section>
      )}

      <section className="audit-block" aria-labelledby="audit-rounds">
        <h3 className="audit-h" id="audit-rounds">三轮审计</h3>
        <ol className="audit-rounds">
          {a.rounds.map((r) => (
            <li key={r.title} data-bad={r.status !== 'ok' || undefined}>
              <p className="audit-round-title">{r.title}</p>
              <p className="audit-round-status">{ROUND_WORD[r.status] ?? r.status}</p>
              <p className="audit-round-counts">P0 {r.p0} · P1 {r.p1} · P2 {r.p2}</p>
              {r.reason && <p className="audit-round-reason">{r.reason}</p>}
            </li>
          ))}
        </ol>
      </section>

      {open.length > 0 && (
        <section className="audit-block" aria-labelledby="audit-p0">
          <h3 className="audit-h" id="audit-p0">P0 · 必须处理</h3>
          <ul className="audit-issues">{open.map((i) => <IssueRow key={i.ref + i.key} issue={i} />)}</ul>
          <p className="audit-hint">确认可接受的 P0，复制豁免行加进项目目录的 <code>.known_p0</code>，补上理由，重新审计即可按键豁免。</p>
        </section>
      )}

      {minor.length > 0 && (
        <details className="audit-block audit-details">
          <summary>P1 / P2 · 建议处理（{minor.length}）</summary>
          <ul className="audit-issues">{minor.map((i) => <IssueRow key={i.ref + i.key} issue={i} />)}</ul>
        </details>
      )}

      {a.patches.length > 0 && (
        <details className="audit-block audit-details">
          <summary>修复建议（{a.patches.length}）· 未写入作品</summary>
          <ul className="audit-plain">
            {a.patches.map((p) => (
              <li key={p.id} className="audit-patch">
                <p className="audit-issue-title">{p.id} · {p.heading}<span className="audit-tag">{p.state}</span></p>
                <div className="audit-diff">
                  <div><span>原文</span><pre>{p.original}</pre></div>
                  <div><span>建议改为</span><pre>{p.replacement}</pre></div>
                </div>
                {p.rationale && <p className="audit-issue-fix">{p.rationale}</p>}
              </li>
            ))}
          </ul>
          <p className="audit-hint">只有在命令行交互终端里审计、并由你选中编号后才会写入，写入前自动备份。</p>
        </details>
      )}

      <details className="audit-block audit-details" open={a.problems.length > 0 || undefined}>
        <summary>审计输入（{a.materials.length} 份）</summary>
        <div className="audit-table-wrap">
          <table className="audit-table">
            <thead><tr><th>文件</th><th>参与轮次</th><th>字数</th><th>sha12</th><th>状态</th></tr></thead>
            <tbody>
              {a.materials.map((m) => (
                <tr key={m.file}><td>{m.file}</td><td>{m.rounds}</td><td>{m.chars}</td><td><code>{m.sha}</code></td><td>{m.state}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        {a.notCovered && <p className="audit-hint">未覆盖：{a.notCovered}</p>}
      </details>

      {(a.waiverSummary.length > 0 || a.notes.length > 0) && (
        <details className="audit-block audit-details">
          <summary>豁免情况与说明</summary>
          <ul className="audit-plain">
            {[...a.waiverSummary, ...a.notes].map((t, i) => <li key={i}>{t}</li>)}
          </ul>
        </details>
      )}

      <details className="audit-block audit-details">
        <summary>报告原文（audit_report.md）</summary>
        <pre className="audit-raw">{raw}</pre>
      </details>
    </div>
  )
}

export default function AuditView() {
  const navigate = useNavigate()
  const { projectName, project } = useProjectWorkbenchContext()
  const [report, setReport] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const parsed = useMemo(() => (report ? parseAuditReport(report) : null), [report])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!projectName) return
    request<{ content: string }>(`/projects/${encodeURIComponent(projectName)}/audit/report`)
      .then((reportData) => {
        setReport(reportData.content)
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
      <div style={{ maxWidth: '960px', margin: '0 auto', padding: 'clamp(1.5rem, 4vw, 3rem)' }}>
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
        ) : report && parsed ? (
          <AuditReportView a={parsed} raw={report} />
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
