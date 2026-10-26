// A/B 分流：按访客稳定分配。访客 id 首次访问时随机生成并存入 localStorage，
// 之后永远得到同一个版本；分配只看 id 的哈希，与 userAgent 等无关。
const KEY = 'mw_visitor_id'

export function getVisitorId(): string {
  try {
    let id = localStorage.getItem(KEY)
    if (!id) {
      id = (typeof crypto !== 'undefined' && 'randomUUID' in crypto)
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2) + Date.now().toString(36)
      localStorage.setItem(KEY, id)
    }
    return id
  } catch {
    // 存储不可用：本次访问内随机，但不保证跨访问稳定
    return Math.random().toString(36).slice(2)
  }
}

// FNV-1a：简单、稳定、分布均匀；奇偶位决定版本
export function assignVariant(visitorId: string): 'a' | 'b' {
  let h = 0x811c9dc5
  for (let i = 0; i < visitorId.length; i++) {
    h ^= visitorId.charCodeAt(i)
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return (h & 1) === 0 ? 'a' : 'b'
}
