# Quorum — Business Case

*Source for the pitch-deck market/revenue/competition slides. Market figures are cited; pricing and capture assumptions are labelled as illustrative.*

---

## 1. The problem, quantified

Every asset manager, hedge fund, RIA, and family office runs the same loop to make and document an investment decision: analysts compile data, a bull and a bear argue, risk & compliance weighs in, a PM decides, and **someone writes the audit trail by hand**.

It is expensive on two axes:

- **Labour.** A single committee-grade decision takes ~2–4 analyst-days of prep plus a meeting of several people earning six figures fully loaded. Multiply by the dozens–hundreds of names a desk reviews per year.
- **Compliance documentation.** The decision rationale and its provenance must be written up and retained — manual, repetitive, and audited.

The pain is **slow, inconsistent (anchoring, politics, who's in the room), and costly to document** — and the documentation is not optional (see §2).

## 2. Why now — regulation creates the market for decision provenance

- **EU AI Act** — high-risk AI systems carry record-keeping and traceability obligations; financial decision-support is squarely in scope.
- **SEC / FINRA recordkeeping** (e.g. SEC Rule 17a-4, FINRA 4511) — firms must retain the books and records behind decisions.

The audit trail Quorum produces automatically — a full, replayable, independently-attested decision record — is a **legally required artifact**. Regulation is converting "nice-to-have decision hygiene" into a **mandatory, budgeted line item**, and that is the wedge.

## 3. Market sizing

> Cited figures use the **most conservative** credible estimate where sources disagree; ranges are noted.

**TAM — the software market Quorum sells into.**
The **investment-management software** market is **~$4.9B in 2025, growing ~11–12% CAGR to ~$8.5B by 2030** ([Research and Markets, 2025](https://www.researchandmarkets.com/reports/6090217/investment-management-software-market-global)); higher-end estimates run to ~$23–26B by 2035 ([Market Research Future](https://www.marketresearchfuture.com/reports/investment-management-software-market-22935)). Two adjacent markets expand the long-term TAM and map directly to Quorum's two value props:
- **AI in asset management** — ~$3.8B in 2025, ~24% CAGR to 2034 ([Precedence Research](https://www.precedenceresearch.com/ai-in-asset-management-market)) → the *decision-quality* expansion.
- **RegTech** — ~$16–19B in 2025, ~20% CAGR toward $100B+ by the mid-2030s ([RegTech Industry Report, 2025](https://www.globenewswire.com/news-release/2025/11/18/3189777/0/en/RegTech-Industry-Research-Report-2025-2035-115-5-Bn-Market-Accelerates-as-Financial-Sector-Digital-Transformation-and-Rising-Regulatory-Demands-Drive-Adoption-of-AI-Enabled-Complia.html)) → the *compliance-tier* expansion.

**SAM — buy-side firms that run formal committees.**
The U.S. SEC-registered investment-adviser industry set a record **16,544 firms in 2025**, managing **$176.8T in assets** and serving 73.7M clients ([IAA / COMPLY 2026 Industry Snapshot](https://www.investmentadviser.org/industry-snapshots/); [WealthManagement.com](https://www.wealthmanagement.com/ria-news/ria-industry-hits-record-number-of-firms-client-aum)). Add hedge funds, pensions, endowments, and family offices and the serviceable base is **tens of thousands of firms** that each run a recurring decision-and-documentation process.

**SOM — a 3-year beachhead.**
*Wedge:* mid-size RIAs and boutique asset managers that run a committee process but **cannot afford a full in-house research desk** — they feel the labour pain most and have the lightest procurement friction.
*Illustrative bottom-up (assumptions, not cited):* capturing **~1% of the 16,544 RIAs ≈ 165 firms** at a **~$30k blended ACV** (a few seats + usage + the compliance tier) ≈ **~$5M ARR** — a modest, credible early target that does not require displacing Bloomberg/FactSet.

## 4. Revenue model

A three-layer model that scales from boutiques to enterprises:

| Layer | What | Why it's durable |
|---|---|---|
| **Seat SaaS** | Per analyst / PM / month | Lands with the team that runs the committee |
| **Usage** | Per committee / per decision | Mirrors the real cost architecture (frontier models for judgment, open models for bulk) and scales with value delivered |
| **Compliance tier** | The independent audit trail + attestation as a retained, premium feature | Highest willingness-to-pay, stickiest — it maps to a *regulatory obligation*, not a preference |

## 5. Competitive landscape & USP

| Player | What they provide | What they don't |
|---|---|---|
| **Bloomberg Terminal / FactSet** | Data, analytics, search | No governed multi-agent decision or debate; no automatic, attested audit trail |
| **AlphaSense** | AI search over filings & transcripts | Surfaces information; doesn't *run a governed committee* or emit an attested decision record |
| **TradingAgents** (open-source) | Multi-agent bull/bear debate | A research demo — no enforced compliance gate, no independent audit, no human governance, not built for regulated workflows |
| **Internal manual committee** | Human judgment | Slow, inconsistent, hand-written audit trail |
| **Quorum** | A self-assembling, governed committee on Band that debates, recruits specialists, gates on compliance, escalates, and **emits an independently-attested, replayable decision record** | — |

**USP:** Quorum is **not** a data terminal and **not** just a debate. It is the **governance + auditability layer** that sits on top of the data firms already buy — the layer regulation now requires. You keep your terminal; Quorum makes the *decision* fast, consistent, and provable.

## 6. Value math (ROI)

| | Manual committee | Quorum |
|---|---|---|
| Prep + debate cycle | 2–4 analyst-days per name | minutes |
| Consistency | anchoring-prone, varies by room | adversarial debate + enforced gate |
| Audit trail | written by hand | auto-generated + independently attested |
| Reproduce a past decision | difficult | full Band trail, replayable |

*Illustrative:* at ~3 analyst-days of fully-loaded cost per decision, automating the prep-and-documentation loop saves on the order of **single-digit $thousands per decision** in labour alone — before counting the avoided compliance-documentation overhead and the risk-reduction value of a consistent, attested process.

---

### Sources
- Investment-management software market — [Research and Markets (2025)](https://www.researchandmarkets.com/reports/6090217/investment-management-software-market-global); [Market Research Future](https://www.marketresearchfuture.com/reports/investment-management-software-market-22935)
- AI in asset management — [Precedence Research](https://www.precedenceresearch.com/ai-in-asset-management-market)
- RegTech — [RegTech Industry Research Report 2025–2035 (GlobeNewswire)](https://www.globenewswire.com/news-release/2025/11/18/3189777/0/en/RegTech-Industry-Research-Report-2025-2035-115-5-Bn-Market-Accelerates-as-Financial-Sector-Digital-Transformation-and-Rising-Regulatory-Demands-Drive-Adoption-of-AI-Enabled-Complia.html)
- RIA industry size — [IAA / COMPLY 2026 Investment Adviser Industry Snapshot](https://www.investmentadviser.org/industry-snapshots/); [WealthManagement.com](https://www.wealthmanagement.com/ria-news/ria-industry-hits-record-number-of-firms-client-aum); [InvestmentNews](https://www.investmentnews.com/ria-news/industry-snapshot-more-advisors-more-clients-1446t-aum/260706)

*Market-size estimates vary by research firm and methodology; figures here use conservative anchors and cite the range. Pricing, ACV, and capture-rate figures are illustrative business assumptions, not third-party data.*
