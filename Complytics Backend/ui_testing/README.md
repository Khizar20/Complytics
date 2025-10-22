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

### Single-Page Scanning
- `POST /api/ui/scan` — Run a scan for a URL
  - Request: `{ "url": "https://example.com", "mode": "all|accessibility|security", "force": false }`
  - Response: `{ wcag_results, security_results, findings, recommendations }`

- `POST /api/ui/scan-now` — Re‑use last URL for the org, run a full scan now.
- `GET  /api/ui/latest` — Get the most recent result for the org (used by the dashboard).
- `POST /api/ui/schedule` — Schedule a future scan (APScheduler).
- `GET  /api/ui/schedules` — List scheduled scans.
- `DELETE /api/ui/schedules/{id}` — Cancel a scheduled scan.
- `POST /api/ui/export/pdf|excel` — Server‑side exports (simple) in addition to client‑side PDF/Word in the dashboard.

### Whole-Site Scanning (NEW)
- `POST /api/ui/scan-site` — Scan entire website by crawling and testing multiple pages
  - Request: `{ "url": "https://example.com", "max_pages": 50, "max_depth": 3, "scan_mode": "all", "parallel_scans": 3, "use_selenium_crawler": false }`
  - Response: `{ summary, crawl_result, page_results, wcag_aggregate, security_aggregate, duration_seconds }`
  - Features:
    - Discovers pages via sitemap.xml parsing
    - Crawls HTML pages to find links (BFS algorithm)
    - Respects robots.txt
    - Filters non-page resources (images, PDFs, etc.)
    - Scans multiple pages in parallel
    - Aggregates results for site-wide analysis

- `POST /api/ui/crawl-only` — Crawl a website to discover pages without running scans (preview mode)
  - Request: `{ "url": "https://example.com", "max_pages": 50, "max_depth": 3, "use_selenium": false }`
  - Response: `{ urls: [...], stats: {...}, errors: [...] }`

- `GET /api/ui/site/latest` — Get the most recent whole-site scan result for the org
- `GET /api/ui/site/history` — Get history of whole-site scans (limit: 10 by default)

All endpoints require authentication (org scoping is enforced in handlers).

## Whole-Site Scanning Architecture (NEW)

### Overview
The whole-site scanning feature extends the single-page scanner to provide comprehensive website-wide accessibility and security analysis. It automatically discovers pages, tests them in parallel, and aggregates results.

### Components

#### 1. Website Crawler (`ui_testing/scanners/crawler.py`)
Intelligent web crawler that discovers pages for testing:

**Features:**
- **Sitemap.xml Parsing**: Automatically fetches and parses sitemap.xml (including sitemap indexes) for comprehensive page discovery
- **HTML Link Extraction**: Crawls pages using BeautifulSoup to find additional links
- **Robots.txt Respect**: Fetches robots.txt and respects disallowed paths
- **Smart Filtering**: 
  - Removes non-HTML resources (images, PDFs, JS, CSS, etc.)
  - Filters out API endpoints, download links, logout links
  - Deduplicates URLs
  - Normalizes URLs (removes fragments, tracking parameters)
- **Domain Scoping**: Optionally restricts crawling to same domain
- **Depth Control**: Limits crawl depth (BFS algorithm)
- **Selenium Support**: Optional Selenium-based crawling for JavaScript-heavy sites
- **Rate Limiting**: Built-in delays to avoid overwhelming servers

**Usage:**
```python
from ui_testing.scanners.crawler import crawl_website

result = await crawl_website(
    url="https://example.com",
    max_pages=50,
    max_depth=3,
    use_selenium=False
)
# Returns: { urls: [...], stats: {...}, errors: [...] }
```

#### 2. Site Scanner (`ui_testing/scanners/site_scanner.py`)
Orchestrates multi-page testing and result aggregation:

**Features:**
- **Parallel Scanning**: Scans multiple pages concurrently (configurable batch size)
- **Per-Page Testing**: Runs WCAG, Security, and Interaction tests on each page
- **Aggregation Logic**:
  - **WCAG Aggregation**: 
    - Groups violations by rule ID across all pages
    - Tracks which pages are affected by each issue
    - Counts instances per violation type
    - Calculates impact distribution (critical/serious/moderate/minor)
    - Identifies top 10 most widespread issues
  - **Security Aggregation**:
    - Recognizes that security headers are typically domain-level
    - Takes primary security scan and notes any variations
    - Provides SSL Labs grade and security headers analysis
- **Site-Wide Scoring**: Calculates accessibility score (0-100) based on violation severity and frequency
- **Executive Summary**: Generates high-level stats and metrics

**Usage:**
```python
from ui_testing.scanners.site_scanner import scan_whole_site

result = await scan_whole_site(
    url="https://example.com",
    max_pages=50,
    max_depth=3,
    scan_mode="all",  # or "accessibility", "security"
    parallel_scans=3,
    use_selenium_crawler=False
)
```

**Result Structure:**
```json
{
  "summary": {
    "site_url": "https://example.com",
    "pages_discovered": 45,
    "pages_scanned": 45,
    "accessibility_score": 72.5,
    "accessibility_summary": {
      "total_violations": 127,
      "unique_issues": 8,
      "pages_with_issues": 32,
      "critical_issues": 3,
      "serious_issues": 12
    },
    "security_summary": {
      "securityheaders_grade": "A",
      "ssl_grade": "A+"
    }
  },
  "crawl_result": {
    "urls": ["..."],
    "stats": {
      "total_discovered": 45,
      "from_sitemap": 38,
      "from_crawl": 7,
      "duration_seconds": 12.4
    }
  },
  "page_results": [
    {
      "url": "https://example.com/page1",
      "wcag_results": {...},
      "security_results": {...},
      "errors": []
    }
  ],
  "wcag_aggregate": {
    "total_pages_scanned": 45,
    "pages_with_issues": 32,
    "total_violations": 127,
    "unique_rules_violated": 8,
    "impact_counts": {
      "critical": 15,
      "serious": 45,
      "moderate": 50,
      "minor": 17
    },
    "violations_summary": [
      {
        "id": "image-alt",
        "description": "Images must have alternate text",
        "impact": "critical",
        "pages_affected": 25,
        "pages_affected_urls": ["url1", "url2", ...],
        "total_instances": 38
      }
    ],
    "top_issues": [...]
  },
  "security_aggregate": {
    "primary_scan": {...},
    "variations_detected": 0
  }
}
```

### Performance Characteristics

- **Crawling**: 0.5s delay per page (respects servers)
- **Scanning**: Parallel batches (default: 3 concurrent scans)
- **Typical Duration**: 
  - 10 pages: ~2-4 minutes
  - 50 pages: ~8-15 minutes (depending on page complexity)
- **Resource Usage**: Headless Chrome instances are created/destroyed per page scan

### Use Cases

1. **Comprehensive Audits**: Scan entire website before launch or major updates
2. **Regression Testing**: Regular full-site scans to catch new accessibility/security issues
3. **Compliance Reporting**: Generate site-wide compliance reports for stakeholders
4. **Issue Prioritization**: Identify which accessibility issues affect the most pages
5. **Security Posture**: Assess domain-level security headers and SSL configuration

### Limitations

- **Scale**: Designed for sites up to ~100 pages (configurable max_pages limit)
- **Auth**: Currently cannot scan pages behind authentication
- **JavaScript**: Standard crawler uses requests (fast); opt-in Selenium for JS-heavy sites (slower)
- **API Rate Limits**: External services (SSL Labs, SecurityHeaders) may rate-limit
- **Completeness**: Automated testing cannot catch all accessibility issues (manual testing still needed)

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


