import { useSearchParams } from 'react-router-dom'
import { LandingA } from './LandingA'
import { LandingB } from './LandingB'
import { assignVariant, getVisitorId } from './variant'

// A/B 测试入口：
//   /landing          → 按访客稳定分配（50/50）
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

  // 按访客稳定分配（50/50）：同一访客每次得到同一个版本
  return assignVariant(getVisitorId()) === 'a' ? <LandingA /> : <LandingB />
}
