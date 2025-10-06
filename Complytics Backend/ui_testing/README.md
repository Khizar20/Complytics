# UI Testing: Accessibility + Security Scanner

This document explains how the UI testing subsystem works end‑to‑end: the scanners, data flow, AI recommendations, persistence, scheduling, API shape, and how the frontend consumes results. It is written for technical stakeholders preparing demos and architectural reviews.

## High‑level overview

- Purpose: Continuously assess a website’s Accessibility (WCAG) and Security posture, produce structured findings, and generate AI‑assisted remediation guidance.
- Components:
  - Backend: FastAPI service under `Complytics Backend/routes/ui_testing.py`
  - Scanners: `Complytics Backend/ui_testing/scanners/{wcag.py, security.py, interaction.py}`
  - AI: `Complytics Backend/ui_testing/ai/recommendations.py`
  - Frontend: React dashboard (`src/components/team/UserDashboard.jsx`) shows summaries under “UI Testing Summary” and uses `GET /api/ui/latest`.

## Data flow

1) A scan request is made (e.g., `POST /api/ui/scan`).
2) The backend runs scanners in parallel depending on mode (`all`, `accessibility`, `security`):
   - WCAG (axe‑core via headless Chrome/Selenium)
   - Security (SecurityHeaders + SSL Labs + Live HTTP headers)
   - DOM snapshot and minimal interaction log (keyboard/tabbing + form typing)
3) Results are normalized and passed to the AI layer to generate human‑readable recommendations.
4) Final result is returned and persisted to the database for the current organization.
5) The dashboard fetches the latest result (`GET /api/ui/latest`) and renders KPIs and charts; export buttons build PDF/Word reports.

## Endpoints (FastAPI)

- `POST /api/ui/scan` — Run a scan for a URL
  - Request: `{ "url": "https://example.com", "mode": "all|accessibility|security", "force": false }`
  - Response: `{ wcag_results, security_results, findings, recommendations }`

- `POST /api/ui/scan-now` — Re‑use last URL for the org, run a full scan now.
- `GET  /api/ui/latest` — Get the most recent result for the org (used by the dashboard).
- `POST /api/ui/schedule` — Schedule a future scan (APScheduler).
- `GET  /api/ui/schedules` — List scheduled scans.
- `DELETE /api/ui/schedules/{id}` — Cancel a scheduled scan.
- `POST /api/ui/export/pdf|excel` — Server‑side exports (simple) in addition to client‑side PDF/Word in the dashboard.

All endpoints require authentication (org scoping is enforced in handlers).

## Scanners

### Accessibility (WCAG) — `ui_testing/scanners/wcag.py`

- Tech stack: Selenium + headless Chrome, axe‑core via `axe_selenium_python`.
- Steps:
  1. Launch headless Chrome with a stable config (eager page load, window size, no‑sandbox).
  2. Navigate to the target URL.
  3. Inject axe‑core and run the audit.
  4. Return simplified `violations` with: `id`, `impact` (critical/serious/moderate/minor), `description`, `helpUrl`, and `nodes` (targets, html, failureSummary).
- Extra: `get_dom_snapshot(url)` collects a full DOM snapshot for AI context.

### Security — `ui_testing/scanners/security.py`

Combines three sources to form a practical, developer‑friendly view:

1. SecurityHeaders (`securityheaders.com`)
   - Returns a grade/score and lists of present/missing headers. Handles non‑JSON responses (rate limits/HTML) gracefully, returning a shaped error.

2. SSL Labs (`api.ssllabs.com`)
   - Polls the analysis until `READY` (or times out). Simplifies the response to endpoint grades, supported protocols, and certificate highlights.

3. Live HTTP headers
   - HEAD with GET fallback; summarizes key headers (CSP, HSTS, X‑Content‑Type‑Options, Referrer‑Policy, Permissions‑Policy, COEP/COOP/CORP). Adds simple boolean signals.

If SecurityHeaders fails, the backend derives a minimal “missing” list from live headers so the result remains actionable.

### Interaction (lightweight) — `ui_testing/scanners/interaction.py`

- Captures a minimal interaction log to help reason about forms and navigation:
  - Keyboard navigation (TAB focus traversal snapshot)
  - Sample typing in common input fields (email, tel, search, etc.) and submit attempts (best‑effort, capped)

This is safe and non‑destructive; it’s used only as hints for recommendations.

## AI recommendations — `ui_testing/ai/recommendations.py`

### Are we using AI agents?

Short answer: Not as autonomous multi‑agent workflows. The current implementation uses a single LLM call (Gemini) with a carefully structured prompt to emulate “roles” (Accessibility vs Security) and produce a merged action plan. This is intentional for reliability, latency, and cost.

