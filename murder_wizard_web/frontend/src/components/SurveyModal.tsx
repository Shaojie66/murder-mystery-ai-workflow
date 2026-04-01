import { useState } from 'react'

interface SurveyModalProps {
  onClose: () => void
}

export function useSurveyModal() {
  const [show, setShow] = useState(false)
  return {
    show,
    onClose: () => setShow(false),
  }
}

export default function SurveyModal({ onClose }: SurveyModalProps) {
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
          maxWidth: '480px',
          padding: '3rem',
        }}
      >
        <h2
          style={{
            fontFamily: "'Playfair Display', serif",
            fontSize: '1.25rem',
            color: 'var(--text-cream)',
            marginBottom: '1rem',
          }}
        >
          创作偏好
        </h2>
        <p
          style={{
            fontFamily: "'Crimson Pro', serif",
            fontSize: '15px',
            color: 'var(--text-muted)',
            marginBottom: '1.5rem',
          }}
        >
          告诉我们你感兴趣的剧本杀类型，帮助我们更好地优化产品。
        </p>
        <button onClick={onClose} className="btn-ghost" style={{ fontSize: '13px' }}>
          关闭
        </button>
      </div>
    </div>
  )
}
