import asyncio
import io
import os
import time
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils.security import get_current_user
from db import database
from ui_testing.scanners.wcag import run_wcag_scan, get_dom_snapshot
from ui_testing.scanners.security import run_security_scan
from ui_testing.scanners.interaction import run_interactive_test
from ui_testing.ai.recommendations import (
    configure_gemini,
    generate_findings_and_recommendations,
)
from config import settings
from utils.security import send_simple_email
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timezone
from bson import ObjectId
from types import SimpleNamespace


router = APIRouter()

# Simple in-memory cache to avoid re-running scans immediately for exports
SCAN_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


class ScanMode(str, Enum):
    all = "all"
    accessibility = "accessibility"
    security = "security"


class ScanRequest(BaseModel):
    url: str
    mode: ScanMode = ScanMode.all
    force: bool = False


class ScheduleScanRequest(BaseModel):
    run_at_iso: str  # ISO 8601 datetime string in user's local or UTC; we interpret as UTC if zoned


@router.on_event("startup")
async def on_startup() -> None:
    configure_gemini(settings.GOOGLE_API_KEY)
    # Initialize scheduler and rehydrate pending jobs
    global SCHEDULER
    try:
        if 'SCHEDULER' not in globals() or SCHEDULER is None:
            SCHEDULER = AsyncIOScheduler()
            SCHEDULER.start()
        # Rehydrate scheduled scans
        if database.db is not None:
            now_ts = int(time.time())
            cursor = database.db.scheduled_scans.find({
                "status": "scheduled",
                "scheduled_for": {"$gte": now_ts}
            })
            async for doc in cursor:
                job_id = str(doc.get("_id"))
                run_date = datetime.fromtimestamp(doc.get("scheduled_for"), tz=timezone.utc)
                if SCHEDULER.get_job(job_id) is None:
                    SCHEDULER.add_job(_execute_scheduled_scan, trigger=DateTrigger(run_date=run_date), id=job_id, args=[job_id])
    except Exception:
        # Do not crash app on scheduler failures
        pass


@router.on_event("shutdown")
async def on_shutdown() -> None:
    try:
        if 'SCHEDULER' in globals() and SCHEDULER is not None:
            SCHEDULER.shutdown(wait=False)
    except Exception:
        pass


def _normalize_url(input_url: str) -> str:
    if not input_url:
        return input_url
    if input_url.startswith("http://") or input_url.startswith("https://"):
        return input_url
    return f"https://{input_url}"


def _cache_key(url: str, mode: ScanMode) -> str:
    return f"{mode.value}:{url}"


def _get_cached_scan(url: str, mode: ScanMode) -> Optional[Dict[str, Any]]:
    key = _cache_key(url, mode)
    entry = SCAN_CACHE.get(key)
    if not entry:
        return None
    ts = entry.get("ts")
    if not isinstance(ts, (int, float)):
        return None
    if time.time() - ts > CACHE_TTL_SECONDS:
        # expired
        SCAN_CACHE.pop(key, None)
        return None
    return entry.get("data")


def _set_cached_scan(url: str, mode: ScanMode, data: Dict[str, Any]) -> None:
    key = _cache_key(url, mode)
    SCAN_CACHE[key] = {"ts": time.time(), "data": data}


async def _run_scan_and_persist(url: str, mode: ScanMode, org_id: Any, requested_by: Any) -> Dict[str, Any]:
    """Run the UI scan using existing scan implementation and persist with provided org/user."""
    # Build a minimal user-like object for reuse of scan() persistence logic
    user_like = SimpleNamespace()
    setattr(user_like, 'organization_id', org_id)
    setattr(user_like, 'id', requested_by)
    payload = ScanRequest(url=url, mode=mode)
    return await scan(payload, user=user_like)  # type: ignore[arg-type]


