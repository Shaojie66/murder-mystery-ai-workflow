import { request } from './client'

export interface LLMConfig {
  provider: string
  api_key: string | null
  base_url: string | null
  model: string | null
}

export interface NotionConfig {
  enabled: boolean
  api_key: string | null
  database_id: string | null
}

export interface ObsidianConfig {
  enabled: boolean
  vault_path: string | null
}

export interface Settings {
  llm: LLMConfig
  notion: NotionConfig
  obsidian: ObsidianConfig
}

export async function getSettings(): Promise<Settings> {
  return request<Settings>('/settings')
}

export async function updateSettings(settings: Settings): Promise<Settings> {
  return request<Settings>('/settings', {
    method: 'PUT',
    body: JSON.stringify(settings),
  })
}

export async function testLLMConnection(settings: Settings): Promise<{
  success: boolean
  model: string
  tokens: number
  response_preview: string
}> {
  return request('/settings/test-llm', {
    method: 'POST',
    body: JSON.stringify(settings),
  })
}

export async function testNotionConnection(notion: NotionConfig): Promise<{
  success: boolean
  user: unknown
}> {
  return request('/settings/test-notion', {
    method: 'POST',
    body: JSON.stringify(notion),
  })
}

export async function testObsidianConnection(obsidian: ObsidianConfig): Promise<{
  success: boolean
  vault_path: string
}> {
  return request('/settings/test-obsidian', {
    method: 'POST',
    body: JSON.stringify(obsidian),
  })
}
