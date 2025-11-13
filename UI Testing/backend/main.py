import asyncio
import os
import logging
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Depends, Header, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from .scanners.wcag import run_wcag_scan, get_dom_snapshot
from .scanners.security import run_security_scan
from .scanners.interaction import run_interactive_test, run_interactive_test_with_auth
from .scanners.authenticated_site_scanner import AuthenticatedSiteScanOrchestrator
from .ai.recommendations import (
    configure_gemini,
    generate_findings_and_recommendations,
)


class ScanMode(str, Enum):
    all = "all"
    accessibility = "accessibility"
    security = "security"


class ScanRequest(BaseModel):
    url: str
    mode: ScanMode = ScanMode.all


class AuthenticatedScanRequest(BaseModel):
    url: str
    mode: ScanMode = ScanMode.all
    credentials: Dict[str, str]
    max_pages: int = 50
    max_depth: int = 3
    parallel_scans: int = 3


class AuthenticationTestRequest(BaseModel):
    url: str
    credentials: Dict[str, str]


class ScanResponse(BaseModel):
    wcag_results: Dict[str, Any]
    security_results: Dict[str, Any]
    findings: Dict[str, Any]
    recommendations: str


class AuthenticatedScanResponse(BaseModel):
    wcag_results: Dict[str, Any]
    security_results: Dict[str, Any]
    findings: Dict[str, Any]
    recommendations: str
    authentication_required: bool
    authentication_successful: bool
    session_used: bool


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("web-compliance-scanner")