async def _execute_scheduled_scan(schedule_id: str) -> None:
    """Job entrypoint for executing a scheduled scan and emailing results."""
    try:
        if database.db is None:
            return
        # Load schedule
        doc = await database.db.scheduled_scans.find_one({"_id": ObjectId(schedule_id)})
        if not doc or doc.get("status") != "scheduled":
            return
        org_id = doc.get("organization_id")
        requested_by = doc.get("scheduled_by")
        email_to = doc.get("email")

        # Mark running
        await database.db.scheduled_scans.update_one({"_id": ObjectId(schedule_id)}, {"$set": {"status": "running", "updated_at": int(time.time())}})

        # Get last scanned URL for the org
        last_doc = await database.db.ui_testing_results.find_one({"organization_id": org_id}, sort=[("created_at", -1)])
        url = (last_doc or {}).get("url")
        if not url:
            # No previous scans to re-use
            await database.db.scheduled_scans.update_one({"_id": ObjectId(schedule_id)}, {"$set": {"status": "failed", "error": "No previous scan URL found", "updated_at": int(time.time())}})
            return

        # Execute scan (always run 'all')
        result = await _run_scan_and_persist(url=url, mode=ScanMode.all, org_id=org_id, requested_by=requested_by)

        # Email results
        try:
            findings = result.get("findings", {}) or {}
            wcag = result.get("wcag_results", {}) or {}
            violations = wcag.get("violations", []) or []
            sev_counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0, "unknown": 0}
            for v in violations:
                impact = str(v.get("impact", "")).lower()
                if impact in sev_counts:
                    sev_counts[impact] += 1
                else:
                    sev_counts["unknown"] += 1
            subject = "Complytics: Scheduled UI Compliance Scan Completed"
            html = f"""
            <html>
              <body>
                <h3>Scheduled Scan Completed</h3>
                <p><strong>URL:</strong> {url}</p>
                <p><strong>Timestamp (UTC):</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}</p>
                <h4>Accessibility (WCAG) Violations</h4>
                <ul>
                  <li>Critical: {sev_counts['critical']}</li>
                  <li>Serious: {sev_counts['serious']}</li>
                  <li>Moderate: {sev_counts['moderate']}</li>
                  <li>Minor: {sev_counts['minor']}</li>
                </ul>
                <h4>AI Recommendations</h4>
                <pre style="white-space:pre-wrap">{result.get('recommendations','')}</pre>
              </body>
            </html>
            """
            if email_to:
                await send_simple_email(email_to, subject, html)
        except Exception:
            # Email failures should not mark job failed
            pass

        # Mark completed
        await database.db.scheduled_scans.update_one({"_id": ObjectId(schedule_id)}, {"$set": {"status": "completed", "updated_at": int(time.time())}})
    except Exception as e:
        try:
            if database.db is not None:
                await database.db.scheduled_scans.update_one({"_id": ObjectId(schedule_id)}, {"$set": {"status": "failed", "error": str(e), "updated_at": int(time.time())}})
        except Exception:
            pass


@router.post("/ui/scan")
async def scan(payload: ScanRequest, user=Depends(get_current_user)) -> Dict[str, Any]:
    url = _normalize_url((payload.url or "").strip())
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    mode = payload.mode or ScanMode.all
    force = bool(getattr(payload, 'force', False))

    # Return cached results if available and fresh, unless forcing a fresh run
    if not force:
        cached = _get_cached_scan(url, mode)
        if cached is not None:
            return cached

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
    result = {
        "wcag_results": wcag_results_dict,
        "security_results": security_results_dict,
        "findings": fr.get("findings", {}),
        "recommendations": fr.get("recommendations", ""),
    }
    _set_cached_scan(url, mode, result)

    # Persist to database for organization visibility
    try:
        org_id = getattr(user, 'organization_id', None)
        if database.db is not None and org_id:
            doc = {
                "organization_id": org_id,
                "requested_by": getattr(user, 'id', None) or getattr(user, '_id', None),
                "url": url,
                "mode": mode.value,
                "results": result,
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }
            await database.db.ui_testing_results.insert_one(doc)
    except Exception:
        # Do not block scan response on persistence failure
        pass
    return result


@router.post("/ui/scan-now")
async def scan_now(user=Depends(get_current_user)) -> Dict[str, Any]:
    org_id = getattr(user, 'organization_id', None)
    if not org_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    if database.db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    # Find most recent URL scanned for this org
    last_doc = await database.db.ui_testing_results.find_one({"organization_id": org_id}, sort=[("created_at", -1)])
    url = (last_doc or {}).get("url")
    if not url:
        raise HTTPException(status_code=400, detail="No previous website found. Please provide a URL in UI Testing first.")

    # Run full scan now and persist
    result = await _run_scan_and_persist(url=url, mode=ScanMode.all, org_id=org_id, requested_by=getattr(user, 'id', None) or getattr(user, '_id', None))
    return {"message": "Scan completed", "url": url, "result": result}


