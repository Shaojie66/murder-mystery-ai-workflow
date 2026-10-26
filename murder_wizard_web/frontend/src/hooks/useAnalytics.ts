import { useCallback, useEffect, useRef } from 'react'

type EventName =
  | 'page_view'
  | 'page_leave'
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

function getVisitId(): string {
  // sessionStorage：同一标签页的一次访问内稳定；StrictMode 重新挂载拿到同一个 id
  const KEY = 'mw_visit_id'
  try {
    let id = sessionStorage.getItem(KEY)
    if (!id) {
      id = Math.random().toString(36).slice(2) + Date.now().toString(36)
      sessionStorage.setItem(KEY, id)
    }
    return id
  } catch {
    return Math.random().toString(36).slice(2) + Date.now().toString(36)
  }
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
  // 一次访问一个 id：后端按它去重 page_view，React StrictMode 的重复挂载也只计一次
  const visitId = useRef(getVisitId())

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
          visit_id: visitId.current,
          ...params,
        }),
      }).catch(() => {})
    },
    [variant]
  )

  // 页面访问：每次访问只发一次 page_view；离开时发 page_leave（带停留时长），它不算访问
  useEffect(() => {
    if (!pageViewFired.current) {
      pageViewFired.current = true
      trackEvent('page_view', {
        referrer: document.referrer,
        user_agent: navigator.userAgent,
      })
    }

    startTime.current = Date.now()

    return () => {
      trackEvent('page_leave', {
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
