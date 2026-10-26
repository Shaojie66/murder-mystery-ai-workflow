// 把 audit_report.md（murder_wizard/wizard/audit.py 的 render_report 输出）解析成结构化数据。
// 报告只以 Markdown 落盘（不新增持久化格式），所以这里宽容解析；
// 任何一步对不上都返回 null，页面回退到原文展示。

export type AuditStatus = 'passed' | 'waived' | 'blocked' | 'incomplete'

export interface AuditIssue {
  ref: string
  severity: string
  dimension: string
  waived: boolean
  key: string
  characters: string
  events: string
  location: string
  verify: string
  quote: string
  problem: string
  suggestion: string
  waiverNote: string
  waiverLine: string
}

export interface AuditRound {
  title: string
  status: string
  p0: string
  p1: string
  p2: string
  chars: string
  reason: string
}

export interface AuditMaterial {
  file: string
  rounds: string
  chars: string
  sha: string
  state: string
}

export interface AuditPatch {
  id: string
  heading: string
  state: string
  original: string
  replacement: string
  rationale: string
}

export interface ParsedAudit {
  status: AuditStatus
  statusLabel: string
  conclusion: string
  generatedAt: string
  model: string
  workState: string
  caveat: string
  materials: AuditMaterial[]
  notCovered: string
  problems: string[]
  notes: string[]
  rounds: AuditRound[]
  groups: { title: string; issues: AuditIssue[] }[]
  waiverSummary: string[]
  patches: AuditPatch[]
  patchNotes: string[]
  appendix: string
}

const STATUS_RE = /^审计状态：(.+?)（status=(passed|waived|blocked|incomplete)）/

function sectionsOf(text: string): Map<string, string[]> {
  const out = new Map<string, string[]>()
  let current = '__head__'
  out.set(current, [])
  for (const line of text.split('\n')) {
    const m = /^## (.+)$/.exec(line)
    if (m) {
      current = m[1].trim()
      out.set(current, [])
    } else {
      out.get(current)!.push(line)
    }
  }
  return out
}

function tableRows(lines: string[]): string[][] {
  return lines
    .filter((l) => l.trim().startsWith('|') && !/^\|\s*-+/.test(l.trim()))
    .map((l) => l.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim()))
    .slice(1) // 去掉表头
}

function bullets(lines: string[]): string[] {
  return lines.filter((l) => l.startsWith('- ')).map((l) => l.slice(2).trim())
}

function parseIssues(lines: string[]): AuditIssue[] {
  const issues: AuditIssue[] = []
  let cur: AuditIssue | null = null
  for (const raw of lines) {
    const h = /^### (\S+) \[(P\d)\] (.+?)(（已豁免）)?$/.exec(raw)
    if (h) {
      cur = {
        ref: h[1], severity: h[2], dimension: h[3], waived: !!h[4], key: '', characters: '', events: '',
        location: '', verify: '', quote: '', problem: '', suggestion: '', waiverNote: '', waiverLine: '',
      }
      issues.push(cur)
      continue
    }
    if (!cur) continue
    const line = raw.trim()
    let m: RegExpExecArray | null
    if ((m = /^- key：(.+)$/.exec(line))) cur.key = m[1]
    else if ((m = /^- 角色：(.*?)　事件：(.*)$/.exec(line))) { cur.characters = m[1]; cur.events = m[2] }
    else if ((m = /^- 位置：(.+?)（定位校验：(.+?)）$/.exec(line))) { cur.location = m[1]; cur.verify = m[2] }
    else if ((m = /^- 引用：(.+)$/.exec(line))) cur.quote = m[1]
    else if ((m = /^- 问题：(.+)$/.exec(line))) cur.problem = m[1]
    else if ((m = /^- 建议：(.+)$/.exec(line))) cur.suggestion = m[1]
    else if ((m = /^- 豁免：(.+)$/.exec(line))) cur.waiverNote = m[1]
    else if ((m = /^- 若确认可接受，在 \.known_p0 加一行：`(.+)`$/.exec(line))) cur.waiverLine = m[1]
  }
  return issues
}

function parsePatches(lines: string[]): { patches: AuditPatch[]; notes: string[] } {
  const patches: AuditPatch[] = []
  const notes: string[] = []
  let cur: AuditPatch | null = null
  for (const raw of lines) {
    const h = /^### (F\d+)　(.+)$/.exec(raw)
    if (h) {
      cur = { id: h[1], heading: h[2], state: '', original: '', replacement: '', rationale: '' }
      patches.push(cur)
      continue
    }
    const line = raw.trim()
    if (!line) continue
    let m: RegExpExecArray | null
    if (cur && (m = /^- 状态：(.+)$/.exec(line))) cur.state = m[1]
    else if (cur && (m = /^- 原文：(.*)$/.exec(line))) cur.original = m[1]
    else if (cur && (m = /^- 建议改为：(.*)$/.exec(line))) cur.replacement = m[1]
    else if (cur && (m = /^- 理由：(.*)$/.exec(line))) cur.rationale = m[1]
    else if (!line.startsWith('###')) notes.push(line.replace(/^- /, ''))
  }
  return { patches, notes }
}

export function parseAuditReport(text: string): ParsedAudit | null {
  const first = text.split('\n', 1)[0] ?? ''
  const sm = STATUS_RE.exec(first)
  if (!sm) return null
  const sec = sectionsOf(text)
  const head = sec.get('__head__') ?? []
  const meta = bullets(head)
  const pick = (prefix: string) => (meta.find((b) => b.startsWith(prefix)) ?? '').slice(prefix.length)
  const caveat = head.find((l) => l.startsWith('> '))?.slice(2) ?? ''

  const materialsLines = sec.get('审计输入') ?? []
  const materials = tableRows(materialsLines).map((c) => ({
    file: c[0] ?? '', rounds: c[1] ?? '', chars: c[2] ?? '', sha: c[3] ?? '', state: c[4] ?? '',
  }))
  const notCovered = (materialsLines.find((l) => l.startsWith('未覆盖：')) ?? '').slice('未覆盖：'.length)

  const rounds = tableRows(sec.get('轮次状态') ?? []).map((c) => ({
    title: c[0] ?? '', status: c[1] ?? '', p0: c[2] ?? '0', p1: c[3] ?? '0', p2: c[4] ?? '0', chars: c[5] ?? '', reason: c[6] ?? '',
  }))

  const groups: { title: string; issues: AuditIssue[] }[] = []
  for (const [name, lines] of sec) {
    const g = /^(未豁免 P0|已豁免 P0|P1|P2)（\d+）$/.exec(name)
    if (g) groups.push({ title: g[1], issues: parseIssues(lines) })
  }

  const waiverLines = sec.get('豁免情况') ?? []
  const { patches, notes: patchNotes } = parsePatches(sec.get('修复建议') ?? [])
  const appendix = (sec.get('附录：失败轮次原文') ?? []).join('\n').trim()

  return {
    status: sm[2] as AuditStatus,
    statusLabel: sm[1],
    conclusion: pick('结论：'),
    generatedAt: pick('生成时间：'),
    model: pick('模型：'),
    workState: pick('作品状态：'),
    caveat,
    materials,
    notCovered,
    problems: bullets(sec.get('材料问题') ?? []),
    notes: bullets(sec.get('说明') ?? []),
    rounds,
    groups,
    waiverSummary: waiverLines.map((l) => l.trim()).filter(Boolean).map((l) => l.replace(/^- /, '')),
    patches,
    patchNotes,
    appendix,
  }
}
