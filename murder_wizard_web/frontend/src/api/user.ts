import { request, getUserId } from './client'

export { getUserId }

export interface PlanInfo {
  plan: 'free' | 'pro'
  project_limit: number
  projects_used: number
  is_upgrade_available: boolean
}

export interface AnalyticsData {
  clicks: {
    total: number
    by_trigger: Record<string, number>
    all: Array<{ trigger: string; user_plan: string; created_at: string }>
  }
  funnel: {
    by_action: Record<string, Record<string, number>>
    totals: Record<string, number>
    events: Array<{ trigger: string; action: string; user_plan: string; created_at: string }>
  }
}

export async function getPlan(): Promise<PlanInfo> {
  return request('/user/plan')
}

export async function recordUpgradeClick(trigger: string): Promise<{ success: boolean; total_clicks: number }> {
  return request('/user/plan/upgrade-click', {
    method: 'POST',
    body: JSON.stringify({ trigger }),
  })
}

export async function recordExperimentEvent(
  trigger: string,
  action: 'view' | 'click' | 'dismiss' | 'upgrade_navigate',
  userPlan: string = 'free'
): Promise<{ success: boolean }> {
  return request('/user/plan/experiment-event', {
    method: 'POST',
    body: JSON.stringify({ trigger, action, user_plan: userPlan }),
  })
}

export async function incrementProjectsUsed(): Promise<{ projects_used: number }> {
  return request('/user/plan/projects-used', { method: 'POST' })
}

export async function getAnalytics(): Promise<AnalyticsData> {
  return request('/user/plan/analytics')
}

export async function activatePro(): Promise<{ success: boolean; plan: string }> {
  return request('/user/plan/activate-pro', { method: 'POST' })
}

export interface FunnelEventData {
  event_type: string
  project_name: string
  stage?: number | null
  success?: boolean | null
  metadata?: string | null
}

export interface FunnelAnalytics {
  events: Array<{ event_type: string; project_name: string; stage: number | null; success: number | null; metadata: string | null; created_at: string }>
  by_project: Record<string, FunnelEventData[]>
  summary: {
    projects_created: number
    expands_triggered: number
    expands_completed: number
    phase_started: Record<number, number>
    phase_completed: Record<number, number>
  }
}

export async function recordFunnelEvent(event: FunnelEventData): Promise<{ success: boolean }> {
  return request('/user/plan/funnel-event', {
    method: 'POST',
    body: JSON.stringify(event),
  })
}

export async function getFunnelAnalytics(): Promise<FunnelAnalytics> {
  return request('/user/plan/funnel-analytics')
}
