import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

interface Subscription {
  status: 'active' | 'canceled' | 'past_due' | 'trialing' | 'none'
  plan: 'pro' | 'free'
  current_period_end: string | null
  cancel_at_period_end: boolean
}

const PLAN_FEATURES = [
  '云端项目存储（无限项目）',
  '团队协作（最多 10 人）',
  'AI 穿帮检测',
  '优先使用最新 LLM 模型',
  '高级模板库',
  '专属客服支持',
]

export default function Subscription() {
  const navigate = useNavigate()
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [confirmCancel, setConfirmCancel] = useState(false)

  useEffect(() => {
    // In production: fetch from /api/subscriptions/me
    setTimeout(() => {
      setSubscription({
        status: 'none',
        plan: 'free',
        current_period_end: null,
        cancel_at_period_end: false,
      })
      setLoading(false)
    }, 500)
  }, [])

  async function handleSubscribe() {
    setProcessing(true)
    // In production: redirect to Stripe checkout or show payment modal
    await new Promise(r => setTimeout(r, 1000))
    setSubscription({
      status: 'active',
      plan: 'pro',
      current_period_end: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      cancel_at_period_end: false,
    })
    setProcessing(false)
  }

  async function handleCancel() {
    setProcessing(true)
    await new Promise(r => setTimeout(r, 1000))
    setSubscription(s => s ? { ...s, cancel_at_period_end: true } : s)
    setConfirmCancel(false)
    setProcessing(false)
  }

  if (loading) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        加载中...
      </div>
    )
  }

  const isPro = subscription?.status === 'active' || subscription?.status === 'trialing'

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
            订阅管理
          </h1>
        </div>
      </header>

      <div style={{ maxWidth: '560px', margin: '0 auto', padding: '3rem' }}>
        {isPro ? (
          <>
            {/* Pro status card */}
            <div
              style={{
                background: 'var(--bg-raised)',
                border: '1px solid var(--accent-crimson)',
                borderRadius: '12px',
                padding: '2rem',
                marginBottom: '2rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                <div
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: '#22c55e',
                  }}
                />
                <span
                  style={{
                    fontFamily: "'Crimson Pro', serif",
                    fontSize: '14px',
                    color: '#22c55e',
                    letterSpacing: '0.05em',
                  }}
                >
                  Pro 版本
                </span>
              </div>
              <div style={{ fontFamily: "'Playfair Display', serif", fontSize: '1.5rem', fontWeight: 500, color: 'var(--text-cream)', marginBottom: '0.5rem' }}>
                ¥29 / 月
              </div>
              {subscription?.current_period_end && (
                <p style={{ fontFamily: "'Crimson Pro', serif", fontSize: '14px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  下次扣款：{new Date(subscription.current_period_end).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })}
                </p>
              )}
              {subscription?.cancel_at_period_end && (
                <p style={{ fontFamily: "'Crimson Pro', serif", fontSize: '14px', color: '#f59e0b', marginTop: '0.5rem' }}>
                  已申请取消，将于到期后生效
                </p>
              )}
            </div>

            {/* Features */}
            <div
              style={{
                background: 'var(--bg-raised)',
                border: '1px solid var(--border)',
                borderRadius: '12px',
                padding: '1.5rem',
                marginBottom: '2rem',
              }}
            >
              <div className="label" style={{ marginBottom: '1rem', color: 'var(--text-faint)' }}>
                包含功能
              </div>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {PLAN_FEATURES.map((f, i) => (
                  <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#788c5d" strokeWidth="2">
                      <path d="M20 6L9 17l-5-5" />
                    </svg>
                    <span style={{ fontFamily: "'Crimson Pro', serif", fontSize: '15px', color: 'var(--text-cream)' }}>
                      {f}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Cancel */}
            {!subscription?.cancel_at_period_end ? (
              confirmCancel ? (
                <div
                  style={{
                    background: 'var(--bg-raised)',
                    border: '1px solid rgba(220,38,38,0.3)',
                    borderRadius: '12px',
                    padding: '1.5rem',
                  }}
                >
                  <p style={{ fontFamily: "'Crimson Pro', serif", fontSize: '15px', color: 'var(--text-cream)', marginBottom: '1rem' }}>
                    确定要取消 Pro 订阅吗？取消后云端项目和高级功能将继续使用至本订阅周期结束。
                  </p>
                  <div style={{ display: 'flex', gap: '0.75rem' }}>
                    <button
                      onClick={handleCancel}
                      disabled={processing}
                      style={{
                        padding: '0.625rem 1.25rem',
                        background: 'rgba(220,38,38,0.1)',
                        border: '1px solid rgba(220,38,38,0.3)',
                        borderRadius: '6px',
                        color: '#fca5a5',
                        fontFamily: "'Crimson Pro', serif",
                        fontSize: '14px',
                        cursor: 'pointer',
                      }}
                    >
                      {processing ? '处理中...' : '确认取消'}
                    </button>
                    <button
                      onClick={() => setConfirmCancel(false)}
                      style={{
                        padding: '0.625rem 1.25rem',
                        background: 'transparent',
                        border: '1px solid var(--border)',
                        borderRadius: '6px',
                        color: 'var(--text-muted)',
                        fontFamily: "'Crimson Pro', serif",
                        fontSize: '14px',
                        cursor: 'pointer',
                      }}
                    >
                      保留订阅
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmCancel(true)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-faint)',
                    fontFamily: "'Crimson Pro', serif",
                    fontSize: '14px',
                    cursor: 'pointer',
                    padding: 0,
                    textDecoration: 'underline',
                  }}
                >
                  取消订阅
                </button>
              )
            ) : (
              <p style={{ fontFamily: "'Crimson Pro', serif", fontSize: '14px', color: 'var(--text-faint)', fontStyle: 'italic' }}>
                订阅到期后将恢复为免费版
              </p>
            )}
          </>
        ) : (
          <>
            {/* Free plan */}
            <div
              style={{
                background: 'var(--bg-raised)',
                border: '1px solid var(--border)',
                borderRadius: '12px',
                padding: '2rem',
                marginBottom: '2rem',
                textAlign: 'center',
              }}
            >
              <div
                style={{
                  fontFamily: "'Playfair Display', serif",
                  fontSize: '1.25rem',
                  fontWeight: 500,
                  color: 'var(--text-cream)',
                  marginBottom: '0.5rem',
                }}
              >
                免费版
              </div>
              <p style={{ fontFamily: "'Crimson Pro', serif", fontSize: '14px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                当前方案
              </p>
            </div>

            {/* Upgrade CTA */}
            <div
              style={{
                background: 'var(--bg-raised)',
                border: '1px solid var(--border)',
                borderRadius: '12px',
                padding: '2rem',
              }}
            >
              <div className="label" style={{ marginBottom: '1rem', color: 'var(--accent-crimson)' }}>
                <span className="accent-rule" style={{ background: 'var(--accent-crimson)' }} />
                升级到 Pro
              </div>
              <div style={{ fontFamily: "'Playfair Display', serif", fontSize: '2rem', fontWeight: 500, color: 'var(--text-cream)', marginBottom: '0.25rem' }}>
                ¥29<span style={{ fontSize: '1rem', color: 'var(--text-muted)', fontFamily: "'Crimson Pro', serif" }}>/月</span>
              </div>
              <p style={{ fontFamily: "'Crimson Pro', serif", fontSize: '14px', color: 'var(--text-muted)', fontStyle: 'italic', marginBottom: '1.5rem' }}>
                解锁全部高级功能
              </p>

              <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 1.5rem', display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                {PLAN_FEATURES.map((f, i) => (
                  <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#788c5d" strokeWidth="2">
                      <path d="M20 6L9 17l-5-5" />
                    </svg>
                    <span style={{ fontFamily: "'Crimson Pro', serif", fontSize: '14px', color: 'var(--text-muted)' }}>
                      {f}
                    </span>
                  </li>
                ))}
              </ul>

              <button
                onClick={handleSubscribe}
                disabled={processing}
                style={{
                  width: '100%',
                  padding: '0.875rem',
                  background: 'var(--accent-crimson)',
                  border: 'none',
                  borderRadius: '8px',
                  color: 'white',
                  fontFamily: "'Crimson Pro', serif",
                  fontSize: '15px',
                  fontWeight: 500,
                  cursor: processing ? 'not-allowed' : 'pointer',
                  opacity: processing ? 0.6 : 1,
                }}
              >
                {processing ? '跳转支付...' : '立即升级'}
              </button>
              <p style={{ fontFamily: "'Crimson Pro', serif", fontSize: '12px', color: 'var(--text-faint)', textAlign: 'center', marginTop: '0.75rem' }}>
                支持支付宝、微信支付 · 随时取消
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