app = FastAPI(title="Web Compliance Scanner", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _normalize_url(input_url: str) -> str:
    if not input_url:
        return input_url
    if input_url.startswith("http://") or input_url.startswith("https://"):
        return input_url
    # Default to https for security
    return f"https://{input_url}"


def require_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    expected = os.getenv("API_KEY")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


async def emit_critical_alert(message: str) -> None:
    logger.warning("CRITICAL ALERT: %s", message)
    try:
        webhook = os.getenv("SLACK_WEBHOOK_URL")
        if webhook:
            import requests
            requests.post(webhook, json={"text": message}, timeout=10)
    except Exception:
        logger.exception("Failed to send Slack alert")


@app.on_event("startup")
async def on_startup() -> None:
    # Configure Gemini once (no-op if key missing)
    primary_key = os.getenv("GOOGLE_API_KEY1")
    fallback_key = os.getenv("GOOGLE_API_KEY2")
    configure_gemini(primary_key, fallback_key)
    logger.info(
        "Application startup complete. Gemini configured=%s",
        bool(primary_key or fallback_key),
    )


@app.post("/scan", response_model=ScanResponse, dependencies=[Depends(require_api_key)])
async def scan(payload: ScanRequest) -> ScanResponse:
    url = _normalize_url(payload.url.strip())
    if not url:
        logger.warning("/scan called without URL")
        raise HTTPException(status_code=400, detail="URL is required")

    mode = payload.mode or ScanMode.all
    logger.info("Starting scan for url=%s | mode=%s", url, mode.value)

    # Run tasks conditionally based on mode
    wcag_task = None
    security_task = None
    dom_task = None
    interaction_task = None
    if mode in (ScanMode.all, ScanMode.accessibility):
        wcag_task = asyncio.create_task(run_wcag_scan(url))
        dom_task = asyncio.to_thread(get_dom_snapshot, url)
        interaction_task = asyncio.to_thread(run_interactive_test, url)
    if mode in (ScanMode.all, ScanMode.security):
        security_task = asyncio.create_task(run_security_scan(url))

    async def _gather_or_none(task):
        return await task if task is not None else None

    wcag_results, security_results, dom_html, interaction_log = await asyncio.gather(
        _gather_or_none(wcag_task),
        _gather_or_none(security_task),
        _gather_or_none(dom_task),
        _gather_or_none(interaction_task),
        return_exceptions=True,
    )

    # Normalize potential exceptions into error objects
    def ensure_dict(result: Any, label: str) -> Dict[str, Any]:
        if isinstance(result, Exception):
            logger.exception("%s raised an exception", label)
            return {"error": f"{label} failed: {str(result)}"}
        if isinstance(result, dict):
            return result
        logger.error("%s returned unexpected type: %s", label, type(result))
        return {"error": f"Unexpected {label} result type"}

    wcag_results_dict = ensure_dict(wcag_results, "WCAG scan") if wcag_results is not None else {}
    security_results_dict = ensure_dict(security_results, "Security scan") if security_results is not None else {}
    dom_snapshot = dom_html if isinstance(dom_html, str) else ""
    interaction = interaction_log if isinstance(interaction_log, dict) else {}

    logger.info(
        "Scan completed for url=%s | mode=%s | wcag_violations=%s | security_errors=%s",
        url,
        mode.value,
        len(wcag_results_dict.get("violations", [])) if isinstance(wcag_results_dict, dict) else "n/a",
        bool(security_results_dict.get("error")) if isinstance(security_results_dict, dict) else "n/a",
    )

    # Generate structured findings and AI recommendations (run in thread)
    findings: Dict[str, Any] = {}
    recommendations: str = ""
    try:
        fr = await asyncio.to_thread(
            generate_findings_and_recommendations,
            {
                "wcag_results": wcag_results_dict,
                "security_results": security_results_dict,
                "_extras": {"dom_snapshot": dom_snapshot, "interaction_log": interaction},
                "_mode": mode.value,
            },
        )
        findings = fr.get("findings", {}) or {}
        recommendations = fr.get("recommendations", "") or ""
        logger.info(
            "Findings generated: sec=%d acc=%d nav=%d",
            len(findings.get("security", []) or []),
            len(findings.get("accessibility", []) or []),
            len(findings.get("navigation", []) or []),
        )
    except Exception:
        logger.exception("Findings/recommendations generation failed")
        recommendations = (
            "AI recommendations unavailable. Consider reviewing WCAG violations and missing security headers."
        )

    resp = ScanResponse(
        wcag_results=wcag_results_dict,
        security_results=security_results_dict,
        findings=findings,
        recommendations=recommendations,
    )
    # Real-time alert for critical security risks only
    try:
        if mode in (ScanMode.all, ScanMode.security):
            sec_findings = (findings or {}).get("security", []) or []
            has_critical_security = any((f.get("severity") or "").lower() == "critical" for f in sec_findings)
            if has_critical_security:
                await emit_critical_alert(f"Critical security risk detected for {url}")
    except Exception:
        logger.exception("Failed to evaluate critical security alert condition")
    return resp


@app.post("/export/pdf", dependencies=[Depends(require_api_key)])
async def export_pdf(payload: ScanRequest) -> StreamingResponse:
    # Simple export: run scan once and render recommendations to PDF-like bytes using ReportLab
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    import io

    res = await scan(payload)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    textobject = c.beginText(40, 750)
    textobject.setFont("Helvetica", 10)
    # Write a compact findings summary first, filtered by mode
    try:
        findings = getattr(res, "findings", {}) or {}
        mode = payload.mode or ScanMode.all
        lines = ["Security Findings:"]
        if mode in (ScanMode.all, ScanMode.security):
            for it in (findings.get("security", []) or [])[:30]:
                lines.append(f"- [{it.get('severity')}] {it.get('title')}")
        else:
            lines.append("(skipped)")
        lines.append("")
        lines.append("Accessibility Findings:")
        if mode in (ScanMode.all, ScanMode.accessibility):
            for it in (findings.get("accessibility", []) or [])[:30]:
                lines.append(f"- [{it.get('severity')}] {it.get('title')}")
        else:
            lines.append("(skipped)")
        lines.append("")
        lines.append("Navigation Findings:")
        if mode in (ScanMode.all, ScanMode.accessibility):
            for it in (findings.get("navigation", []) or [])[:30]:
                lines.append(f"- [{it.get('severity')}] {it.get('title')}")
        else:
            lines.append("(skipped)")
        lines.append("")
        lines.append("AI Recommendations:")
        text = "\n".join(lines) + "\n\n" + (res.recommendations or "")
    except Exception:
        text = (res.recommendations or "UI Compliance Report")
    for line in text.splitlines() or ["UI Compliance Report"]:
        if textobject.getY() < 40:
            c.drawText(textobject)
            c.showPage()
            textobject = c.beginText(40, 750)
            textobject.setFont("Helvetica", 10)
        textobject.textLine(line[:110])
    c.drawText(textobject)
    c.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=report.pdf"})


@app.post("/export/excel", dependencies=[Depends(require_api_key)])
async def export_excel(payload: ScanRequest) -> StreamingResponse:
    import io
    import pandas as pd
    engine = None
    try:
        import xlsxwriter  # noqa: F401
        engine = "xlsxwriter"
    except Exception:
        try:
            import openpyxl  # noqa: F401
            engine = "openpyxl"
        except Exception:
            # Return a friendly error instead of 500
            buf = io.BytesIO()
            buf.write(b"Excel export requires xlsxwriter or openpyxl. Please install one.")
            buf.seek(0)
            return StreamingResponse(buf, media_type="text/plain")

    res = await scan(payload)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine=engine) as xw:
        mode = payload.mode or ScanMode.all
        if mode in (ScanMode.all, ScanMode.accessibility):
            wcag_df = pd.DataFrame(res.wcag_results.get("violations", []))
            if not wcag_df.empty:
                wcag_df.to_excel(xw, index=False, sheet_name="WCAG")
        if mode in (ScanMode.all, ScanMode.security):
            sec_df = pd.json_normalize(res.security_results)
            if not sec_df.empty:
                sec_df.to_excel(xw, index=False, sheet_name="Security")
        # Structured findings sheets
        try:
            findings = getattr(res, "findings", {}) or {}
            def _mk_df(items, category):
                import pandas as _pd
                rows = []
                for it in items or []:
                    rows.append({
                        "Category": category,
                        "Title": it.get("title"),
                        "Severity": it.get("severity"),
                        "Rule": it.get("rule"),
                        "Evidence": it.get("evidence"),
                        "Fix": it.get("fix"),
                    })
                return _pd.DataFrame(rows)
            if mode in (ScanMode.all, ScanMode.security):
                f_sec = _mk_df(findings.get("security", []), "Security")
                if not f_sec.empty:
                    f_sec.to_excel(xw, index=False, sheet_name="Findings_Security")
            if mode in (ScanMode.all, ScanMode.accessibility):
                f_acc = _mk_df(findings.get("accessibility", []), "Accessibility")
                f_nav = _mk_df(findings.get("navigation", []), "Navigation")
                if not f_acc.empty:
                    f_acc.to_excel(xw, index=False, sheet_name="Findings_Access")
                if not f_nav.empty:
                    f_nav.to_excel(xw, index=False, sheet_name="Findings_Nav")
        except Exception:
            pass
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=report.xlsx"})