You may see legacy docs referring to an agent graph (Security, Accessibility, Navigation, Reviewer). That design is not active in this codebase. Instead, we approximate the same outcome by:

- Generating normalized/structured findings first (`generate_structured_findings`) so the LLM receives concise, standardized inputs.
- Supplying optional context (`dom_snapshot`, `interaction_log`).
- Prompting Gemini once, grouped by mode (`accessibility`, `security`, or `all`).

This “single‑shot with structured roles” approach yields consistent guidance without orchestration overhead.

### How the AI step works (current)

- Provider: Google Gemini (via `google.generativeai`) with conservative sampling (temperature 0.3).
- Input bundle: `{ wcag_results, security_results, _extras: { dom_snapshot, interaction_log }, _mode }`.
- Pre‑processing:
  - Accessibility: violations are summarized (rule id, impact, short description, example targets) to avoid dumping raw DOM.
  - Security: SecurityHeaders + SSL Labs are distilled (missing headers list, SSL grade, notable notes).
- Prompting:
  - Tailored prompt by mode (accessibility/security/all).
  - Asks for severity + an explicit “How to fix” line for each item.
- Robustness:
  - Minimal call spacing and bounded retries.
  - On token/quota failures, rebuilds a more compact summary and retries.
  - Optional fallback to Groq (if `GROQ_API_KEY` is present). Otherwise returns a safe baseline checklist.
- Post‑processing: output text is cleaned to remove duplicated attributes and artifacts.

Additionally, `generate_structured_findings` produces a uniform, table‑friendly list of items:

```json
{ "title", "severity", "rule", "evidence", "fix" }
```

This structure powers the dashboard tables and the PDF/Word exports.

## Agentic mode: how the AI agents work

When `AGENTIC_MODE=1` is set, the backend switches to an agentic prompting strategy that emulates four roles in a single orchestrated prompt. This improves clarity and structure without introducing complex runtime orchestration.

### Roles
- **Accessibility Agent**: reads summarized axe‑core violations and proposes items with severity (Critical/Major/Minor) and a one‑line “How to fix”.
- **Security Agent**: reads SecurityHeaders, SSL Labs, and live header summaries to propose items with severity and fixes aligned to OWASP guidance (e.g., CSP, HSTS, X‑Content‑Type‑Options, Referrer‑Policy, Permissions‑Policy).
- **Navigation Agent**: reads the lightweight interaction log (TAB traversal, sample form input/submit) to flag forms/keyboard issues with concise fixes.
- **Reviewer Agent**: merges/deduplicates all items, adds a short executive summary, and emits the final action plan grouped by Accessibility vs Security.

### Inputs and summaries
- **WCAG summary**: compact list of violations with rule id, impact, brief description, and example targets (from `wcag.py`).
- **Security summary**: missing headers + SSL Labs grade (from `security.py`), with a short note.
- **Navigation summary**: small sample from the interaction log (from `interaction.py`).
- These summaries are constructed in `ui_testing/ai/agents.py` and fed into a single prompt.

### Prompt construction
- The backend builds a multi‑section prompt: [Accessibility Agent] → [Security Agent] → [Navigation Agent] → [Reviewer], with explicit instructions and a fixed final output format (executive summary, then grouped bullets with severity and How‑to‑fix).
- Provider defaults to Gemini. Temperature remains conservative for consistency.

### Execution and fallbacks
- The agentic prompt is sent to Gemini if `GOOGLE_API_KEY` is available.
- If Gemini is unavailable and `GROQ_API_KEY` is configured, the same prompt is sent to Groq as a fallback.
- If all providers fail, a minimal, deterministic baseline plan is returned so the UI never breaks.

### Output contract
- The final text is human‑readable and structured. Downstream, we also maintain `findings` (structured items) for table/exports, independent of the AI text.
- Severity labels map to the UI (Critical/Major/Minor). The executive summary is 2–4 bullets.

### Why a single orchestrated prompt?
- Lower latency, fewer API calls, reduced complexity vs true multi‑turn tool‑using agents.
- More predictable output and easier testing for demos/presentations.

### Limitations
- Still LLM‑generated text; not a formal compliance report.
- The Navigation Agent’s signals are lightweight (non‑destructive). For deeper coverage, expand interaction tooling and prompts.

### What would a true agentic mode look like?

If you want to enable multi‑agent orchestration (future work):

- Create an `ai/agents.py` that coordinates discrete agents:
  - Accessibility agent → from axe results + DOM snapshot
  - Security agent → from SecurityHeaders, SSL Labs, live headers
  - Navigation agent → from interaction log
  - Reviewer agent → merges/deduplicates + writes final plan
