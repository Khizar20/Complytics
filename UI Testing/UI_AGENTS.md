## UI Agents: Architecture and Operation

This document explains how the project’s AI agents work end-to-end, how scans are performed, how the accessibility score is computed, and how security posture is evaluated. It complements the root `README.md` with deeper agent details.

### Components at a glance
- Backend (`backend/`): FastAPI service that executes scanners and invokes AI agents.
  - `backend/main.py`: Orchestrates scans, auth, alerts, and exports.
  - `backend/scanners/wcag.py`: Headless Chrome + axe-core accessibility scan and DOM snapshots.
  - `backend/scanners/security.py`: SecurityHeaders API, SSL Labs API, and live HTTP header fetch.
  - `backend/scanners/interaction.py`: Basic interactive UI testing (keyboard navigation + form inputs).
  - `backend/ai/recommendations.py`: Entry point that routes to the agentic pipeline when `AGENTIC_MODE=1`.
  - `backend/ai/agents.py`: Agent graph (Security, Accessibility, Navigation, Reviewer).
- Frontend (`frontend/app.py`): Streamlit UI that calls the backend, shows results, and offers PDF/Excel exports.

### Data flow
1. User submits a URL in the Streamlit UI (`frontend/app.py`).
2. UI calls `POST /scan` with `X-API-Key` to the backend (`backend/main.py`).
3. Backend runs, in parallel:
   - Accessibility scan via axe-core (`run_wcag_scan` in `wcag.py`).
   - Security scans: SecurityHeaders + SSL Labs + live HTTP header fetch (`security.py`).
   - DOM snapshot via Selenium (`get_dom_snapshot` in `wcag.py`).
   - Interactive test (keyboard tabs and sample form input) (`interaction.py`).
4. Backend normalizes results and, if `AGENTIC_MODE=1`, calls the agentic pipeline (`ai/agents.py`) to produce an action plan. Otherwise a single-shot Gemini prompt is used.
5. Backend returns `wcag_results`, `security_results`, `recommendations` to the UI.
6. UI displays KPIs, tables/charts, and AI recommendations. PDF/Excel export call the export endpoints.

### AI agents: roles and graph
The agentic pipeline is implemented with a simple state graph in `backend/ai/agents.py`:
- Security agent (OWASP-focused):
  - Inputs: DOM snapshot, SecurityHeaders/SSL Labs summaries, live HTTP headers.
  - Output: JSON-like list of risks (title, severity, rule, evidence, fix) mapped to OWASP guidance.
- Accessibility agent (WCAG-focused):
  - Inputs: axe-core findings and DOM snapshot.
  - Output: JSON-like list of accessibility issues with severities and remediations.
- Navigation agent (Interactive testing):
  - Inputs: Interaction log (keyboard tab steps, form input/submit attempts).
  - Output: JSON-like issues related to forms/navigation compliance.
- Reviewer agent:
  - Inputs: Security + Accessibility + Navigation findings.
  - Output: Final, merged, de-duplicated action plan in Markdown plus a concise JSON summary.

Agent routing
- Controlled by `AGENTIC_MODE` environment variable.
- When `AGENTIC_MODE=1`, `backend/ai/recommendations.py` uses `run_agentic(...)` to invoke the graph.
- On failure or if disabled, it falls back to a single LLM call with a structured prompt.

Model
- Google Gemini (via `google-generativeai` and `langchain-google-genai`).
- Temperature kept low to prioritize consistency and precision.

### Accessibility checks
Primary scanner
- `axe-core` via Selenium (`backend/scanners/wcag.py`). The page is opened in headless Chrome, axe is injected, and results are simplified into violations containing: rule id, impact (critical/serious/moderate/minor), description, help URL, and affected node targets.

Heuristic enrichment (agents)
- The Accessibility agent augments axe-core by reasoning about:
  - Image alternatives (quality/appropriateness).
  - ARIA usage and landmark coverage.
  - Keyboard navigation/focus patterns (with help from interaction logs).
  - Color contrast cues at a high level.

Accessibility score (UI KPI)
- Computed in `frontend/app.py`:
  - Weights: minor=1, moderate=2, serious=3, critical=4.
  - Score = max(0, 100 − 2 × sum(weights for all violations)).
  - This is a heuristic index used for quick progress tracking, not a formal WCAG conformance metric.

### Security checks
Multi-source security posture is built from:
1) SecurityHeaders summary (`securityheaders.com`)
   - Returns grade/score and lists of present/missing headers. The service may rate-limit or serve HTML; the backend now detects non-JSON responses and surfaces a clear message instead of failing.
