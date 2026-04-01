import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getSettings,
  updateSettings,
  testLLMConnection,
  testNotionConnection,
  testObsidianConnection,
  type Settings,
  type LLMConfig,
  type NotionConfig,
  type ObsidianConfig,
} from '../api/settings'

const LLM_PROVIDERS = [
  { value: 'minimax', label: 'MiniMax' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'claude', label: 'Claude' },
  { value: 'ollama', label: 'Ollama (本地)' },
]

export default function Settings() {
  const navigate = useNavigate()
  const [settings, setSettings] = useState<Settings>({
    llm: { provider: 'minimax', api_key: null, base_url: null, model: null },
    notion: { enabled: false, api_key: null, database_id: null },
    obsidian: { enabled: false, vault_path: null },
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [testing, setTesting] = useState<string | null>(null)

  useEffect(() => {
    loadSettings()
  }, [])

  async function loadSettings() {
    try {
      setLoading(true)
      const data = await getSettings()
      setSettings(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载设置失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    try {
      setSaving(true)
      setError(null)
      setSuccess(null)
      await updateSettings(settings)
      setSuccess('设置已保存')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  async function handleTestLLM() {
    try {
      setTesting('llm')
      setError(null)
      const result = await testLLMConnection(settings)
      if (result.success) {
        setSuccess(`连接成功！模型: ${result.model}`)
      }
    } catch (e: unknown) {
      setError(`LLM 连接失败: ${e instanceof Error ? e.message : '未知错误'}`)
    } finally {
      setTesting(null)
    }
  }

  async function handleTestNotion() {
    try {
      setTesting('notion')
      setError(null)
      await testNotionConnection(settings.notion)
      setSuccess('Notion 连接成功！')
    } catch (e: unknown) {
      setError(`Notion 连接失败: ${e instanceof Error ? e.message : '未知错误'}`)
    } finally {
      setTesting(null)
    }
  }

  async function handleTestObsidian() {
    try {
      setTesting('obsidian')
      setError(null)
      await testObsidianConnection(settings.obsidian)
      setSuccess('Obsidian 连接成功！')
    } catch (e: unknown) {
      setError(`Obsidian 连接失败: ${e instanceof Error ? e.message : '未知错误'}`)
    } finally {
      setTesting(null)
    }
  }

  function updateLLM(updates: Partial<LLMConfig>) {
    setSettings(s => ({ ...s, llm: { ...s.llm, ...updates } }))
  }

  function updateNotion(updates: Partial<NotionConfig>) {
    setSettings(s => ({ ...s, notion: { ...s.notion, ...updates } }))
  }

  function updateObsidian(updates: Partial<ObsidianConfig>) {
    setSettings(s => ({ ...s, obsidian: { ...s.obsidian, ...updates } }))
  }

  if (loading) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        加载中...
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
          background: 'var(--bg-base)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <button
            onClick={() => navigate('/')}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              fontFamily: "'Crimson Pro', serif",
              fontSize: '14px',
              marginBottom: '0.5rem',
              padding: 0,
            }}
          >
            ← 返回
          </button>
          <h1
            style={{
              fontFamily: "'Playfair Display', serif",
              fontSize: '1.75rem',
              fontWeight: 500,
              color: 'var(--text-cream)',
              letterSpacing: '-0.01em',
              margin: 0,
            }}
          >
            设置
          </h1>
        </div>
        <button
          type="submit"
          form="settings-form"
          disabled={saving}
          className="btn-primary"
        >
          {saving ? '保存中...' : '保存设置'}
        </button>
      </header>

      <div style={{ maxWidth: '640px', margin: '0 auto', padding: '2rem 3rem 4rem' }}>
        {/* Alerts */}
        {error && (
          <div
            role="alert"
            aria-live="polite"
            style={{
              padding: '1rem',
              background: 'rgba(220,38,38,0.1)',
              border: '1px solid rgba(220,38,38,0.3)',
              color: 'var(--output-error)',
              fontFamily: "'Crimson Pro', serif",
              marginBottom: '1.5rem',
            }}
          >
            {error}
          </div>
        )}
        {success && (
          <div
            role="status"
            aria-live="polite"
            style={{
              padding: '1rem',
              background: 'rgba(34,197,94,0.1)',
              border: '1px solid rgba(34,197,94,0.3)',
              color: 'var(--output-success)',
              fontFamily: "'Crimson Pro', serif",
              marginBottom: '1.5rem',
            }}
          >
            {success}
          </div>
        )}

        <form id="settings-form" onSubmit={handleSave}>
          {/* LLM Settings */}
          <section style={{ marginBottom: '3rem' }}>
            <h2
              style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: '1.25rem',
                fontWeight: 500,
                color: 'var(--text-cream)',
                marginBottom: '1.5rem',
                paddingBottom: '0.75rem',
                borderBottom: '1px solid var(--border-subtle)',
              }}
            >
              LLM 提供商
            </h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Provider */}
              <div>
                <label
                  htmlFor="llm-provider"
                  className="label"
                  style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-faint)' }}
                >
                  提供商
                </label>
                <select
                  id="llm-provider"
                  value={settings.llm.provider}
                  onChange={(e) => updateLLM({ provider: e.target.value })}
                  style={{ width: '100%' }}
                >
                  {LLM_PROVIDERS.map(p => (
                    <option key={p.value} value={p.value}>{p.label}</option>
                  ))}
                </select>
              </div>

              {/* API Key */}
              <div>
                <label
                  className="label"
                  style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-faint)' }}
                >
                  API Key
                </label>
                <input
                  type="password"
                  value={settings.llm.api_key || ''}
                  onChange={(e) => updateLLM({ api_key: e.target.value || null })}
                  placeholder={settings.llm.provider === 'ollama' ? '可选（本地无需认证）' : '输入 API Key'}
                  style={{ width: '100%' }}
                />
              </div>

              {/* Base URL */}
              {settings.llm.provider === 'ollama' && (
                <div>
                  <label
                    className="label"
                    style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-faint)' }}
                  >
                    服务器地址
                  </label>
                  <input
                    type="text"
                    value={settings.llm.base_url || ''}
                    onChange={(e) => updateLLM({ base_url: e.target.value || null })}
                    placeholder="http://localhost:11434/v1"
                    style={{ width: '100%' }}
                  />
                </div>
              )}

              {/* Model */}
              <div>
                <label
                  className="label"
                  style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-faint)' }}
                >
                  模型
                </label>
                <input
                  type="text"
                  value={settings.llm.model || ''}
                  onChange={(e) => updateLLM({ model: e.target.value || null })}
                  placeholder={
                    settings.llm.provider === 'minimax' ? 'MiniMax-M2.7' :
                    settings.llm.provider === 'openai' ? 'gpt-4o' :
                    settings.llm.provider === 'claude' ? 'claude-3-5-sonnet-20241022' :
                    'llama3'
                  }
                  style={{ width: '100%' }}
                />
              </div>

              {/* Test Button */}
              <div>
                <button
                  type="button"
                  onClick={handleTestLLM}
                  disabled={testing === 'llm'}
                  className="btn-ghost"
                  style={{ fontSize: '13px' }}
                >
                  {testing === 'llm' ? '测试中...' : '测试连接'}
                </button>
              </div>
            </div>
          </section>

          {/* Notion Settings */}
          <section style={{ marginBottom: '3rem' }}>
            <h2
              style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: '1.25rem',
                fontWeight: 500,
                color: 'var(--text-cream)',
                marginBottom: '1.5rem',
                paddingBottom: '0.75rem',
                borderBottom: '1px solid var(--border-subtle)',
              }}
            >
              Notion 集成
            </h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Enable */}
              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={settings.notion.enabled}
                    onChange={(e) => updateNotion({ enabled: e.target.checked })}
                    style={{ width: '16px', height: '16px', accentColor: 'var(--accent-crimson)' }}
                  />
                  <span style={{ fontFamily: "'Crimson Pro', serif", color: 'var(--text-cream)' }}>
                    启用 Notion 同步
                  </span>
                </label>
              </div>

              {settings.notion.enabled && (
                <>
                  {/* API Key */}
                  <div>
                    <label
                      className="label"
                      style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-faint)' }}
                    >
                      Notion API Key
                    </label>
                    <input
                      type="password"
                      value={settings.notion.api_key || ''}
                      onChange={(e) => updateNotion({ api_key: e.target.value || null })}
                      placeholder="secret_xxx"
                      style={{ width: '100%' }}
                    />
                  </div>

                  {/* Database ID */}
                  <div>
                    <label
                      className="label"
                      style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-faint)' }}
                    >
                      Database ID
                    </label>
                    <input
                      type="text"
                      value={settings.notion.database_id || ''}
                      onChange={(e) => updateNotion({ database_id: e.target.value || null })}
                      placeholder="数据库 ID"
                      style={{ width: '100%' }}
                    />
                  </div>

                  {/* Test Button */}
                  <div>
                    <button
                      type="button"
                      onClick={handleTestNotion}
                      disabled={testing === 'notion'}
                      className="btn-ghost"
                      style={{ fontSize: '13px' }}
                    >
                      {testing === 'notion' ? '测试中...' : '测试连接'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </section>

          {/* Obsidian Settings */}
          <section style={{ marginBottom: '3rem' }}>
            <h2
              style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: '1.25rem',
                fontWeight: 500,
                color: 'var(--text-cream)',
                marginBottom: '1.5rem',
                paddingBottom: '0.75rem',
                borderBottom: '1px solid var(--border-subtle)',
              }}
            >
              Obsidian 集成
            </h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Enable */}
              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={settings.obsidian.enabled}
                    onChange={(e) => updateObsidian({ enabled: e.target.checked })}
                    style={{ width: '16px', height: '16px', accentColor: 'var(--accent-crimson)' }}
                  />
                  <span style={{ fontFamily: "'Crimson Pro', serif", color: 'var(--text-cream)' }}>
                    启用 Obsidian 同步
                  </span>
                </label>
              </div>

              {settings.obsidian.enabled && (
                <>
                  {/* Vault Path */}
                  <div>
                    <label
                      className="label"
                      style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-faint)' }}
                    >
                      Vault 路径
                    </label>
                    <input
                      type="text"
                      value={settings.obsidian.vault_path || ''}
                      onChange={(e) => updateObsidian({ vault_path: e.target.value || null })}
                      placeholder="/Users/你的用户名/Documents/我的笔记库"
                      style={{ width: '100%' }}
                    />
                  </div>

                  {/* Test Button */}
                  <div>
                    <button
                      type="button"
                      onClick={handleTestObsidian}
                      disabled={testing === 'obsidian'}
                      className="btn-ghost"
                      style={{ fontSize: '13px' }}
                    >
                      {testing === 'obsidian' ? '测试中...' : '测试连接'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </section>
        </form>
      </div>
    </div>
  )
}