@app.post("/scan-authenticated", response_model=AuthenticatedScanResponse, dependencies=[Depends(require_api_key)])
async def scan_authenticated(payload: AuthenticatedScanRequest) -> AuthenticatedScanResponse:
    """
    Scan website with authentication support for login-protected pages.
    
    This endpoint handles websites that require login credentials to access
    protected areas. It will automatically detect login pages, authenticate
    using provided credentials, and then scan the authenticated areas.
    """
    url = _normalize_url(payload.url.strip())
    if not url:
        logger.warning("/scan-authenticated called without URL")
        raise HTTPException(status_code=400, detail="URL is required")
    
    if not payload.credentials or not payload.credentials.get("username") or not payload.credentials.get("password"):
        raise HTTPException(status_code=400, detail="Username and password are required for authenticated scanning")
    
    mode = payload.mode or ScanMode.all
    logger.info("Starting authenticated scan for url=%s | mode=%s | user=%s", 
                url, mode.value, payload.credentials.get("username"))
    
    try:
        # Create authenticated scanner
        scanner = AuthenticatedSiteScanOrchestrator(
            credentials=payload.credentials,
            max_pages=payload.max_pages,
            max_depth=payload.max_depth,
            scan_mode=mode.value,
            parallel_scans=payload.parallel_scans
        )
        
        # Run authenticated scan
        result = await scanner.scan_site_with_auth(url)
        
        # Check if authentication was required and successful
        auth_required = result.get("authentication_required", False)
        auth_successful = result.get("authentication_successful", False)
        session_used = result.get("session_used", False)
        
        if auth_required and not auth_successful:
            logger.warning("Authentication failed for url=%s", url)
            raise HTTPException(
                status_code=401, 
                detail="Authentication failed. Please check your credentials."
            )
        
        # Generate AI recommendations if scan was successful
        findings = result.get("findings", {})
        recommendations = result.get("recommendations", "")
        
        if not recommendations and (result.get("wcag_results") or result.get("security_results")):
            try:
                fr = await asyncio.to_thread(
                    generate_findings_and_recommendations,
                    {
                        "wcag_results": result.get("wcag_results", {}),
                        "security_results": result.get("security_results", {}),
                        "_mode": mode.value,
                        "_authenticated": True
                    }
                )
                findings = fr.get("findings", {}) or {}
                recommendations = fr.get("recommendations", "") or ""
            except Exception:
                logger.exception("Failed to generate recommendations for authenticated scan")
                recommendations = "AI recommendations unavailable for authenticated scan."
        
        return AuthenticatedScanResponse(
            wcag_results=result.get("wcag_results", {}),
            security_results=result.get("security_results", {}),
            findings=findings,
            recommendations=recommendations,
            authentication_required=auth_required,
            authentication_successful=auth_successful,
            session_used=session_used
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Authenticated scan failed for url=%s", url)
        raise HTTPException(status_code=500, detail=f"Authenticated scan failed: {str(e)}")


@app.post("/test-authentication", dependencies=[Depends(require_api_key)])
async def test_authentication(payload: AuthenticationTestRequest) -> Dict[str, Any]:
    """
    Test authentication for a URL without running a full scan.
    
    This endpoint allows you to test if authentication works for a given URL
    and credentials before running a full authenticated scan.
    """
    url = _normalize_url(payload.url.strip())
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    if not payload.credentials or not payload.credentials.get("username") or not payload.credentials.get("password"):
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    logger.info("Testing authentication for url=%s | user=%s", 
                url, payload.credentials.get("username"))
    
    try:
        # Create authenticated scanner for testing
        scanner = AuthenticatedSiteScanOrchestrator(
            credentials=payload.credentials,
            max_pages=10,  # Minimal for testing
            max_depth=1,
            scan_mode="all"
        )
        
        # Test authentication only
        result = await scanner.test_authentication_only(url)
        
        return {
            "url": url,
            "authentication_required": result.get("authentication_required", False),
            "authentication_successful": result.get("authentication_successful", False),
            "login_form_detected": result.get("login_form_detected", False),
            "session_info": result.get("session_info", {}),
            "final_url": result.get("final_url", url),
            "error": result.get("error")
        }
        
    except Exception as e:
        logger.exception("Authentication test failed for url=%s", url)
        raise HTTPException(status_code=500, detail=f"Authentication test failed: {str(e)}")


@app.post("/scan-with-auth", response_model=ScanResponse, dependencies=[Depends(require_api_key)])
async def scan_with_auth(payload: AuthenticatedScanRequest) -> ScanResponse:
    """
    Enhanced single-page scan with authentication support.
    
    This endpoint performs a single-page scan but with authentication support,
    useful for testing individual pages that require login.
    """
    url = _normalize_url(payload.url.strip())
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    mode = payload.mode or ScanMode.all
    logger.info("Starting authenticated single-page scan for url=%s | mode=%s", url, mode.value)
    
    try:
        # Run interactive test with authentication
        interaction_result = run_interactive_test_with_auth(url, payload.credentials)
        
        # Check authentication status
        auth_required = interaction_result.get("authentication_required", False)
        auth_successful = interaction_result.get("authentication_successful", False)
        
        if auth_required and not auth_successful:
            raise HTTPException(
                status_code=401,
                detail="Authentication failed. Please check your credentials."
            )
        
        # Run scans based on mode
        wcag_task = None
        security_task = None
        dom_task = None
        
        if mode in (ScanMode.all, ScanMode.accessibility):
            wcag_task = asyncio.create_task(run_wcag_scan(url))
            dom_task = asyncio.to_thread(get_dom_snapshot, url)
        
        if mode in (ScanMode.all, ScanMode.security):
            security_task = asyncio.create_task(run_security_scan(url))
        
        async def _gather_or_none(task):
            return await task if task is not None else None
        
        wcag_results, security_results, dom_html = await asyncio.gather(
            _gather_or_none(wcag_task),
            _gather_or_none(security_task),
            _gather_or_none(dom_task),
            return_exceptions=True,
        )
        
        # Normalize results
        def ensure_dict(result: Any, label: str) -> Dict[str, Any]:
            if isinstance(result, Exception):
                logger.exception("%s raised an exception", label)
                return {"error": f"{label} failed: {str(result)}"}
            if isinstance(result, dict):
                return result
            logger.error("%s returned unexpected type: %s", label, type(result))
            return {"error": f"Unexpected {label} result type"}
        
        wcag_results_dict = ensure_dict(wcag_results, "WCAG scan") if wcag_results is not None else {}
        security_results_dict = ensure_dict(security_results, "Security scan") if security_results is not None else {}
        dom_snapshot = dom_html if isinstance(dom_html, str) else ""
        
        # Generate recommendations
        findings: Dict[str, Any] = {}
        recommendations: str = ""
        try:
            fr = await asyncio.to_thread(
                generate_findings_and_recommendations,
                {
                    "wcag_results": wcag_results_dict,
                    "security_results": security_results_dict,
                    "_extras": {"dom_snapshot": dom_snapshot, "interaction_log": interaction_result},
                    "_mode": mode.value,
                    "_authenticated": True
                },
            )
            findings = fr.get("findings", {}) or {}
            recommendations = fr.get("recommendations", "") or ""
        except Exception:
            logger.exception("Findings/recommendations generation failed")
            recommendations = "AI recommendations unavailable for authenticated scan."
        
        return ScanResponse(
            wcag_results=wcag_results_dict,
            security_results=security_results_dict,
            findings=findings,
            recommendations=recommendations
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Authenticated single-page scan failed for url=%s", url)
        raise HTTPException(status_code=500, detail=f"Authenticated scan failed: {str(e)}")


