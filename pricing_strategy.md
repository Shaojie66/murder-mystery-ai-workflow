# Pricing Strategy: murder-wizard Pro

**Date**: 2026-04-01
**Product**: murder-wizard Pro (SaaS subscription)
**Stage**: Pre-launch, validated through user research and competitor analysis

---

## 1. Current State

| | |
|---|---|
| **Product** | AI-powered murder mystery script creation — CLI free, Pro web SaaS |
| **Current Pro price** | ¥29/month (single tier, draft) |
| **Model** | Per-user subscription, monthly/annual |
| **CLI** | Continues free — core users, technical creators |
| **Target KRs** | 500 signups in 3 months, ≥5% paid conversion, ≥70% renewal |

---

## 2. Pricing Model Analysis

Three models were evaluated against murder-wizard's value structure:

| Model | Fit | Verdict |
|---|---|---|
| Flat per-user | Simple, predictable | Good for individuals, underprices studios |
| Per-seat team | Captures studio value | Right model, needs ≥2 tiers |
| Usage-based (API credits) | Misaligns — creative output isn't metered | Wrong fit for this product |
| Freemium → upgrade | Good for top-of-funnel | Works if free tier has genuine value |

**Recommendation: Tiered per-seat subscription with a permanent free CLI tier.**

The single ¥29 tier leaves money on the table from studios and underprices independent creators who would pay more. The market segments have sufficiently different WTP (¥9-19 amateur, ¥29 independent, ¥79-149 studio) to support at least 3 paid tiers.

---

## 3. Recommended Pricing Structure

### 3.1 Tier Architecture

| | Solo Pro | Studio | Studio+ |
|---|---|---|---|
| **Price (monthly)** | ¥29 | ¥79 | ¥199 |
| **Price (annual)** | ¥249 (≈¥21/mo) | ¥699 (≈¥58/mo) | ¥1,799 (≈¥150/mo) |
| **Seats** | 1 | 3 | 10 |
| **Projects** | 3 active | 10 active | Unlimited |
| **AI checks/month** | 20 | 100 | Unlimited |
| **Templates** | Basic | Full library | Full + custom |
| **Cloud storage** | 1 GB | 10 GB | 100 GB |
| **Priority LLM** | Standard | Priority | Dedicated |
| **Support** | Community | Email | Dedicated |
| **Team features** | — | Real-time collab, roles | + Admin, audit log |

**Per-user overage**: ¥19/seat/month beyond included seats (Studio+, up to 20 extra)

### 3.2 Why This Architecture Works

- **¥29 Solo Pro** — anchors the existing vision, low-risk launch tier
- **¥79 Studio** — 2.7× Solo price for 3× the value, captures the studio segment that was never addressed
- **¥199 Studio+** — 6.9× Solo price for serious studios with 10 seats and unlimited AI
- **Annual discount (25%)** — reduces churn, improves LTV, predictable revenue
- **Overage model** — natural upsell path for studios that grow

### 3.3 Free CLI (Permanent)

The free CLI tier is not a "freemium conversion funnel" — it's a moat. It:
- Keeps technical users in the ecosystem
- Generates word-of-mouth from the creator community
- Provides a no-risk entry point to the brand
- Makes competitor adoption harder

Free CLI does NOT include cloud sync, AI features, or any Pro web features. The gap between free and ¥29 is wide enough to justify conversion.

---

## 4. Competitive Benchmark

| Product | Model | Price (CNY) | Notes |
|---|---|---|---|
| Notion | Per-seat | ¥60/user/mo (annual) | General productivity, well-known |
| ChatGPT Plus | Per-user | ¥140/mo | AI assistant, established |
| 秘塔写作猫 | Per-user | ¥49-199/mo | Chinese AI writing, similar market |
| 橙瓜码字 | Per-user | ¥30-80/mo | Chinese script/novel writing tool |
| 途游写作 | Per-user | ¥19-59/mo | Budget writing tool |
| **murder-wizard Pro** | **Per-seat** | **¥29/79/199** | **Niche creative tool, first-mover** |

**Positioning**: murder-wizard sits at or below the floor of Chinese productivity SaaS — ¥29 Solo is the entry price of Notion's annual plan. The reasoning: first-mover in a niche category should price to acquire users, not maximize early ARPU. Raise prices after network effects kick in.

---

## 5. Willingness to Pay Estimates

Based on discovery plan user research segments:

| Segment | Evidence | WTP Estimate | Primary Driver |
|---|---|---|---|
| Amateur (enthusiast) | Low technical confidence, hobby budget | ¥9-19/mo | Time savings, ease of use |
| Independent creator | Experienced, values efficiency, solo workflow | ¥29-49/mo | Cloud access, AI detection |
| Studio (2-5 people) | Multiple concurrent projects, collaboration pain | ¥59-99/mo | Team features, seat scaling |
| Publisher/producer | Needs templates, compliance, bulk management | ¥149-249/mo | Scale, support, customization |

