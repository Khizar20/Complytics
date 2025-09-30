import asyncio
import io
import os
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils.security import get_current_user
from ui_testing.scanners.wcag import run_wcag_scan, get_dom_snapshot
from ui_testing.scanners.security import run_security_scan
from ui_testing.scanners.interaction import run_interactive_test
from ui_testing.ai.recommendations import (
    configure_gemini,
    generate_findings_and_recommendations,
)
from config import settings


router = APIRouter()


class ScanMode(str, Enum):
    all = "all"
    accessibility = "accessibility"
    security = "security"


class ScanRequest(BaseModel):
    url: str
    mode: ScanMode = ScanMode.all


@router.on_event("startup")
async def on_startup() -> None:
    configure_gemini(settings.GOOGLE_API_KEY)


def _normalize_url(input_url: str) -> str:
    if not input_url:
        return input_url
    if input_url.startswith("http://") or input_url.startswith("https://"):
        return input_url
    return f"https://{input_url}"


@router.post("/ui/scan")
async def scan(payload: ScanRequest, user=Depends(get_current_user)) -> Dict[str, Any]:
    url = _normalize_url((payload.url or "").strip())
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    mode = payload.mode or ScanMode.all

    wcag_task = None
    security_task = None
    dom_task = None
    interaction_task = None
    if mode in (ScanMode.all, ScanMode.accessibility):
        wcag_task = asyncio.create_task(run_wcag_scan(url))
        dom_task = asyncio.to_thread(get_dom_snapshot, url)
        interaction_task = asyncio.to_thread(run_interactive_test, url)
    if mode in (ScanMode.all, ScanMode.security):
        security_task = asyncio.to_thread(run_security_scan, url)

    async def _gather_or_none(task):
        return await task if task is not None else None

    wcag_results, security_results, dom_html, interaction_log = await asyncio.gather(
        _gather_or_none(wcag_task),
        _gather_or_none(security_task),
        _gather_or_none(dom_task),
        _gather_or_none(interaction_task),
        return_exceptions=True,
    )

    def ensure_dict(result: Any) -> Dict[str, Any]:
        if isinstance(result, Exception):
            return {"error": str(result)}
        if isinstance(result, dict):
            return result
        return {"error": "Unexpected result type"}

    wcag_results_dict = ensure_dict(wcag_results) if wcag_results is not None else {}
    security_results_dict = ensure_dict(security_results) if security_results is not None else {}
    dom_snapshot = dom_html if isinstance(dom_html, str) else ""
    interaction = interaction_log if isinstance(interaction_log, dict) else {}

    fr = await asyncio.to_thread(
        generate_findings_and_recommendations,
        {
            "wcag_results": wcag_results_dict,
            "security_results": security_results_dict,
            "_extras": {"dom_snapshot": dom_snapshot, "interaction_log": interaction},
            "_mode": mode.value,
        },
    )
    return {
        "wcag_results": wcag_results_dict,
        "security_results": security_results_dict,
        "findings": fr.get("findings", {}),
        "recommendations": fr.get("recommendations", ""),
    }


@router.post("/ui/export/pdf")
async def export_pdf(payload: ScanRequest, user=Depends(get_current_user)) -> StreamingResponse:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter

    res = await scan(payload, user)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    textobject = c.beginText(40, 750)
    textobject.setFont("Helvetica", 10)
    try:
        findings = res.get("findings", {}) or {}
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
        lines.append("AI Recommendations:")
        text = "\n".join(lines) + "\n\n" + (res.get("recommendations") or "")
    except Exception:
        text = (res.get("recommendations") or "UI Compliance Report")
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
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=ui-testing-report.pdf"})


@router.post("/ui/export/excel")
async def export_excel(payload: ScanRequest, user=Depends(get_current_user)) -> StreamingResponse:
    import pandas as pd
    import io
    engine = None
    try:
        import xlsxwriter  # noqa: F401
        engine = "xlsxwriter"
    except Exception:
        try:
            import openpyxl  # noqa: F401
            engine = "openpyxl"
        except Exception:
            buf = io.BytesIO()
            buf.write(b"Excel export requires xlsxwriter or openpyxl. Please install one.")
            buf.seek(0)
            return StreamingResponse(buf, media_type="text/plain")

    res = await scan(payload, user)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine=engine) as xw:
        mode = payload.mode or ScanMode.all
        if mode in (ScanMode.all, ScanMode.accessibility):
            wcag_df = pd.DataFrame(res.get("wcag_results", {}).get("violations", []))
            if not wcag_df.empty:
                wcag_df.to_excel(xw, index=False, sheet_name="WCAG")
        if mode in (ScanMode.all, ScanMode.security):
            sec_df = pd.json_normalize(res.get("security_results", {}))
            if not sec_df.empty:
                sec_df.to_excel(xw, index=False, sheet_name="Security")
        try:
            findings = res.get("findings", {}) or {}
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
                if not f_acc.empty:
                    f_acc.to_excel(xw, index=False, sheet_name="Findings_Access")
        except Exception:
            pass
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=ui-testing-report.xlsx"})


