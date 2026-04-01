import type { PlanInfo } from '../api/user'

interface UpgradePromptProps {
  trigger: 'project_limit' | 'audit' | 'expand' | 'cloud_sync'
  planInfo: PlanInfo
  onClose: () => void
  onUpgrade: () => void
}

export default function UpgradePrompt({ trigger, planInfo, onClose, onUpgrade }: UpgradePromptProps) {
  const messages: Record<string, string> = {
    project_limit: `你已达到免费版项目上限（${planInfo.project_limit}个），升级 Pro 解锁无限项目。`,
    audit: '完整穿帮审计需要 Pro 版本支持。',
    expand: '原型扩写为完整版需要 Pro 版本。',
    cloud_sync: '云端同步需要 Pro 版本。',
  }

  return (
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
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        style={{
          background: 'var(--bg-raised)',
          border: '1px solid var(--border)',
          width: '100%',
          maxWidth: '400px',
          padding: '3rem',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            fontFamily: "'Playfair Display', serif",
            fontSize: '1.5rem',
            color: 'var(--accent-gold)',
            marginBottom: '1rem',
          }}
        >
          升级到 Pro
        </div>
        <p
          style={{
            fontFamily: "'Crimson Pro', serif",
            fontSize: '15px',
            color: 'var(--text-muted)',
            marginBottom: '2rem',
          }}
        >
          {messages[trigger] || '升级 Pro 解锁全部功能。'}
        </p>
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
          <button onClick={onUpgrade} className="btn-primary" style={{ fontSize: '13px' }}>
            升级
          </button>
          <button onClick={onClose} className="btn-ghost" style={{ fontSize: '13px' }}>
            关闭
          </button>
        </div>
      </div>
    </div>
  )
}
