import { useState } from 'react'
import { Modal } from './components/Modal'
import { OnboardingModal } from './components/OnboardingModal'
import { useAnalytics } from '../hooks/useAnalytics'

export function LandingA() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [submittedEmail, setSubmittedEmail] = useState('')
  const [showOnboarding, setShowOnboarding] = useState(false)
  const { trackEvent } = useAnalytics('a')

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
    <div className="min-h-[100dvh] text-white" style={{ backgroundColor: 'var(--bg-base)' }}>
      {/* Header */}
      <header className="border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: 'var(--accent-orange)' }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                <path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z" />
                <polyline points="14,2 14,8 20,8" />
              </svg>
            </div>
            <span className="font-semibold text-lg tracking-tight">murder-wizard</span>
          </div>
          <nav className="flex items-center gap-6 text-sm" style={{ color: 'var(--text-muted)' }}>
            <a href="#features" className="hover:text-white transition-colors">功能</a>
            <a href="#pricing" className="hover:text-white transition-colors">定价</a>
            <a href="#docs" className="hover:text-white transition-colors">文档</a>
            <button
              onClick={() => handleModalOpen('header')}
              className="px-4 py-2 rounded-lg font-medium hover:bg-[rgba(255,255,255,0.1)] transition-colors"
              style={{ backgroundColor: 'var(--text-cream)', color: 'var(--bg-base)' }}
            >
              预约 Pro
            </button>
          </nav>
        </div>
      </header>

      {/* Hero - Terminal Style */}
      <section className="border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="max-w-6xl mx-auto px-6 py-20">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div
                className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium mb-6"
                style={{ backgroundColor: 'rgba(217,119,87,0.1)', border: '1px solid rgba(217,119,87,0.2)', color: 'var(--accent-orange)' }}
              >
                <span className="w-2 h-2 rounded-full pulse-dot" style={{ backgroundColor: 'var(--accent-orange)' }} />
                CLI to Web — 全面升级
              </div>
              <h1 className="text-5xl lg:text-6xl font-bold tracking-tighter mb-6 leading-[1.1]">
                从命令行<br />
                <span style={{ color: 'var(--accent-orange)' }}>到协作工作区</span>
              </h1>
              <p className="text-lg mb-4 max-w-[50ch]" style={{ color: 'var(--text-muted)' }}>
                保留 CLI 的精确控制，添加 Web 协作能力。
                API-first 架构，支持脚本化批量处理。
              </p>
              <pre
                className="text-sm font-mono rounded-lg p-3 mb-8 border"
                style={{
                  backgroundColor: 'var(--bg-raised)',
                  borderColor: 'var(--border)',
                  color: 'var(--text-faint)',
                }}
              >
                {`$ murder-wizard init my_script
$ murder-wizard phase my_script 1
$ murder-wizard expand --cloud --team`}
              </pre>
              <div className="flex items-center gap-4">
                <button
                  onClick={() => handleModalOpen('hero')}
                  className="px-6 py-3 font-medium rounded-lg transition-colors"
                  style={{ backgroundColor: 'var(--accent-orange)', color: 'white' }}
                >
                  预约 Pro 版本
                </button>
                <a
                  href="#docs"
                  className="px-6 py-3 transition-colors"
                  style={{ color: 'var(--text-muted)' }}
                >
                  查看文档 →
                </a>
              </div>
            </div>

            {/* Terminal Mock */}
            <div
              className="rounded-2xl overflow-hidden border"
              style={{ backgroundColor: 'var(--lbg-terminal-bg)', borderColor: 'var(--border)' }}
            >
              <div
                className="flex items-center gap-2 px-4 py-3 border-b"
                style={{ borderColor: 'var(--border)' }}
              >
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#ff5f56' }} />
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#ffbd2e' }} />
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#27ca40' }} />
                <span className="ml-3 text-xs" style={{ color: 'var(--text-faint)' }}>murder-wizard — 8 stages</span>
              </div>
              <div className="p-6 font-mono text-sm space-y-2">
                <div style={{ color: 'var(--text-muted)' }}>$ mw status</div>
                <div style={{ color: 'var(--text-faint)' }}>┌─ 项目进度 ─────────────────</div>
                <div style={{ color: 'var(--text-faint)' }}>│</div>
                <div style={{ color: 'var(--green-status)' }}>✓ 阶段 1: 机制设计</div>
                <div style={{ color: 'var(--green-status)' }}>✓ 阶段 2: 剧本创作</div>
                <div style={{ color: 'var(--accent-orange)' }}>● 阶段 3: 视觉物料</div>
                <div style={{ color: 'var(--text-faint)' }}>○ 阶段 4: 用户测试</div>
                <div style={{ color: 'var(--text-faint)' }}>...</div>
                <div style={{ color: 'var(--text-faint)' }}>└──────────────────────────</div>
                <div style={{ color: 'var(--text-muted)' }}>$</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="max-w-6xl mx-auto px-6 py-20">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold tracking-tight mb-4">为开发者设计的工作流</h2>
            <p className="max-w-[50ch] mx-auto" style={{ color: 'var(--text-muted)' }}>
              保留 CLI 的所有能力，同时提供现代 Web 界面
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                  </svg>
                ),
                title: 'API-First 架构',
                desc: 'RESTful API，支持脚本化批量处理，与现有 CI/CD 集成',
              },
              {
                icon: (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 6v6l4 2" />
                  </svg>
                ),
                title: '版本控制',
                desc: '内置 Git 版本控制，支持回滚、分支、团队协作',
              },
              {
                icon: (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <path d="M3 9h18M9 21V9" />
                  </svg>
                ),
                title: '8 阶段工作流',
                desc: '从机制设计到印刷生产的完整流程，阶段状态一目了然',
              },
              {
                icon: (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
                  </svg>
                ),
                title: '团队协作',
                desc: '角色分配、权限管理、实时多人编辑',
              },
              {
                icon: (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  </svg>
                ),
                title: '穿帮检测',
                desc: 'AI 自动扫描信息矩阵，自动发现角色间信息矛盾',
              },
              {
                icon: (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="22,12 18,12 15,21 9,3 6,12 2,12" />
                  </svg>
                ),
                title: 'LLM 适配层',
                desc: '支持 Claude / GPT-4o / Ollama，本地运行零成本',
              },
            ].map((f, i) => (
              <div
                key={i}
                className="p-6 rounded-xl border"
                style={{ backgroundColor: 'var(--bg-raised)', borderColor: 'var(--border)' }}
              >
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center mb-4"
                  style={{ backgroundColor: 'rgba(217,119,87,0.1)', color: 'var(--accent-orange)' }}
                >
                  {f.icon}
                </div>
                <h3 className="font-semibold mb-2" style={{ color: 'var(--text-cream)' }}>{f.title}</h3>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="max-w-6xl mx-auto px-6 py-20">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold tracking-tight mb-4">简单定价</h2>
            <p style={{ color: 'var(--text-muted)' }}>Pro 版本包含所有高级功能</p>
          </div>

          <div className="max-w-md mx-auto">
            <div
              className="rounded-2xl p-8 border-2"
              style={{ backgroundColor: 'var(--bg-raised)', borderColor: 'rgba(217,119,87,0.5)' }}
            >
              <div className="flex items-baseline gap-2 mb-2">
                <span className="text-5xl font-bold">¥29</span>
                <span style={{ color: 'var(--text-muted)' }}>/月</span>
              </div>
              <div className="text-sm font-medium mb-6" style={{ color: 'var(--accent-orange)' }}>Pro 版本</div>

              <ul className="space-y-3 mb-8">
                {[
                  '云端项目存储（无限项目）',
                  '团队协作（最多 10 人）',
                  'AI 穿帮检测',
                  '优先使用最新 LLM 模型',
                  '高级模板库',
                  'Email 支持',
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-3 text-sm" style={{ color: 'var(--text-muted)' }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#788c5d" strokeWidth="2">
                      <path d="M20 6L9 17l-5-5" />
                    </svg>
                    {item}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleModalOpen('pricing')}
                className="w-full py-3 font-medium rounded-lg transition-colors"
                style={{ backgroundColor: 'var(--accent-orange)', color: 'white' }}
              >
                立即预约
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between text-sm" style={{ color: 'var(--text-faint)' }}>
          <div>© 2026 murder-wizard. MIT License.</div>
          <div className="flex items-center gap-6">
            <a href="#" className="hover:text-[var(--text-muted)] transition-colors">文档</a>
            <a href="#" className="hover:text-[var(--text-muted)] transition-colors">GitHub</a>
            <a href="#" className="hover:text-[var(--text-muted)] transition-colors">联系我们</a>
          </div>
        </div>
      </footer>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} variant="a" onEmailSubmit={handleEmailSubmit} />
      <OnboardingModal isOpen={showOnboarding} onClose={handleOnboardingClose} email={submittedEmail} />
    </div>
  )
}
