import { useState, useEffect, useRef } from 'react'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  variant?: 'a' | 'b' | 'random' | 'unknown'
  onEmailSubmit?: (email: string) => void
}

export function Modal({ isOpen, onClose, variant, onEmailSubmit }: ModalProps) {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')
  const firstFocusRef = useRef<HTMLInputElement>(null)
  const modalRef = useRef<HTMLDivElement>(null)
  const previousActiveElement = useRef<Element | null>(null)

  // Focus trap — save previous focus, focus first element, trap Tab
  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement
      // Move focus into modal
      setTimeout(() => {
        firstFocusRef.current?.focus()
      }, 0)
    } else {
      // Restore focus when modal closes
      if (previousActiveElement.current instanceof HTMLElement) {
        previousActiveElement.current.focus()
      }
    }
  }, [isOpen])

  // Trap Tab key inside modal
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
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
          last?.focus()
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault()
          first?.focus()
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return

    try {
      const res = await fetch('/api/landing/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, variant: variant ?? 'unknown' }),
      })

      if (res.ok) {
        setSubmitted(true)
        onEmailSubmit?.(email)
        setTimeout(() => {
          onClose()
          setSubmitted(false)
          setEmail('')
        }, 2000)
      } else {
        const data = await res.json()
        setError(data.error === 'invalid_email' ? '请输入有效的邮箱地址' : '提交失败，请重试')
      }
    } catch {
      setError('网络错误，请检查网络连接')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      {/* Backdrop — use inert to block underlying content */}
      <div
        className="absolute inset-0 bg-[rgba(18,17,15,0.75)]"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        ref={modalRef}
        className="relative z-10 w-full max-w-md mx-4 bg-[#141413] border border-[rgba(217,119,87,0.3)] rounded-2xl p-8 shadow-2xl"
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-[#b0aea5] hover:text-white transition-colors"
          aria-label="关闭"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>

        {submitted ? (
          <div className="text-center py-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[rgba(120,140,93,0.2)] flex items-center justify-center">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#788c5d" strokeWidth="2">
                <path d="M20 6L9 17l-5-5" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-white mb-2" id="modal-title">已收录</h3>
            <p className="text-[#b0aea5]">功能上线后第一时间通知你</p>
          </div>
        ) : (
          <>
            <div className="text-center mb-6">
              <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-[rgba(217,119,87,0.1)] flex items-center justify-center">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#d97757" strokeWidth="2">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2" id="modal-title">功能开发中</h3>
              <p className="text-[#b0aea5] text-sm">留邮箱优先体验 Pro 版本</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <input
                  ref={firstFocusRef}
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value)
                    setError('')
                  }}
                  placeholder="your@email.com"
                  required
                  aria-label="邮箱地址"
                  className="w-full px-4 py-3 bg-[#1a1917] border border-[#333] rounded-lg text-white placeholder-[#666] focus:outline-none focus:border-[rgba(217,119,87,0.5)] transition-colors"
                />
                {error && (
                  <p role="alert" className="text-red-400 text-xs mt-1">{error}</p>
                )}
              </div>
              <button
                type="submit"
                className="w-full py-3 bg-[#d97757] hover:bg-[#c4684a] text-white font-medium rounded-lg transition-colors"
              >
                立即预约
              </button>
            </form>

            <p className="text-center text-[#666] text-xs mt-4">我们尊重隐私，不会向第三方透露你的邮箱</p>
          </>
        )}
      </div>
    </div>
  )
}
