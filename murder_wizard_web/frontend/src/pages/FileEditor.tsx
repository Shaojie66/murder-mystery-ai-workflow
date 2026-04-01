import { useState, useEffect, lazy, Suspense } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { getFile, saveFile, listFiles } from '../api/files'

// Lazy load Monaco — only loaded when user opens the file editor
const Editor = lazy(() => import('@monaco-editor/react'))

type ViewMode = 'edit' | 'preview'

export default function FileEditor() {
  const { name, filename } = useParams<{ name: string; filename: string }>()
  const navigate = useNavigate()
  const projectName = decodeURIComponent(name || '')
  const fileName = decodeURIComponent(filename || '')
  const [content, setContent] = useState('')
  const [originalContent, setOriginalContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('edit')
  const [files, setFiles] = useState<string[]>([])
  const isMarkdown = fileName.endsWith('.md')
  const isJson = fileName.endsWith('.json')
  const hasChanges = content !== originalContent

  useEffect(() => {
    if (!projectName || !fileName) return
    setLoading(true)
    Promise.all([getFile(projectName, fileName), listFiles(projectName)])
      .then(([fileData, filesData]) => {
        setContent(fileData.content)
        setOriginalContent(fileData.content)
        setFiles(filesData.files.map((f) => f.name))
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : '加载失败')
      })
      .finally(() => setLoading(false))
  }, [projectName, fileName])

  async function handleSave() {
    if (!projectName || !fileName) return
    setSaving(true)
    setSaved(false)
    try {
      await saveFile(projectName, fileName, content)
      setOriginalContent(content)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault()
      handleSave()
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
          }}
        >
          {error}
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-base)' }} onKeyDown={handleKeyDown}>
      {/* Header */}
      <header
        style={{
          padding: '0.875rem 1.5rem',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-raised)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: 0 }}>
          <button
            onClick={() => navigate(`/projects/${encodeURIComponent(projectName)}`)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-faint)',
              cursor: 'pointer',
              fontFamily: "'Crimson Pro', serif",
              fontSize: '13px',
              padding: 0,
              flexShrink: 0,
              transition: 'color 150ms',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-cream)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-faint)')}
          >
            ←
          </button>
          <span style={{ color: 'var(--border)', fontSize: '11px', flexShrink: 0 }}>/</span>
          <span
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '13px',
              color: 'var(--text-muted)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {fileName}
          </span>
          {hasChanges && (
            <span
              style={{
                fontFamily: "'Crimson Pro', serif",
                fontSize: '12px',
                color: 'var(--accent-gold)',
                flexShrink: 0,
                fontStyle: 'italic',
              }}
            >
              已修改
            </span>
          )}
          {saved && (
            <span
              style={{
                fontFamily: "'Crimson Pro', serif",
                fontSize: '12px',
                color: 'var(--output-success)',
                flexShrink: 0,
              }}
            >
              ✓ 已保存
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', flexShrink: 0 }}>
          {/* File switcher */}
          <select
            value={fileName}
            onChange={(e) =>
              navigate(`/projects/${encodeURIComponent(projectName)}/files/${e.target.value}`)
            }
            style={{
              padding: '0.375rem 0.625rem',
              fontSize: '13px',
              maxWidth: '200px',
            }}
          >
            {files.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>

          {/* View mode toggle */}
          {isMarkdown && (
            <div
              style={{
                display: 'flex',
                border: '1px solid var(--border)',
                overflow: 'hidden',
              }}
            >
              {(['edit', 'preview'] as ViewMode[]).map((m) => (
                <button
                  key={m}
                  onClick={() => setViewMode(m)}
                  style={{
                    padding: '0.375rem 0.75rem',
                    fontSize: '12px',
                    fontFamily: "'Crimson Pro', serif",
                    background: viewMode === m ? 'var(--bg-elevated)' : 'transparent',
                    border: 'none',
                    borderRight: m === 'edit' ? '1px solid var(--border)' : 'none',
                    color: viewMode === m ? 'var(--text-cream)' : 'var(--text-faint)',
                    cursor: 'pointer',
                    transition: 'all 150ms',
                  }}
                >
                  {m === 'edit' ? '编辑' : '预览'}
                </button>
              ))}
            </div>
          )}

          {/* Save */}
          <button
            onClick={handleSave}
            disabled={!hasChanges || saving}
            style={{
              padding: '0.375rem 1rem',
              fontSize: '13px',
              fontFamily: "'Crimson Pro', serif",
              background: hasChanges ? 'var(--accent-crimson)' : 'transparent',
              border: '1px solid var(--accent-crimson)',
              color: hasChanges ? 'var(--text-cream)' : 'var(--text-faint)',
              cursor: hasChanges ? 'pointer' : 'not-allowed',
              opacity: saving ? 0.6 : 1,
              transition: 'all 150ms',
              letterSpacing: '0.02em',
            }}
          >
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </header>

      {/* Editor / Preview */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {viewMode === 'edit' ? (
          <Suspense fallback={<div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-faint)', fontFamily: "'Crimson Pro', serif", fontStyle: 'italic' }}>加载编辑器...</div>}>
            <Editor
              height="100%"
              language={isJson ? 'json' : 'markdown'}
              value={content}
              onChange={(v) => setContent(v || '')}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                fontFamily: "'JetBrains Mono', monospace",
                lineNumbers: 'on',
                wordWrap: 'on',
                automaticLayout: true,
                scrollBeyondLastLine: false,
                padding: { top: 16, bottom: 16 },
                renderLineHighlight: 'line',
                scrollbar: { verticalScrollbarSize: 5 },
              }}
            />
          </Suspense>
        ) : (
          <div
            style={{
              height: '100%',
              overflowY: 'auto',
              padding: '3rem',
              background: 'var(--bg-base)',
            }}
          >
            <div
              style={{
                maxWidth: '680px',
                margin: '0 auto',
                fontFamily: "'Crimson Pro', serif",
                fontSize: '17px',
                lineHeight: 1.75,
                color: 'var(--text-muted)',
              }}
            >
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
