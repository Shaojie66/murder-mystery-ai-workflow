// API types for the murder-wizard web backend

export interface Project {
  name: string
  path: string
  story_type: string
  is_prototype: boolean
  current_stage: string
  created_at: string | null
  artifact_count: number
}

export interface ArtifactInfo {
  name: string
  exists: boolean
  size?: number
  modified?: string
}

export interface ProjectDetails extends Project {
  artifacts: Record<string, ArtifactInfo>
  can_expand: boolean
  can_audit: boolean
}

export interface CreateProjectRequest {
  name: string
  story_type: string
  is_prototype: boolean
  era?: string
  answers?: Record<string, string>
}

// SSE event types
export type SSEEventType =
  | 'start'
  | 'progress'
  | 'token'
  | 'cost'
  | 'artifact'
  | 'stage_complete'
  | 'round_complete'
  | 'revision_complete'
  | 'audit_complete'
  | 'expand_complete'
  | 'error'
  | 'end'
  | 'keepalive'

export interface SSEEvent {
  type: SSEEventType
  data: Record<string, unknown>
}

export interface PhaseStartEvent {
  phase: number
  stage: string
}

export interface TokenEvent {
  content: string
  delta: boolean
}

export interface ProgressEvent {
  step: string
  percent: number
}

export interface CostEvent {
  tokens: number
  cost: number
  total_cost: number
}

export interface StageCompleteEvent {
  phase: number
  success: boolean
  artifacts: string[]
  total_cost: number
  total_tokens: number
}

// Matrix types
export type CognitionState = '知' | '疑' | '昧' | '否' | '误信' | '隐瞒'

export interface CognitiveState {
  state: CognitionState
  detail: string
  evidence_refs: string[]
}

export interface CharacterEntry {
  character_id: string
  name: string
  role: string
  public_relationship: string
  secret_relationship: Record<string, string>
  surface_info: string
  middle_info: string
  deep_info: string
  belief_before: string
  belief_trigger: string
  belief_after: string
  can_say: string[]
  cannot_say: string[]
  must_deny: string[]
  event_cognitions: Record<string, CognitiveState>
}

export interface EvidenceItem {
  evidence_id: string
  name: string
  description: string
  source_event: string
  source_character: string
  chain_role: string
  points_to: string
}

export interface CharacterMatrix {
  version: string
  char_count: number
  event_count: number
  is_prototype: boolean
  characters: Record<string, CharacterEntry>
  evidence: Record<string, EvidenceItem>
  meta: {
    created_at: string
    updated_at: string
    commit_hash: string
  }
}

// Cost types
export interface CostSummary {
  total_cost: number
  total_tokens: number
  by_operation: Array<{
    operation: string
    tokens: number
    cost: number
    count: number
  }>
  by_date: Array<{ date: string; cost: number }>
  by_model: Record<string, { model: string; tokens: number; cost: number }>
}