**Confidence**: Medium. WTP estimates are inferred from comparable Chinese creative tool pricing, not yet validated with Van Westendorp survey.

---

## 6. Revenue Projections

Assumptions: 500 signups in month 3, conservative growth curve.

| Scenario | Conversion | Solo | Studio | Studio+ | Y1 ARR |
|---|---|---|---|---|---|
| **Conservative** | 3% paid, 70% annual | 8 | 4 | 0 | ¥4,200 |
| **Expected** | 5% paid, 50% annual | 15 | 7 | 2 | ¥10,500 |
| **Optimistic** | 8% paid, 60% annual | 30 | 12 | 3 | ¥24,000 |

**Y1 expected ARR**: ¥10,500 (~US$1,450) — early stage, validate first.

**Long-range (Y3, if 500 paying users)**: ¥180K-360K ARR depending on tier mix.

**Note**: These are starting-point estimates. Real pricing experiments will be more accurate than any projection.

---

## 7. Free vs Paid Boundary

| Feature | Free CLI | Solo Pro ¥29 | Studio ¥79 | Studio+ ¥199 |
|---|---|---|---|---|
| 8-stage workflow | ✅ | ✅ | ✅ | ✅ |
| Local storage | ✅ | ✅ | ✅ | ✅ |
| Web interface | ❌ | ✅ | ✅ | ✅ |
| Cloud sync | ❌ | ✅ | ✅ | ✅ |
| AI detection | ❌ | 20 checks/mo | 100 checks/mo | Unlimited |
| Templates | ❌ | Basic | Full library | Full + custom |
| Team collaboration | ❌ | ❌ | ✅ (3 seats) | ✅ (10 seats) |
| Priority LLM | ❌ | Standard | Priority | Dedicated |
| Support | ❌ | Community | Email | Dedicated |

**Key design principle**: Free tier is the "try it" experience. Paid tiers are "live with it" — no artificial time limits.

---

## 8. Launch Pricing Experiments

### Experiment 1: Price Anchoring (A/B test)
- **What**: ¥29 vs ¥39 vs ¥49 Solo tier
- **Hypothesis**: Users anchor on ¥29 but ¥39 has same conversion rate, doubling revenue per user
- **Method**: A/B/C test on pricing page over 4 weeks
- **Metric**: Conversion rate × price = revenue per visitor
- **Effort**: Low (change one number on the pricing page)

### Experiment 2: Annual Discount Framing (A/B test)
- **What**: "Save 25%" vs "¥249/year" vs "Less than ¥1/day"
- **Hypothesis**: "Less than ¥1/day" reduces price sensitivity without changing the number
- **Method**: A/B test on landing page CTA
- **Metric**: Annual plan uptake rate
- **Effort**: Low

### Experiment 3: Studio Tier Opening (Fake door)
- **What**: Show ¥79 Studio tier but disable signup — measure clicks
- **Hypothesis**: If click-through rate >15% of Solo interest, there's demand worth building for
- **Method**: Feature stub with waitlist CTA
- **Metric**: Waitlist signups / Solo conversions
- **Effort**: Low

### Experiment 4: Overage vs Seat Flat (Survey)
- **What**: Do studio users prefer ¥79 flat for 3 seats or ¥29/seat (¥87 for 3)?
- **Method**: Survey to existing CLI users who match studio profile
- **Effort**: Medium

---

## 9. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Studios expect seat-based, get wrong model | Medium | High | Survey before building; Experiment 4 |
| Price too low to signal quality | Medium | Medium | A/B test ¥29 vs ¥39 first |
| Free CLI users never convert | High | High | Target indie creators who already pay for tools |
| No竞争对手 → no reference pricing | Medium | Low | Use 秘塔/橙瓜 as anchors; iterate |
| AI detection accuracy disappoints | Medium | High | Include detection quality in onboarding; free detection trial |
| CNY exchange rate affects hosting costs | Low | Medium | Price in CNY, not USD |

---

## 10. Recommended Next Steps (Priority Order)

1. **Run Experiment 1 (¥29 vs ¥39)** before launch — costs nothing, highest expected ROI
2. **Add ¥79 Studio tier** to roadmap — addressable market is studios, not just individuals
3. **Design and send WTP survey** to CLI users — 10 questions, 5 minutes, Van Westendorp
4. **Build waitlist for Studio tier** — validates demand before engineering investment
5. **Set up pricing analytics** — track conversion by tier, source, and cohort from day 1

---

## Appendix: Pricing Language

**For landing page**: "开始创作" not "购买" — position as starting a project, not subscribing.

**Annual framing**: "¥249/年 (节省 ¥99)" — show annual savings prominently.

**Studio positioning**: "专为剧本杀工作室打造" — not a feature list, a persona match.

**Free tier CTA**: "免费开始" — no credit card, no commitment.
