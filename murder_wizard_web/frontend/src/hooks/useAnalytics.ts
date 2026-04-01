import { useCallback, useEffect, useRef } from 'react'

type EventName =
  | 'page_view'
  | 'cta_click'
  | 'modal_open'
  | 'email_submit'
  | 'email_invalid'
  | 'nav_click'
  | 'scroll_50'
  | 'scroll_100'

interface EventParams {
  variant?: 'a' | 'b' | 'random'
  location?: string
  target?: string
  time_on_page?: number
  [key: string]: string | number | undefined
}

// 轻量级分析追踪 hook
// 使用 Plausible Analytics 格式，可无缝对接
export function useAnalytics(variant: 'a' | 'b' | 'random' = 'random') {
  const sessionId = useRef(
    typeof window !== 'undefined'
      ? Math.random().toString(36).substring(2) + Date.now().toString(36)
      : ''
  )
  const scroll50Fired = useRef(false)
  const scroll100Fired = useRef(false)
  const startTime = useRef(Date.now())
  const pageViewFired = useRef(false)

  const trackEvent = useCallback(
    (name: EventName, params?: EventParams) => {
      if (typeof window === 'undefined') return

      const eventData = {
        event: name,
        props: {
          variant,
          session: sessionId.current,
          url: window.location.pathname,
          ...params,
        },
      }

      // 方式 1: Plausible Analytics（推荐）
      // @ts-ignore
      if (window.plausible) {
        // @ts-ignore
        window.plausible(name, { props: { variant, ...params } })
      }

      // 方式 2: console 日志（开发调试用）
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      if ((import.meta as any).env?.DEV) {
        console.log('[Analytics]', JSON.stringify(eventData, null, 2))
      }

      // 方式 3: 发送到自建数据端点（可选）
      fetch('/api/analytics/track', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event: name,
          variant,
          url: window.location.pathname,
          ...params,
        }),
      }).catch(() => {})
    },
    [variant]
  )

  // 页面访问 — 只在首次挂载时触发一次，unmount 时发送 duration
  useEffect(() => {
    if (pageViewFired.current) return
    pageViewFired.current = true

    trackEvent('page_view', {
      referrer: document.referrer,
      user_agent: navigator.userAgent,
    })

    startTime.current = Date.now()

    return () => {
      // Only fire on unmount (user navigates away), not on re-renders
      trackEvent('page_view', {
        duration: Date.now() - startTime.current,
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 滚动追踪
  useEffect(() => {
    const handleScroll = () => {
      const scrollHeight = document.documentElement.scrollHeight - window.innerHeight
      const scrollPercent = (scrollHeight > 0 ? window.scrollY / scrollHeight : 0) * 100

      if (scrollPercent >= 50 && !scroll50Fired.current) {
        scroll50Fired.current = true
        trackEvent('scroll_50', {
          time_on_page: Date.now() - startTime.current,
        })
      }

      if (scrollPercent >= 100 && !scroll100Fired.current) {
        scroll100Fired.current = true
        trackEvent('scroll_100', {
          time_on_page: Date.now() - startTime.current,
        })
      }
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [trackEvent])

  return { trackEvent }
}
