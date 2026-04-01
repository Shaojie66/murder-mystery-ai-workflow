import { useState } from 'react'
import { Modal } from './components/Modal'
import { OnboardingModal } from './components/OnboardingModal'
import { useAnalytics } from '../hooks/useAnalytics'

// Inline SVG icons to replace emoji — consistent with the design system
const IconRole = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
  </svg>
)
const IconSearch = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
  </svg>
)
const IconBook = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
  </svg>
)
const IconCheck = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M20 6L9 17l-5-5"/>
  </svg>
)
const IconGear = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>
)
const IconPen = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
  </svg>
)
const IconPaint = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M12 2C6.49 2 2 6.49 2 12s4.49 10 10 10c1.38 0 2.5-1.12 2.5-2.5 0-.61-.23-1.2-.64-1.67-.08-.1-.13-.21-.13-.33 0-.28.22-.5.5-.5H16c3.31 0 6-2.69 6-6 0-4.96-4.49-9-10-9zm-5.5 9c-.28 0-.5-.22-.5-.5s.22-.5.5-.5.5.22.5.5-.22.5-.5.5zm3 4c-.28 0-.5-.22-.5-.5s.22-.5.5-.5.5.22.5.5-.22.5-.5.5zm5 0c-.28 0-.5-.22-.5-.5s.22-.5.5-.5.5.22.5.5-.22.5-.5.5zm3-4c-.28 0-.5-.22-.5-.5s.22-.5.5-.5.5.22.5.5-.22.5-.5.5z"/>
  </svg>
)
const IconLab = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M9 3h6v2H9zM8 5H6v3l-4 8h20l-4-8V5h-2v0H8z"/>
  </svg>
)
const IconMoney = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
  </svg>
)
const IconPrint = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>
  </svg>
)
const IconMegaphone = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M3 11l19-9-9 19-2-8-8-2z"/>
  </svg>
)
const IconUsers = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
)
const IconArrow = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M9 18l6-6-6-6"/>
  </svg>
)