2) SSL Labs summary (`api.ssllabs.com`)
   - Status, endpoint grades, supported protocols, and certificate basics. First run on a host may take a minute or more.
3) Live HTTP headers (HEAD → GET fallback)
   - Fetched directly from the target URL. The backend summarizes key headers and signals:
     - Content-Security-Policy
     - Strict-Transport-Security
     - X-Content-Type-Options
     - Referrer-Policy
     - Permissions-Policy
     - Cross-Origin-Embedder-Policy
     - Cross-Origin-Opener-Policy
     - Cross-Origin-Resource-Policy

Security agent
- Consumes all three sources (plus DOM snapshot) and produces OWASP-oriented findings with severities and recommended fixes.

### Interactive testing
- `backend/scanners/interaction.py` executes a minimal set of safe interactions:
  - Keyboard tabbing (focus traversal snapshot).
  - Sample form typing and submit attempt (non-destructive, best-effort).
- The interaction log helps agents reason about accessibility and security issues tied to forms and navigation (e.g., missing labels, tabindex problems, keyboard traps).

### Auth, alerts, and exports
- Authorization: `POST /scan` and export endpoints require `X-API-Key` (set `API_KEY`).
- Alerts: When a Critical item is detected in the recommendations, the backend logs a critical alert and can optionally post to Slack via `SLACK_WEBHOOK_URL`.
- Exports:
  - `POST /export/pdf`: simple PDF rendering of the recommendations for sharing.
  - `POST /export/excel`: Excel workbook with WCAG and Security sheets. Falls back between `xlsxwriter` and `openpyxl` engines.

### API and response shape
`POST /scan` request
```json
{ "url": "https://example.com" }
```

`POST /scan` response (simplified)
```json
{
  "wcag_results": {
    "violations": [ { "id": "image-alt", "impact": "critical", "helpUrl": "...", "nodes": [ { "target": ["img.hero" ] } ] } ],
    "passes_count": 42,
    "inapplicable_count": 17
  },
  "security_results": {
    "securityheaders": { "grade": "A", "missing": ["Content-Security-Policy"], ... } | { "error": "non-JSON response", ... },
    "ssllabs": { "status": "READY", "endpoints": [ { "ipAddress": "...", "grade": "A-" } ], ... },
    "live_headers": { "headers": { "Content-Security-Policy": { "present": true, "value": "..." } }, "signals": { "csp_present": true, "hsts_present": true } }
  },
  "recommendations": "... Markdown action plan with Security vs Accessibility sections ..."
}
```

### Environment variables
- `GOOGLE_API_KEY`: Gemini API key.
- `AGENTIC_MODE`: set `"1"` to enable the agent graph; any other value uses single-shot prompt.
- `API_KEY`: required for backend authorization; also set in the frontend environment so it can send the header.
- `SLACK_WEBHOOK_URL` (optional): for critical alerts.
- `API_URL` (frontend optional): defaults to `http://localhost:8000/scan`.

### Running locally (Windows PowerShell)
Backend
```powershell
cd "C:\\UI Testing"
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r backend/requirements.txt
$env:GOOGLE_API_KEY = "<your-google-gemini-api-key>"
$env:AGENTIC_MODE   = "1"
$env:API_KEY        = "<a-strong-random-secret>"
# Optional Slack webhook
# $env:SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/XXX/YYY/ZZZ"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend
```powershell
cd "C:\\UI Testing"
.\\.venv\\Scripts\\Activate.ps1
pip install -r frontend/requirements.txt
$env:API_URL = "http://localhost:8000/scan"
$env:API_KEY = "<a-strong-random-secret>"
streamlit run frontend/app.py --server.port 8501
```

### Interpreting results
- Accessibility score: a directional score useful for trending; prioritize Critical/Serious items listed.
- Security posture: consider SSL Labs (TLS) + live headers (CSP/HSTS/etc.). SecurityHeaders may rate-limit; the app reports this clearly and still provides live headers.
- AI recommendations: a merged action plan with severity and fixes across Security, Accessibility, and Interactive testing. Use it to drive remediation tasks.

### Extending the agents
- Add tools for deeper analysis (e.g., color contrast sampling, keyboard trap detection via script injection).
- Expand Navigation agent with constrained actions (route coverage, login flows using test creds).
- Cache third-party results (SecurityHeaders/SSL Labs) to reduce rate limits.
- Persist scan histories and diff results across runs.


