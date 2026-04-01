# Metrics Dashboard: murder-wizard Pro

**Date**: 2026-04-01
**Stage**: Pre-launch (building metrics foundation before go-live)
**North Star**: Projects completed through Stage 2 (script creation)

---

## 1. North Star Metric

**Metric**: `scripts_completed_rate`
**Definition**: (Projects reaching Stage 2 or beyond, with at least one AI check run) ÷ (Total registered projects created in last 30 days)
**Formula**: `COUNT(projects WHERE current_stage ≥ 'stage_2_script' AND ai_checks_run > 0) / COUNT(projects WHERE created_at > NOW() - 30d)`
**Why this North Star**:
- Captures **value delivered** — a script reaching Stage 2 means the creator got real output, not just logged in
- Is a **leading indicator** of both AI utility and retention — users who finish Stage 2 are far more likely to subscribe and continue
- Is **actionable** — the team can improve Stage 2 conversion through UX, AI quality, and onboarding
- Avoids vanity — "signups" or "page views" don't measure whether the product works

**Current value**: Unknown (pre-launch)
**Target**: ≥40% of registered projects reach Stage 2 within 14 days of creation

---

## 2. Input Metrics (Levers)

These are the 5 levers that drive the North Star. Each is directly controllable by the team.

### I1: Activation Rate
**Definition**: New registrations who run Stage 1 (mechanism design) within 7 days of signup
**Formula**: `COUNT(users WHERE first_phase_run WITHIN 7d OF signup) / COUNT(total_signups)`
**Target**: ≥30% activation within 7 days
**Why it matters**: No Stage 1 run = never activated = will never reach Stage 2
**Driver of improvement**: Onboarding flow, landing page clarity, email drip

### I2: Stage 1→2 Conversion Rate
**Definition**: Activated projects that advance from Stage 1 to Stage 2
**Formula**: `COUNT(projects WHERE current_stage = 'stage_2') / COUNT(projects WHERE current_stage = 'stage_1')`
**Target**: ≥50% Stage 1→2 conversion
**Why it matters**: The hardest workflow step — going from brief to script. AI quality and UX here is everything.
**Driver of improvement**: AI output quality, prompt templates, UX for reviewing/accepting output

### I3: AI Detection Usage Rate
**Definition**: Projects that run at least one AI consistency check (Stage 4 or audit) per month
**Formula**: `COUNT(DISTINCT projects WHERE audit_events > 0) / COUNT(total_active_projects)`
**Target**: ≥60% of active projects use AI detection
**Why it matters**: AI detection is murder-wizard's unique differentiator vs. manual creation. High usage = product is delivering on its core promise.
**Driver of improvement**: UX that surfaces detection naturally (not buried in menu), quality of detection results

### I4: Collaboration Adoption
**Definition**: Projects with 2+ team members, among projects that are Studio tier
**Formula**: `COUNT(team_projects WHERE member_count ≥ 2) / COUNT(team_projects)`
**Target**: ≥40% of Studio tier projects are actively collaborated on
**Why it matters**: Collaboration is the Studio tier's core value proposition. Solo usage = studio tier is being bought by individuals, not teams.
**Driver of improvement**: Invite UX, role permissions, real-time collaboration feel

### I5: Subscription Conversion Rate
**Definition**: Free users who convert to any paid tier within 30 days of project creation
**Formula**: `COUNT(users WHERE first_paid_subscription WITHIN 30d) / COUNT(free_signups_last_30d)`
**Target**: ≥5% conversion (matches PRD KR2)
**Why it matters**: Revenue funds the business. Also signals product-market fit — if people won't pay, something is wrong.
**Driver of improvement**: Trial experience, feature gating, pricing page clarity

---

## 3. Health Metrics (Should Stay Stable)

| Metric | Healthy | Yellow | Red | Frequency |
|---|---|---|---|---|
| **Error rate (API)** | <1% | 1-5% | >5% | Real-time |
| **AI response time (p95)** | <15s | 15-30s | >30s | Per request |
| **Landing page bounce rate** | <60% | 60-75% | >75% | Daily |
| **Churn rate (monthly)** | <5% | 5-10% | >10% | Monthly |
| **Support ticket volume** | <10/week | 10-20/week | >20/week | Weekly |
| **LLM API cost / completion** | Stable ±10% | ±10-25% | >25% variance | Weekly |

**Rationale**:
- API errors and AI latency directly destroy user trust in a creative tool
- Bounce rate tells you if the landing page is reaching the right audience
- Churn >10% means the product isn't sticky — investigate onboarding or AI quality
- Cost variance signals either prompt drift or model pricing changes