export function LandingB() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [submittedEmail, setSubmittedEmail] = useState('')
  const [showOnboarding, setShowOnboarding] = useState(false)
  const { trackEvent } = useAnalytics('b')

  const handleModalOpen = (location: string) => {
    setIsModalOpen(true)
    trackEvent('modal_open', { location })
  }

  const handleEmailSubmit = (email: string) => {
    trackEvent('email_submit', { location: 'modal' })
    setIsModalOpen(false)
    setSubmittedEmail(email)
    setShowOnboarding(true)
  }

  const handleOnboardingClose = () => {
    setShowOnboarding(false)
  }

  return (
    <div className="min-h-[100dvh]" style={{ backgroundColor: 'var(--lbg-bg)', color: 'var(--lbg-text)' }}>
      {/* Header */}
      <header className="border-b" style={{ borderColor: 'var(--lbg-border)' }}>
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: 'var(--lbg-accent)' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                <path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z" />
                <polyline points="14,2 14,8 20,8" />
              </svg>
            </div>
            <span className="font-semibold text-lg tracking-tight">murder-wizard</span>
          </div>
          <nav className="flex items-center gap-6 text-sm" style={{ color: 'var(--lbg-muted)' }}>
            <a href="#features" className="hover:text-[var(--lbg-text)] transition-colors">功能</a>
            <a href="#how" className="hover:text-[var(--lbg-text)] transition-colors">如何使用</a>
            <button
              onClick={() => handleModalOpen('header')}
              className="px-4 py-2 rounded-lg font-medium transition-colors"
              style={{ backgroundColor: 'var(--lbg-text)', color: 'var(--lbg-bg)' }}
            >
              预约 Pro
            </button>
          </nav>
        </div>
      </header>

      {/* Hero - Friendly Style */}
      <section className="border-b" style={{ borderColor: 'var(--lbg-border)' }}>
        <div className="max-w-6xl mx-auto px-6 py-20">
          <div className="max-w-3xl mx-auto text-center">
            <div
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full border text-sm font-medium mb-6"
              style={{ color: 'var(--lbg-accent)', borderColor: 'rgba(217,119,87,0.3)' }}
            >
              全新 Web 版本现已开放预约
            </div>
            <h1 className="text-4xl md:text-6xl tracking-tighter mb-6 leading-[1.1] font-bold" style={{ color: 'var(--lbg-text)' }}>
              用 AI 轻松创作<br />
              <span style={{ color: 'var(--lbg-accent)' }}>你的剧本杀</span>
            </h1>
            <p className="text-xl mb-4 max-w-[50ch] mx-auto leading-relaxed" style={{ color: 'var(--lbg-muted)' }}>
              不会写剧本？没关系。跟向导一步步来，8 个阶段，从创意到印刷，
              轻松完成一部完整的剧本杀作品。
            </p>
            <p className="text-base mb-8" style={{ color: 'var(--lbg-faint)' }}>
              无需任何技术背景，打开浏览器就能用
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <button
                onClick={() => handleModalOpen('hero')}
                className="px-8 py-4 font-medium rounded-xl transition-colors text-lg"
                style={{ backgroundColor: 'var(--lbg-accent)', color: 'white' }}
              >
                立即开始创作
              </button>
              <a
                href="#how"
                className="px-6 py-4 transition-colors"
                style={{ color: 'var(--lbg-muted)' }}
              >
                了解工作流程
                <span className="inline-block ml-1"><IconArrow /></span>
              </a>
            </div>
          </div>

          {/* Visual Flow */}
          <div className="mt-16 flex items-center justify-center gap-4 flex-wrap">
            {[
              { step: '1', title: '输入想法', desc: '用中文描述你的剧本创意' },
              { step: '2', title: 'AI 辅助创作', desc: '系统引导完成每个阶段' },
              { step: '3', title: '生成剧本', desc: '导出可直接印刷的文件' },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-4">
                <div className="text-center">
                  <div
                    className="w-16 h-16 rounded-2xl border flex items-center justify-center mb-2"
                    style={{ borderColor: 'rgba(217,119,87,0.3)', backgroundColor: 'rgba(217,119,87,0.08)' }}
                  >
                    <span className="text-2xl font-bold" style={{ color: 'var(--lbg-accent)' }}>{item.step}</span>
                  </div>
                  <div className="font-medium text-sm" style={{ color: 'var(--lbg-text)' }}>{item.title}</div>
                  <div className="text-xs" style={{ color: 'var(--lbg-faint)' }}>{item.desc}</div>
                </div>
                {i < 2 && (
                  <div className="hidden sm:block" style={{ color: '#ccc' }}>
                    <IconArrow />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features - Stacked on mobile */}
      <section id="features" className="border-b" style={{ borderColor: 'var(--lbg-border)' }}>
        <div className="max-w-6xl mx-auto px-6 py-20">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold tracking-tight mb-4" style={{ color: 'var(--lbg-text)' }}>只需三步，完成专业剧本杀</h2>
            <p style={{ color: 'var(--lbg-muted)' }}>向导式流程，让复杂的创作变得简单</p>
          </div>

          {/* Feature cards — stack on mobile, 3-col on desktop */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                step: '01',
                title: '创意输入',
                desc: '用日常语言描述你的想法，系统自动理解并规划剧本结构',
                colorVar: 'var(--lbg-accent)',
              },
              {
                step: '02',
                title: '分步引导',
                desc: '每个阶段都有清晰的指引和示例，不知不觉完成所有步骤',
                colorVar: 'var(--lbg-blue)',
              },
              {
                step: '03',
                title: '一键导出',
                desc: '直接生成 PDF 文件，可用于印刷或分享给玩家',
                colorVar: 'var(--lbg-green)',
              },
            ].map((f, i) => (
              <div key={i} className="p-8 rounded-2xl" style={{ backgroundColor: 'var(--lbg-surface)', border: '1px solid var(--lbg-border)' }}>
                <div
                  className="text-6xl font-bold tracking-tighter mb-4"
                  style={{ color: f.colorVar + '33' }}
                >
                  {f.step}
                </div>
                <h3 className="text-xl font-semibold mb-2" style={{ color: 'var(--lbg-text)' }}>{f.title}</h3>
                <p className="leading-relaxed" style={{ color: 'var(--lbg-muted)' }}>{f.desc}</p>
              </div>
            ))}
          </div>

          {/* More Features — 2-col tablet, 4-col desktop */}
          <div className="mt-12 grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { Icon: IconRole, title: '角色设计', desc: 'AI 帮你构建 6 个性格鲜明的角色' },
              { Icon: IconSearch, title: '线索设计', desc: '自动生成互相关联的线索链' },
              { Icon: IconBook, title: '剧本生成', desc: '每个人有独立的阅读本和线索本' },
              { Icon: IconCheck, title: '穿帮检查', desc: '自动发现角色间的逻辑矛盾' },
            ].map((f, i) => (
              <div key={i} className="p-4 rounded-xl" style={{ backgroundColor: 'var(--lbg-surface)', border: '1px solid var(--lbg-border)' }}>
                <div className="w-8 h-8 rounded-lg mb-3 flex items-center justify-center" style={{ backgroundColor: 'rgba(217,119,87,0.1)', color: 'var(--lbg-accent)' }}>
                  <f.Icon />
                </div>
                <h4 className="font-medium text-sm mb-1" style={{ color: 'var(--lbg-text)' }}>{f.title}</h4>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--lbg-faint)' }}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="border-b" style={{ borderColor: 'var(--lbg-border)' }}>
        <div className="max-w-6xl mx-auto px-6 py-20">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold tracking-tight mb-4">8 阶段完整工作流</h2>
            <p style={{ color: 'var(--lbg-muted)' }}>从创意到印刷，覆盖剧本杀制作的每个环节</p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { n: '1', title: '机制设计', Icon: IconGear, done: true },
              { n: '2', title: '剧本创作', Icon: IconPen, done: true },
              { n: '3', title: '视觉物料', Icon: IconPaint, done: false },
              { n: '4', title: '用户测试', Icon: IconLab, done: false },
              { n: '5', title: '商业化', Icon: IconMoney, done: false },
              { n: '6', title: '印刷生产', Icon: IconPrint, done: false },
              { n: '7', title: '宣发内容', Icon: IconMegaphone, done: false },
              { n: '8', title: '社区运营', Icon: IconUsers, done: false },
            ].map((stage, i) => (
              <div
                key={i}
                className="p-4 rounded-xl border"
                style={
                  stage.done
                    ? { backgroundColor: 'rgba(120,140,93,0.05)', borderColor: 'rgba(120,140,93,0.2)' }
                    : { backgroundColor: 'var(--lbg-surface)', borderColor: 'var(--lbg-border)' }
                }
              >
                <div className="flex items-center gap-3 mb-2">
                  <span
                    className="w-8 h-8 rounded-lg flex items-center justify-center"
                    style={{
                      background: stage.done ? 'rgba(120,140,93,0.15)' : 'rgba(0,0,0,0.04)',
                      color: stage.done ? 'var(--lbg-green)' : 'var(--lbg-faint)',
                    }}
                  >
                    <stage.Icon />
                  </span>
                  <span
                    className="text-sm font-medium"
                    style={{ color: stage.done ? 'var(--lbg-green)' : 'var(--lbg-muted)' }}
                  >
                    阶段 {stage.n}
                  </span>
                </div>
                <div className="text-sm" style={{ color: stage.done ? 'var(--lbg-green)' : '#333' }}>
                  {stage.title}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="border-b" style={{ borderColor: 'var(--lbg-border)' }}>
        <div className="max-w-6xl mx-auto px-6 py-20">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold tracking-tight mb-4">Pro 版本</h2>
            <p style={{ color: 'var(--lbg-muted)' }}>解锁全部高级功能，创作更轻松</p>
          </div>

          <div className="max-w-md mx-auto">
            <div className="rounded-2xl p-8 border-2" style={{ backgroundColor: 'var(--lbg-surface)', borderColor: 'var(--lbg-accent)' }}>
              <div className="flex items-baseline gap-2 mb-2">
                <span className="text-5xl font-bold" style={{ color: 'var(--lbg-text)' }}>¥29</span>
                <span style={{ color: 'var(--lbg-muted)' }}>/月</span>
              </div>
              <div className="text-sm font-medium mb-6" style={{ color: 'var(--lbg-accent)' }}>包含全部功能</div>

              <ul className="space-y-3 mb-8">
                {[
                  '云端保存，随时随地访问',
                  'AI 穿帮检测，自动发现错误',
                  '高级剧本模板',
                  '无限协作人数',
                  '优先体验新功能',
                  '专属客服支持',
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-3 text-sm" style={{ color: 'var(--lbg-muted)' }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--lbg-green)" strokeWidth="2">
                      <path d="M20 6L9 17l-5-5" />
                    </svg>
                    {item}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleModalOpen('pricing')}
                className="w-full py-3 font-medium rounded-xl transition-colors text-lg"
                style={{ backgroundColor: 'var(--lbg-accent)', color: 'white' }}
              >
                立即预约
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Banner */}
      <section style={{ backgroundColor: 'var(--lbg-text)' }}>
        <div className="max-w-4xl mx-auto px-6 py-16 text-center">
          <h2 className="text-3xl font-bold mb-4 tracking-tight" style={{ color: 'var(--lbg-bg)' }}>准备好创作你的剧本杀了吗？</h2>
          <p className="mb-8" style={{ color: '#b0aea5' }}>加入早期用户列表，功能上线后第一时间通知你</p>
          <button
            onClick={() => handleModalOpen('banner')}
            className="px-8 py-4 font-medium rounded-xl transition-colors text-lg"
            style={{ backgroundColor: 'var(--lbg-accent)', color: 'white' }}
          >
            立即预约
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12" style={{ backgroundColor: 'var(--lbg-bg)' }}>
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between text-sm" style={{ color: 'var(--lbg-faint)' }}>
          <div>© 2026 murder-wizard. MIT License.</div>
          <div className="flex items-center gap-6">
            <a href="#" className="hover:text-[var(--lbg-muted)] transition-colors">使用帮助</a>
            <a href="#" className="hover:text-[var(--lbg-muted)] transition-colors">隐私政策</a>
            <a href="#" className="hover:text-[var(--lbg-muted)] transition-colors">联系我们</a>
          </div>
        </div>
      </footer>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} variant="b" onEmailSubmit={handleEmailSubmit} />
      <OnboardingModal isOpen={showOnboarding} onClose={handleOnboardingClose} email={submittedEmail} />
    </div>
  )
}
