import { useState, useRef, useEffect, useCallback } from 'react'

interface OnboardingModalProps {
  isOpen: boolean
  onClose: () => void
  email: string
}

export function OnboardingModal({ isOpen, onClose, email }: OnboardingModalProps) {
  const [step, setStep] = useState<'success' | 'login' | 'register'>('success')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const modalRef = useRef<HTMLDivElement>(null)

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose()
      return
    }
    if (e.key !== 'Tab') return
    const modal = modalRef.current
    if (!modal) return
    const focusable = modal.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault()
        last.focus()
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
  }, [onClose])

  useEffect(() => {
    if (!isOpen) return
    // Store previous focus for restoration on close
    const previousFocus = document.activeElement as HTMLElement
    document.addEventListener('keydown', handleKeyDown)
    // Focus first focusable element
    const timer = setTimeout(() => {
      const modal = modalRef.current
      if (!modal) return
      const focusable = modal.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
      focusable[0]?.focus()
    }, 0)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      clearTimeout(timer)
      // Restore focus to the element that opened the modal
      previousFocus?.focus()
    }
  }, [isOpen, handleKeyDown])

  // Reset state when modal re-opens
  useEffect(() => {
    if (isOpen) {
      setStep('success')
      setPassword('')
      setConfirmPassword('')
      setError('')
      setLoading(false)
    }
  }, [isOpen])

  if (!isOpen) return null

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault()
    if (password !== confirmPassword) {
      setError('两次密码不一致')
      return
    }
    if (password.length < 8) {
      setError('密码至少 8 位')
      return
    }
    setLoading(true)
    setError('')
    // In production: call /api/auth/register
    await new Promise(r => setTimeout(r, 1000))
    setLoading(false)
    // Redirect to dashboard
    window.location.href = '/'
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center" role="dialog" aria-modal="true" aria-label="用户引导">
      <div className="absolute inset-0 bg-black/75" onClick={onClose} />

      <div ref={modalRef} className="relative z-10 w-full max-w-md mx-4 bg-[#141413] border border-[#333] rounded-2xl overflow-hidden">
        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-[#666] hover:text-white transition-colors z-10"
          aria-label="关闭"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>

        {/* Success state */}
        {step === 'success' && (
          <div className="p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-[#788c5d]/20 flex items-center justify-center">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#788c5d" strokeWidth="2">
                <path d="M20 6L9 17l-5-5" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">预约成功</h2>
            <p className="text-[#b0aea5] text-sm mb-1">{email}</p>
            <p className="text-[#666] text-xs mb-8">功能上线后第一时间通知你</p>

            <div className="border-t border-[#222] pt-6">
              <p className="text-[#b0aea5] text-sm mb-4">
                抢先体验murder-wizard Pro？
              </p>
              <div className="flex flex-col gap-2">
                <button
                  onClick={() => setStep('register')}
                  className="w-full py-2.5 bg-[#d97757] hover:bg-[#c4684a] text-white font-medium rounded-lg transition-colors text-sm"
                >
                  立即注册（免费）
                </button>
                <button
                  onClick={() => setStep('login')}
                  className="w-full py-2.5 bg-[#1a1917] hover:bg-[#222] text-[#b0aea5] font-medium rounded-lg transition-colors text-sm border border-[#333]"
                >
                  已有账号？登录
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Register */}
        {step === 'register' && (
          <div className="p-8">
            <button
              onClick={() => setStep('success')}
              className="text-[#666] hover:text-white text-sm mb-6 flex items-center gap-1 transition-colors"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M15 18l-6-6 6-6" />
              </svg>
              返回
            </button>

            <h2 className="text-xl font-semibold text-white mb-1">创建账号</h2>
            <p className="text-[#666] text-sm mb-6">邮箱：{email}</p>

            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <label className="block text-xs text-[#666] mb-1.5">设置密码（至少8位）</label>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="输入密码"
                  required
                  minLength={8}
                  className="w-full px-4 py-2.5 bg-[#1a1917] border border-[#333] rounded-lg text-white placeholder-[#555] text-sm focus:outline-none focus:border-[#d97757]/50 transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs text-[#666] mb-1.5">确认密码</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  placeholder="再次输入密码"
                  required
                  minLength={8}
                  className="w-full px-4 py-2.5 bg-[#1a1917] border border-[#333] rounded-lg text-white placeholder-[#555] text-sm focus:outline-none focus:border-[#d97757]/50 transition-colors"
                />
              </div>

              {error && (
                <p className="text-red-400 text-xs">{error}</p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 bg-[#d97757] hover:bg-[#c4684a] disabled:opacity-50 text-white font-medium rounded-lg transition-colors text-sm"
              >
                {loading ? '注册中...' : '完成注册'}
              </button>
            </form>
          </div>
        )}

        {/* Login */}
        {step === 'login' && (
          <div className="p-8">
            <button
              onClick={() => setStep('success')}
              className="text-[#666] hover:text-white text-sm mb-6 flex items-center gap-1 transition-colors"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M15 18l-6-6 6-6" />
              </svg>
              返回
            </button>

            <h2 className="text-xl font-semibold text-white mb-1">登录账号</h2>
            <p className="text-[#666] text-sm mb-6">邮箱：{email}</p>

            <form className="space-y-4">
              <div>
                <label className="block text-xs text-[#666] mb-1.5">密码</label>
                <input
                  type="password"
                  placeholder="输入密码"
                  required
                  className="w-full px-4 py-2.5 bg-[#1a1917] border border-[#333] rounded-lg text-white placeholder-[#555] text-sm focus:outline-none focus:border-[#d97757]/50 transition-colors"
                />
              </div>
              <button
                type="submit"
                className="w-full py-2.5 bg-[#d97757] hover:bg-[#c4684a] text-white font-medium rounded-lg transition-colors text-sm"
              >
                登录
              </button>
            </form>

            <p className="text-center text-[#555] text-xs mt-4">
              忘记密码？<button className="text-[#d97757] hover:underline">重置</button>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