---

## 4. Counter-Metrics (Watch For Gaming)

| Metric | Why It Matters | What to Watch |
|---|---|---|
| **Page views without signup** | Vanity metric, not value | page_views ↑ but email_signups flat = wrong traffic |
| **Signup-to-ghost rate** | Signups with zero activity | >50% ghost rate = onboarding broken |
| **AI check volume without context** | Users running checks without understanding output | High check count, low Stage 2 completion = using checks as "magic button" not actually reading results |
| **Team seats purchased vs. used** | Studios buying 3 seats, using 1 | seat_utilization < 50% = product isn't compelling enough for collaboration |

---

## 5. Metrics Tree

```
North Star: scripts_completed_rate (≥40% in 14d)
│
├── I1: Activation Rate (≥30% in 7d)
│   └── Landing page quality → onboarding drip → first-run wizard UX
│
├── I2: Stage 1→2 Conversion (≥50%)
│   └── AI output quality → prompt templates → review UX
│
├── I3: AI Detection Usage (≥60% of active projects)
│   └── Detection quality → UX discoverability → creator confidence
│
├── I4: Collaboration Adoption (≥40% of Studio projects)
│   └── Invite UX → real-time experience → role permissions
│
└── I5: Subscription Conversion (≥5% in 30d)
    └── Trial experience → feature gating → pricing clarity

Health: Error rate <1% | AI latency p95 <15s | Bounce <60% | Churn <5%

Counter: Ghost signup rate | AI check abuse | Seat underutilization
```

---

## 6. A/B Test Metrics (Landing Page)

From the metrics_plan.md, tracking experiment 1 (fake door):

| Metric | Definition | Target |
|---|---|---|
| Variant A page views | Visitors to /landing-a | — |
| Variant B page views | Visitors to /landing-b | — |
| Email modal open rate | modal_open / page_view | >15% |
| Email submission rate | email_submit / page_view | >5% |
| Submission → Pro signup | first_subscription within 14d / email_submissions | >3% |
| **Primary: Conversion rate** | email_submissions / page_views | Variant winner |
| **Secondary: Trial signup** | first_trial_started / email_submissions | Variant winner |

**Decision rule**: If Variant B submission rate > Variant A × 1.2 AND total volume > 200 visitors per variant → ship Variant B.

---

## 7. Implementation Notes

### Data Sources
| Event | Source | Notes |
|---|---|---|
| Page views, bounces | Frontend analytics hook (`useAnalytics.ts`) | POST /api/analytics/track |
| Email signups | Landing page | POST /api/landing/subscribe |
| Project creation, stage | Backend projects API | session state |
| AI checks run | Phase events (SSE) | stage_complete events |
| Subscriptions | Subscription page | POST /api/subscription |
| Support tickets | Manual (email/WeChat for now) | Track in spreadsheet initially |

### Analytics Implementation (Already Built)
- `useAnalytics.ts` tracks: page_view, scroll_50, scroll_100, modal_open, cta_click, email_submit
- `/api/analytics/track` stores events in memory (dev) — swap for database in prod
- `/api/analytics/summary` computes conversion rates by variant
- `/metrics` page displays charts via Recharts

### Refresh Cadence
- **Real-time**: API error rate, AI latency (from server logs)
- **Hourly**: Page views, email submissions (via analytics API)
- **Daily**: Stage progression, activation rate, A/B test results
- **Weekly**: Churn, cohort analysis, funnel metrics
- **Monthly**: LTV, MRR, NPS survey

---

## 8. Review Cadence

| Cadence | What | Who |
|---|---|---|
| **Daily (standup)** | North Star + Health metrics | Full team |
| **Weekly (growth)** | A/B test results, activation funnel, conversion rates | PM + Eng |
| **Monthly (review)** | Full dashboard, cohort analysis, OKR progress | Full team |
| **Quarterly** | Metrics framework review — are these still the right metrics? | PM lead |

---

## 9. Current Gaps to Fill Before Launch

| Gap | Priority | How to Fix |
|---|---|---|
| No project funnel tracking | P0 | Add `project_created`, `stage_1_started`, `stage_2_completed` events to analytics |
| No subscription revenue tracking | P0 | Hook `/api/subscription` into analytics |
| NPS not being collected | P1 | Add in-app NPS widget after Stage 2 completion |
| No cohort analysis | P2 | Set up cohort tracking once 30-day cohorts exist |
| Analytics in-memory only | P2 | Migrate to Postgres + Grafana once paying users arrive |