- Add a switch (e.g., `AGENTIC_MODE=1`) and branch in `recommendations.py` to call the agent graph.
- Keep the single‑shot path as fallback for resilience.

## Persistence and caching

- Results are cached in‑memory briefly (`SCAN_CACHE`) to avoid re‑running scanners during export.
- Results are persisted per organization in `ui_testing_results` with `{ organization_id, url, mode, results, created_at }` and surfaced via `GET /api/ui/latest`.

## Scheduling

- APScheduler runs in the backend process. Scheduled jobs re‑use the last scanned URL for the org and email a short HTML summary (optional email).

## Frontend integration

- The React dashboard calls `GET /api/ui/latest` and renders:
  - Accessibility Score (heuristic based on violation counts by impact)
  - WCAG violation counts and severity distribution
  - Security headers coverage and SSL Labs grades
  - Missing headers badges and compliance checklist
  - AI Recommendations (from the backend `recommendations` string)
- Report export buttons (PDF/Word) build a structured report (headings + tables) and append a visual snapshot.

## Environment variables

- `GOOGLE_API_KEY` — enables Gemini recommendations. If unset, a safe fallback message is returned.
- (Optional) `GROQ_API_KEY` — enables Groq fallback.
- `AGENTIC_MODE` — set to `1` to enable multi-role agentic prompting (Accessibility/Security/Navigation/Reviewer) via a single orchestrated prompt; otherwise a single-shot prompt per mode is used.

## API: response shape (simplified)

```json
{
  "wcag_results": {
    "violations": [
      {
        "id": "image-alt",
        "impact": "critical",
        "description": "Images must have alternate text.",
        "helpUrl": "https://dequeuniversity.com/rules/axe/4.7/image-alt",
        "nodes": [ { "target": ["img.hero"], "html": "<img ...>", "failureSummary": "..." } ]
      }
    ],
    "passes_count": 42,
    "inapplicable_count": 17
  },
  "security_results": {
    "securityheaders": { "grade": "A", "missing": ["Content-Security-Policy"], ... },
    "ssllabs": { "status": "READY", "endpoints": [ { "ipAddress": "...", "grade": "A-" } ] },
    "live_headers": { "headers": { "Content-Security-Policy": { "present": false, "value": null } }, "signals": { "csp_present": false } }
  },
  "findings": {
    "security": [ { "title": "Missing Content-Security-Policy header", "severity": "Critical", "rule": "OWASP ASVS 14.4.2", "evidence": "...", "fix": "Define a strict CSP." } ],
    "accessibility": [ { "title": "Images must have alternate text", "severity": "Major", "rule": "image-alt", "evidence": "img.hero", "fix": "Provide meaningful alt attributes." } ]
  },
  "recommendations": "... Human-friendly, grouped action plan ..."
}
```

## Key technical terms (glossary)

- axe‑core: Industry‑standard accessibility engine for automated WCAG checks.
- WCAG: Web Content Accessibility Guidelines (e.g., WCAG 2.1 AA). Impacts: critical/serious/moderate/minor from axe.
- CSP (Content‑Security‑Policy): HTTP header that restricts resource loading and mitigates XSS.
- HSTS (Strict‑Transport‑Security): Enforces HTTPS with max‑age and optional subdomains.
- X‑Content‑Type‑Options: `nosniff` helps prevent MIME‑sniffing attacks.
- Referrer‑Policy: Controls referrer header; `no-referrer` and `strict-origin-when-cross-origin` are common choices.
- Permissions‑Policy: Restricts powerful browser features (e.g., geolocation, camera).
- COEP/COOP/CORP: Cross‑origin isolation headers improving security for advanced APIs.
- SSL Labs: External TLS analyzer that grades endpoint TLS configuration and certificates.

## Running locally (scanner excerpt)

Python 3.10+, Google Chrome installed.

```bash
uvicorn app:app --reload  # from Complytics Backend/ (actual entry point is managed by the main backend)
```

Then hit the endpoints above (remember auth). The frontend dashboard will automatically surface the latest results.

## Limitations and roadmap

- axe‑core is a powerful automated checker but cannot replace manual audits (e.g., content meaning, UX context).
- SSL Labs analysis may take minutes on first run; results are cached briefly.
- Recommendations favor concise actions over exhaustive reports; future iterations can include sectioned remediation playbooks, diffs across scans, and richer interaction flows.

## Security and privacy

- Only the target URL and scan results are processed. External calls are made to SecurityHeaders and SSL Labs for the host under test.
- Provide your own Gemini key; it is never stored in code.


