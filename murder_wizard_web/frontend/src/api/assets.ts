import { request } from './client'

export interface ImageGenerateRequest {
  prompt: string
  resolution?: string
  model?: string
  aspect_ratio?: string
  wait?: boolean
}

export interface VideoGenerateRequest {
  prompt: string
  duration?: number
  resolution?: string
  aspect_ratio?: string
  model?: string
  wait?: boolean
}

export interface Img2VideoRequest {
  image_url: string
  prompt: string
  duration?: number
  resolution?: string
  model?: string
  wait?: boolean
}

export async function generateImage(req: ImageGenerateRequest): Promise<{ url: string; status: string }> {
  return request('/assets/image/generate', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function generateText2Video(req: VideoGenerateRequest): Promise<{ url: string; status: string }> {
  return request('/assets/video/text2video', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function generateImg2Video(req: Img2VideoRequest): Promise<{ url: string; status: string }> {
  return request('/assets/video/img2video', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function getTaskStatus(taskId: string): Promise<Record<string, unknown>> {
  return request(`/assets/task/${taskId}`)
}
