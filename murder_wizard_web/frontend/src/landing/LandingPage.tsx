import { useSearchParams } from 'react-router-dom'
import { LandingA } from './LandingA'
import { LandingB } from './LandingB'

// A/B 测试入口：
//   /landing          → 自动分配（50/50）
//   /landing?variant=a → 强制显示 A（技术向）
//   /landing?variant=b → 强制显示 B（新手友好）
//
// 也可直接用 /landing-a 和 /landing-b 单独访问

export function LandingPage() {
  const [searchParams] = useSearchParams()
  const variant = searchParams.get('variant')

  // 强制指定版本
  if (variant === 'a') return <LandingA />
  if (variant === 'b') return <LandingB />

  // 50/50 随机分配（基于 session 一致性）
  const hash = (() => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    let h = 0
    for (let i = 0; i < chars.length; i++) {
      h = (h * 31 + chars.charCodeAt(i)) >>> 0
    }
    return h
  })()

  // 同一浏览器保持一致（基于 userAgent 哈希）
  const sessionId = typeof window !== 'undefined'
    ? hash + window.navigator.userAgent.length
    : hash
  const isA = (sessionId % 2) === 0

  return isA ? <LandingA /> : <LandingB />
}
