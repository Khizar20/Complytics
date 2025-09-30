## Web Accessibility & Security Scanner

FastAPI backend + Streamlit frontend that scans a website for:
- Accessibility (WCAG) via axe-core in headless Chrome (Selenium)
- Security headers via SecurityHeaders
- TLS/HTTPS configuration via SSL Labs
- Optional AI-written remediation recommendations via Google Gemini

### High-level architecture
- Backend (`backend/`): FastAPI service exposing `POST /scan`.
  - `scanners/wcag.py`: launches headless Chrome, runs axe-core, returns simplified violations.
  - `scanners/security.py`: calls SecurityHeaders and polls SSL Labs; normalizes results.
  - `ai/recommendations.py`: optionally calls Gemini to turn findings into concise actions.
- Frontend (`frontend/`): Streamlit app that calls the backend and visualizes results.

### Data flow
1. User enters a URL in the Streamlit UI and clicks Run Scan.
2. Frontend sends `POST` to backend `/scan` with `{ "url": "..." }`.
3. Backend runs two scans concurrently:
   - WCAG (axe-core via Selenium/Chrome)
   - Security (SecurityHeaders + SSL Labs)
4. When both finish, backend optionally calls Gemini once to generate recommendations.
5. Backend returns a JSON `ScanResponse` with `wcag_results`, `security_results`, `recommendations`.
6. Frontend shows KPIs, tables/charts, raw security summaries, and the AI recommendations.

### Are AI agents used?
**No.** This project does not use autonomous multi-agent systems. It makes a single, stateless call to a large language model (Gemini) to convert scan outputs into human-friendly recommendations. If the API key is not set or the call fails, the backend returns a fallback message.

### Prerequisites
- Python 3.10+ (3.11 recommended)
- Google Chrome installed
- (Optional) Google API key for Gemini set as `GOOGLE_API_KEY`

### Backend setup (Windows PowerShell)
```powershell
cd "C:\UI Testing"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
# Optional for AI recommendations
$env:GOOGLE_API_KEY = "YOUR_API_KEY"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend setup (Windows PowerShell)
```powershell
cd "C:\UI Testing"
# Reuse same venv or create another
.\.venv\Scripts\Activate.ps1
pip install -r frontend/requirements.txt
# Optional; defaults to http://localhost:8000/scan
$env:API_URL = "http://localhost:8000/scan"
streamlit run frontend/app.py --server.port 8501
```

### Usage
1. Start the backend (port 8000)
2. Start the frontend (port 8501)
3. In the Streamlit UI, enter a website URL and click Run Scan
4. Review:
   - Accessibility violations and impact chart
   - Security headers and SSL Labs summaries
   - AI recommendations (if `GOOGLE_API_KEY` configured)

### API
- `POST /scan`
  - Request JSON: `{ "url": "https://example.com" }`
  - Response JSON: `{ wcag_results, security_results, recommendations }`

### How each scan works
- WCAG: Uses Selenium to load the page in headless Chrome, injects axe-core, and returns simplified `violations` (rule id, impact, description, help URL, and nodes/targets).
- SecurityHeaders: Queries `securityheaders.com` JSON for grade/score and missing/present headers.
- SSL Labs: Polls SSL Labs API, returning final summary (status, per-endpoint grades, protocols, and certificate basics).
- AI recommendations: If `GOOGLE_API_KEY` is set, the backend calls Gemini once with both scan results and returns bullet-point guidance grouped by Accessibility vs Security.

### Troubleshooting
- Chrome/driver issues: Ensure Google Chrome is installed and accessible. Selenium Manager auto-resolves ChromeDriver.
- Rate limits: SecurityHeaders and SSL Labs may rate-limit (HTTP 429). Retry later.
- Long SSL Labs runs: First-time analyses can take 1–3 minutes.
- No AI output: Check `GOOGLE_API_KEY` and outbound network connectivity. The backend logs will indicate if Gemini was configured and whether generation failed.

### Security & Privacy
- Only the target host and scan results are processed. SecurityHeaders/SSL Labs involve external API calls to those services about the target host.
- Provide your own Gemini API key; do not hardcode secrets in code or files.

### Example commands
```powershell
# Backend
uvicorn backend.main:app --reload

# Frontend
streamlit run frontend/app.py
```
