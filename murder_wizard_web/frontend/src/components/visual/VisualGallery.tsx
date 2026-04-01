import { useState } from 'react'
import { generateImage } from '../../api/assets'

interface VisualGalleryProps {
  prompts?: string // image prompts from image-prompts.md
}

export default function VisualGallery({ prompts }: VisualGalleryProps) {
  const [generating, setGenerating] = useState(false)
  const [generatedImages, setGeneratedImages] = useState<Array<{ url: string; prompt: string }>>([])
  const [error, setError] = useState<string | null>(null)

  // Extract individual prompts from the markdown content
  const extractPrompts = (content: string): string[] => {
    if (!content) return []
    // Look for prompt lines or image descriptions
    const lines = content.split('\n')
    const prompts: string[] = []
    for (const line of lines) {
      // Skip headers, empty lines, and non-prompt content
      if (line.startsWith('#') || line.startsWith('##') || line.startsWith('###')) continue
      if (!line.trim()) continue
      // Clean up the line
      const cleaned = line.replace(/^[-*]\s*/, '').replace(/^\d+\.\s*/, '').trim()
      if (cleaned.length > 10) {
        prompts.push(cleaned)
      }
    }
    return prompts.slice(0, 6) // Limit to 6 images
  }

  const handleGenerate = async () => {
    if (!prompts) return
    const promptList = extractPrompts(prompts)
    if (promptList.length === 0) {
      setError('没有找到可用的图像提示词')
      return
    }

    setGenerating(true)
    setError(null)
    const results: Array<{ url: string; prompt: string }> = []

    try {
      for (const prompt of promptList) {
        try {
          const result = await generateImage({
            prompt,
            resolution: '1K',
            model: 'q3-fast',
            aspect_ratio: '16:9',
          })
          results.push({ url: result.url, prompt })
        } catch {
          // Silent failure — loop continues with remaining prompts
        }
      }
      setGeneratedImages(results)
    } catch (e) {
      setError(e instanceof Error ? e.message : '生成失败')
    } finally {
      setGenerating(false)
    }
  }

  if (!prompts) {
    return (
      <div
        style={{
          padding: '2rem',
          border: '1px solid var(--border-subtle)',
          background: 'var(--bg-raised)',
          textAlign: 'center',
        }}
      >
        <p style={{ color: 'var(--text-faint)', fontFamily: "'Crimson Pro', serif", fontStyle: 'italic' }}>
          请先运行阶段3生成图像提示词
        </p>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <div className="label" style={{ color: 'var(--text-faint)' }}>
          视觉物料
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          style={{
            padding: '0.5rem 1rem',
            fontSize: '13px',
            fontFamily: "'Crimson Pro', serif",
            background: generating ? 'var(--bg-elevated)' : 'var(--accent-crimson)',
            border: '1px solid var(--accent-crimson)',
            color: 'var(--text-cream)',
            cursor: generating ? 'not-allowed' : 'pointer',
            opacity: generating ? 0.6 : 1,
          }}
        >
          {generating ? '生成中...' : '▶ Vidu 生成图像'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div
          style={{
            padding: '0.75rem 1rem',
            marginBottom: '1rem',
            border: '1px solid var(--output-error-border)',
            background: 'var(--output-error-bg)',
            color: 'var(--output-error)',
            fontFamily: "'Crimson Pro', serif",
            fontSize: '13px',
          }}
        >
          {error}
        </div>
      )}

      {/* Generated Images */}
      {generatedImages.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
            gap: '1rem',
            marginBottom: '1.5rem',
          }}
        >
          {generatedImages.map((img, idx) => (
            <div
              key={idx}
              style={{
                border: '1px solid var(--border)',
                background: 'var(--bg-raised)',
                overflow: 'hidden',
              }}
            >
              <img
                src={img.url}
                alt={img.prompt}
                style={{
                  width: '100%',
                  height: '140px',
                  objectFit: 'cover',
                  display: 'block',
                }}
                onError={(e) => {
                  const img = e.target as HTMLImageElement
                  img.style.display = 'none'
                  const placeholder = img.nextElementSibling as HTMLElement
                  if (placeholder) {
                    placeholder.style.display = 'flex'
                  }
                }}
              />
              {/* Placeholder shown when image fails to load */}
              <div
                aria-hidden="true"
                style={{
                  display: 'none',
                  height: '140px',
                  background: 'var(--bg-base)',
                  borderBottom: '1px solid var(--border-subtle)',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <span style={{ color: 'var(--border)', fontSize: '2rem' }}>◻</span>
              </div>
              <div
                style={{
                  padding: '0.5rem',
                  fontFamily: "'Crimson Pro', serif",
                  fontSize: '11px',
                  color: 'var(--text-faint)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
                title={img.prompt}
              >
                {img.prompt.slice(0, 50)}...
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Placeholder when no images generated */}
      {generatedImages.length === 0 && !generating && (
        <div
          style={{
            padding: '3rem 2rem',
            border: '1px solid var(--border-subtle)',
            background: 'var(--bg-raised)',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              fontFamily: "'Playfair Display', serif",
              fontSize: '2rem',
              color: 'var(--border)',
              marginBottom: '0.5rem',
            }}
          >
            ◻
          </div>
          <p style={{ color: 'var(--text-faint)', fontFamily: "'Crimson Pro', serif", fontStyle: 'italic', fontSize: '14px' }}>
            点击「Vidu 生成图像」从提示词创建视觉物料
          </p>
        </div>
      )}
    </div>
  )
}