@router.post("/ui/schedule")
async def schedule_scan(payload: ScheduleScanRequest, user=Depends(get_current_user)) -> Dict[str, Any]:
    # Only compliance team members (and superadmin/admins) can schedule
    role = getattr(user, 'role', '')
    if role not in ("compliance_team", "admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Not authorized to schedule scans")
    org_id = getattr(user, 'organization_id', None)
    if not org_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    # Parse date
    try:
        # fromisoformat supports offsets; assume UTC if provided, else treat as UTC
        dt = datetime.fromisoformat(payload.run_at_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        run_at_utc = dt.astimezone(timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid run_at_iso format")

    run_ts = int(run_at_utc.timestamp())
    if run_ts <= int(time.time()):
        raise HTTPException(status_code=400, detail="run_at must be in the future")

    # Persist schedule
    doc = {
        "organization_id": org_id,
        "scheduled_by": getattr(user, 'id', None) or getattr(user, '_id', None),
        "email": getattr(user, 'email', None),
        "scheduled_for": run_ts,
        "status": "scheduled",
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    }
    if database.db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    res = await database.db.scheduled_scans.insert_one(doc)
    schedule_id = str(res.inserted_id)

    # Schedule job in memory
    global SCHEDULER
    if 'SCHEDULER' not in globals() or SCHEDULER is None:
        SCHEDULER = AsyncIOScheduler()
        SCHEDULER.start()
    run_date = datetime.fromtimestamp(run_ts, tz=timezone.utc)
    if SCHEDULER.get_job(schedule_id) is None:
        SCHEDULER.add_job(_execute_scheduled_scan, trigger=DateTrigger(run_date=run_date), id=schedule_id, args=[schedule_id])

    return {"id": schedule_id, "scheduled_for": run_ts, "status": "scheduled"}


@router.get("/ui/schedules")
async def list_schedules(user=Depends(get_current_user)) -> Dict[str, Any]:
    org_id = getattr(user, 'organization_id', None)
    if not org_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    if database.db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    items = []
    cursor = database.db.scheduled_scans.find({"organization_id": org_id}).sort("scheduled_for", 1)
    async for d in cursor:
        d["_id"] = str(d.get("_id"))
        items.append(d)
    return {"schedules": items}


@router.delete("/ui/schedules/{schedule_id}")
async def cancel_schedule(schedule_id: str, user=Depends(get_current_user)) -> Dict[str, Any]:
    org_id = getattr(user, 'organization_id', None)
    if not org_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    if database.db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    doc = await database.db.scheduled_scans.find_one({"_id": ObjectId(schedule_id)})
    if not doc or doc.get("organization_id") != org_id:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if doc.get("status") in ("completed", "failed"):
        return {"id": schedule_id, "status": doc.get("status")}
    await database.db.scheduled_scans.update_one({"_id": ObjectId(schedule_id)}, {"$set": {"status": "cancelled", "updated_at": int(time.time())}})
    try:
        if 'SCHEDULER' in globals() and SCHEDULER is not None:
            job = SCHEDULER.get_job(schedule_id)
            if job:
                job.remove()
    except Exception:
        pass
    return {"id": schedule_id, "status": "cancelled"}
@router.get("/ui/latest")
async def get_latest_ui_result(user=Depends(get_current_user)) -> Dict[str, Any]:
    org_id = getattr(user, 'organization_id', None)
    if not org_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    try:
        if database.db is None:
            raise HTTPException(status_code=500, detail="Database not initialized")
        doc = await database.db.ui_testing_results.find_one(
            {"organization_id": org_id}, sort=[("created_at", -1)]
        )
        if not doc:
            return {"result": None}
        # Normalize id
        doc["_id"] = str(doc.get("_id"))
        return {
            "result": doc.get("results"),
            "url": doc.get("url"),
            "mode": doc.get("mode"),
            "created_at": doc.get("created_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch latest UI result: {e}")


@router.post("/ui/export/pdf")
async def export_pdf(payload: ScanRequest, user=Depends(get_current_user)) -> StreamingResponse:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter

    url = _normalize_url((payload.url or "").strip())
    mode = payload.mode or ScanMode.all
    res = _get_cached_scan(url, mode)
    if res is None:
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

    url = _normalize_url((payload.url or "").strip())
    mode = payload.mode or ScanMode.all
    res = _get_cached_scan(url, mode)
    if res is None:
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


