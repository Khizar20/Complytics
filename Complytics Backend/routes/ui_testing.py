import asyncio
import io
import os
import time
import logging
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils.security import get_current_user
from db import database
from ui_testing.scanners.wcag import run_wcag_scan, get_dom_snapshot
from ui_testing.scanners.security import run_security_scan
from ui_testing.scanners.interaction import run_interactive_test, run_interactive_test_with_auth
from ui_testing.scanners.authenticated_site_scanner import scan_authenticated_site
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
logger = logging.getLogger("routes.ui_testing")

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
    url: Optional[str] = None  # Optional URL - if not provided, uses last scanned URL


@router.on_event("startup")
async def on_startup() -> None:
    configure_gemini(settings.GOOGLE_API_KEY1, settings.GOOGLE_API_KEY2)
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
    """Job entrypoint for executing a scheduled whole-site scan and emailing results."""
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

        # Get URL - use stored URL if provided, otherwise use last scanned URL
        url = doc.get("url")
        if not url:
            # Get last scanned URL for the org (prefer whole-site scan results)
            last_doc = await database.db.ui_testing_site_results.find_one({"organization_id": org_id}, sort=[("created_at", -1)])
            if not last_doc:
                # Fallback to single-page scan results
                last_doc = await database.db.ui_testing_results.find_one({"organization_id": org_id}, sort=[("created_at", -1)])
            
            url = (last_doc or {}).get("url")
            if not url:
                # No previous scans to re-use
                await database.db.scheduled_scans.update_one({"_id": ObjectId(schedule_id)}, {"$set": {"status": "failed", "error": "No previous scan URL found", "updated_at": int(time.time())}})
                return

        # Execute whole-site scan (comprehensive testing)
        try:
            from ui_testing.scanners.site_scanner import scan_whole_site
            
            logger.info(f"Starting scheduled whole-site scan for {url} | org={org_id}")
            
            result = await scan_whole_site(
                url=url,
                max_pages=50,
                max_depth=3,
                scan_mode="all",
                parallel_scans=3,
                use_selenium_crawler=False,
                db=database.db,
                organization_id=str(org_id) if org_id else None
            )
            
            # Generate AI recommendations for the site scan
            try:
                from ui_testing.ai.recommendations import generate_findings_and_recommendations
                
                # Format the result for AI recommendations with complete site-wide data
                wcag_agg = result.get("wcag_aggregate", {})
                ai_input = {
                    "wcag_results": {
                        "violations": wcag_agg.get("violations_summary", []),
                        "total_violations": wcag_agg.get("total_violations", 0),
                        "unique_rules_violated": wcag_agg.get("unique_rules_violated", 0),
                        "pages_with_issues": wcag_agg.get("pages_with_issues", 0),
                        "total_pages_scanned": wcag_agg.get("total_pages_scanned", 0),
                        "impact_counts": wcag_agg.get("impact_counts", {})
                    },
                    "security_results": result.get("security_aggregate", {}).get("primary_scan", {}),
                    "_extras": {
                        "pages_scanned": result.get("summary", {}).get("pages_scanned", 0),
                        "accessibility_score": result.get("summary", {}).get("accessibility_score", 0)
                    },
                    "_mode": "all",
                }
                
                fr = await asyncio.to_thread(
                    generate_findings_and_recommendations,
                    ai_input
                )
                
                # Add findings and recommendations to result
                result["findings"] = fr.get("findings", {})
                result["recommendations"] = fr.get("recommendations", "")
                
            except Exception as e:
                logger.error(f"Failed to generate AI recommendations for scheduled scan: {e}")
                result["findings"] = {}
                result["recommendations"] = "AI recommendations unavailable"
            
            # Persist the result to database
            try:
                if database.db is not None:
                    await database.db.ui_testing_site_results.insert_one({
                        "organization_id": org_id,
                        "user_id": requested_by,
                        "url": url,
                        "mode": "all",
                        "result": result,
                        "created_at": int(time.time())
                    })
            except Exception as e:
                logger.error(f"Failed to persist scheduled site scan result: {e}")
            
        except Exception as e:
            logger.error(f"Scheduled whole-site scan failed: {e}")
            # Fallback to single-page scan if whole-site scan fails
            logger.info("Falling back to single-page scan...")
            result = await _run_scan_and_persist(url=url, mode=ScanMode.all, org_id=org_id, requested_by=requested_by)

        # Email results
        try:
            # Handle both whole-site and single-page result formats
            if result.get("wcag_aggregate"):
                # Whole-site scan results
                wcag_agg = result.get("wcag_aggregate", {})
                sev_counts = wcag_agg.get("impact_counts", {"critical": 0, "serious": 0, "moderate": 0, "minor": 0})
                pages_scanned = result.get("summary", {}).get("pages_scanned", 0)
                accessibility_score = result.get("summary", {}).get("accessibility_score", 0)
                total_violations = wcag_agg.get("total_violations", 0)
                unique_issues = wcag_agg.get("unique_rules_violated", 0)
                
                subject = "Complytics: Scheduled Whole-Site Compliance Scan Completed"
                html = f"""
                <html>
                  <body>
                    <h3>Scheduled Whole-Site Scan Completed</h3>
                    <p><strong>URL:</strong> {url}</p>
                    <p><strong>Timestamp (UTC):</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Pages Scanned:</strong> {pages_scanned}</p>
                    <p><strong>Accessibility Score:</strong> {accessibility_score}/100</p>
                    <h4>Accessibility (WCAG) Violations</h4>
                    <ul>
                      <li>Total Violations: {total_violations}</li>
                      <li>Unique Issues: {unique_issues}</li>
                      <li>Critical: {sev_counts.get('critical', 0)}</li>
                      <li>Serious: {sev_counts.get('serious', 0)}</li>
                      <li>Moderate: {sev_counts.get('moderate', 0)}</li>
                      <li>Minor: {sev_counts.get('minor', 0)}</li>
                    </ul>
                    <h4>AI Recommendations</h4>
                    <pre style="white-space:pre-wrap">{result.get('recommendations','')}</pre>
                  </body>
                </html>
                """
            else:
                # Single-page scan results (fallback)
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

    wcag_results = {}
    security_results = {}
    dom_html = ""
    interaction_log = {}
    # Sequence heavy headless Chrome tasks to avoid parallel renderer contention
    if mode in (ScanMode.all, ScanMode.accessibility):
        try:
            # For standard scans, no credentials needed
            wcag_results = await run_wcag_scan(url)
        except Exception as e:
            wcag_results = {"error": str(e), "violations": []}
        try:
            dom_html = await asyncio.to_thread(get_dom_snapshot, url)
        except Exception:
            dom_html = ""
        try:
            interaction_log = await asyncio.to_thread(run_interactive_test, url)
        except Exception:
            interaction_log = {}
    if mode in (ScanMode.all, ScanMode.security):
        try:
            security_results = await asyncio.to_thread(run_security_scan, url)
        except Exception as e:
            security_results = {"error": str(e)}

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
    def _compute_a11y_score(w: Dict[str, Any]) -> int:
        try:
            violations = (w or {}).get("violations") or []
            counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0, "unknown": 0}
            for v in violations:
                imp = str(v.get("impact", "")).lower()
                if imp in counts:
                    counts[imp] += 1
                else:
                    counts["unknown"] += 1
            deduction = counts["critical"] * 25 + counts["serious"] * 15 + counts["moderate"] * 8 + counts["minor"] * 3 + counts["unknown"] * 5
            score = max(0, min(100, 100 - deduction))
            if len(violations) == 0:
                return 100
            return score
        except Exception:
            return 0
    def _compute_security_score(s: Dict[str, Any]) -> int:
        try:
            sh = (s or {}).get("securityheaders") or {}
            if isinstance(sh.get("score"), (int, float)):
                return int(sh["score"])  # SecurityHeaders may return numeric score
            missing = len((sh.get("missing") or []))
            return max(0, 100 - missing * 15)
        except Exception:
            return 0
    result = {
        "wcag_results": wcag_results_dict,
        "security_results": security_results_dict,
        "findings": fr.get("findings", {}),
        "recommendations": fr.get("recommendations", ""),
        "a11y_score": _compute_a11y_score(wcag_results_dict) if mode in (ScanMode.all, ScanMode.accessibility) else None,
        "security_score": _compute_security_score(security_results_dict) if mode in (ScanMode.all, ScanMode.security) else None,
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

    # Find most recent URL scanned for this org (prefer whole-site scan results)
    last_doc = await database.db.ui_testing_site_results.find_one({"organization_id": org_id}, sort=[("created_at", -1)])
    if not last_doc:
        # Fallback to single-page scan results
        last_doc = await database.db.ui_testing_results.find_one({"organization_id": org_id}, sort=[("created_at", -1)])
    
    url = (last_doc or {}).get("url")
    if not url:
        raise HTTPException(status_code=400, detail="No previous website found. Please provide a URL in UI Testing first.")

    # Run comprehensive whole-site scan
    try:
        from ui_testing.scanners.site_scanner import scan_whole_site
        
        logger.info(f"Starting scan-now whole-site scan for {url} | org={org_id}")
        
        result = await scan_whole_site(
            url=url,
            max_pages=50,
            max_depth=3,
            scan_mode="all",
            parallel_scans=3,
            use_selenium_crawler=False,
            db=database.db,
            organization_id=str(org_id) if org_id else None
        )
        
        # Generate AI recommendations for the site scan
        try:
            from ui_testing.ai.recommendations import generate_findings_and_recommendations
            
            # Format the result for AI recommendations with complete site-wide data
            wcag_agg = result.get("wcag_aggregate", {})
            ai_input = {
                "wcag_results": {
                    "violations": wcag_agg.get("violations_summary", []),
                    "total_violations": wcag_agg.get("total_violations", 0),
                    "unique_rules_violated": wcag_agg.get("unique_rules_violated", 0),
                    "pages_with_issues": wcag_agg.get("pages_with_issues", 0),
                    "total_pages_scanned": wcag_agg.get("total_pages_scanned", 0),
                    "impact_counts": wcag_agg.get("impact_counts", {})
                },
                "security_results": result.get("security_aggregate", {}).get("primary_scan", {}),
                "_extras": {
                    "pages_scanned": result.get("summary", {}).get("pages_scanned", 0),
                    "accessibility_score": result.get("summary", {}).get("accessibility_score", 0)
                },
                "_mode": "all",
            }
            
            fr = await asyncio.to_thread(
                generate_findings_and_recommendations,
                ai_input
            )
            
            # Add findings and recommendations to result
            result["findings"] = fr.get("findings", {})
            result["recommendations"] = fr.get("recommendations", "")
            
        except Exception as e:
            logger.error(f"Failed to generate AI recommendations for scan-now: {e}")
            result["findings"] = {}
            result["recommendations"] = "AI recommendations unavailable"
        
        # Persist the result to database
        try:
            if database.db is not None:
                await database.db.ui_testing_site_results.insert_one({
                    "organization_id": org_id,
                    "user_id": getattr(user, 'id', None) or getattr(user, '_id', None),
                    "url": url,
                    "mode": "all",
                    "result": result,
                    "created_at": int(time.time())
                })
        except Exception as e:
            logger.error(f"Failed to persist scan-now site scan result: {e}")
        
        return {"message": "Whole-site scan completed", "url": url, "result": result}
        
    except Exception as e:
        logger.error(f"Scan-now whole-site scan failed: {e}")
        # Fallback to single-page scan if whole-site scan fails
        logger.info("Falling back to single-page scan...")
        result = await _run_scan_and_persist(url=url, mode=ScanMode.all, org_id=org_id, requested_by=getattr(user, 'id', None) or getattr(user, '_id', None))
        return {"message": "Scan completed (fallback to single-page)", "url": url, "result": result}


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
    
    # Store URL if provided, otherwise will use last scanned URL at execution time
    if payload.url:
        doc["url"] = _normalize_url(payload.url)
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
    from reportlab.lib import colors

    url = _normalize_url((payload.url or "").strip())
    mode = payload.mode or ScanMode.all
    res = _get_cached_scan(url, mode)
    if res is None:
        res = await scan(payload, user)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    # Header
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 50, "UI Compliance Report")
    c.setFont("Helvetica", 10)
    c.drawString(40, height - 68, f"URL: {url}")
    c.drawString(300, height - 68, f"Mode: {mode}")
    c.line(40, height - 75, width - 40, height - 75)

    # Metrics
    a11y_score = res.get("a11y_score")
    security_score = res.get("security_score")
    ssl = (res.get("security_results") or {}).get("ssllabs") or {}
    endpoints = ssl.get("endpoints") if isinstance(ssl.get("endpoints"), list) else []
    ssl_grade = (endpoints[0].get("grade") if endpoints else ssl.get("grade")) or ""
    wcag = (res.get("wcag_results") or {})
    violations = wcag.get("violations") or []
    counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0, "unknown": 0}
    for v in violations:
        imp = str(v.get("impact", "")).lower()
        if imp in counts:
            counts[imp] += 1
        else:
            counts["unknown"] += 1

    y = height - 110
    def section(title, color):
        nonlocal y
        c.setFillColor(color)
        c.rect(40, y - 18, width - 80, 20, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(48, y - 14, title)
        y -= 30
        c.setFillColor(colors.black)

    # Security section (when selected)
    if mode in (ScanMode.all, ScanMode.security):
        section("Security Summary", colors.darkgreen)
        c.setFont("Helvetica", 10)
        c.drawString(48, y, f"Security Score: {security_score if isinstance(security_score, int) else '—'}")
        y -= 14
        c.drawString(48, y, f"SSL Labs Grade: {ssl_grade or '—'}")
        y -= 18
        # Findings (top items)
        sec_findings = (res.get("findings", {}) or {}).get("security", [])
        c.setFont("Helvetica-Bold", 10)
        c.drawString(48, y, "Top Security Findings:")
        y -= 14
        c.setFont("Helvetica", 10)
        for it in sec_findings[:12]:
            line = f"- [{it.get('severity')}] {it.get('title')}"
            c.drawString(52, y, line[:110])
            y -= 12
            if y < 80:
                c.showPage(); y = height - 80

    # Accessibility section (when selected)
    if mode in (ScanMode.all, ScanMode.accessibility):
        section("Accessibility Summary", colors.darkblue)
        c.setFont("Helvetica", 10)
        c.drawString(48, y, f"Accessibility Score: {a11y_score if isinstance(a11y_score, int) else '—'}")
        y -= 14
        c.drawString(48, y, f"Violations: Crit {counts['critical']} • Serious {counts['serious']} • Moderate {counts['moderate']} • Minor {counts['minor']}")
        y -= 18
        acc_findings = (res.get("findings", {}) or {}).get("accessibility", [])
        c.setFont("Helvetica-Bold", 10)
        c.drawString(48, y, "Top Accessibility Findings:")
        y -= 14
        c.setFont("Helvetica", 10)
        for it in acc_findings[:12]:
            line = f"- [{it.get('severity')}] {it.get('title')}"
            c.drawString(52, y, line[:110])
            y -= 12
            if y < 80:
                c.showPage(); y = height - 80

    # Recommendations
    section("AI Recommendations", colors.grey)
    c.setFont("Helvetica", 10)
    rec_text = (res.get("recommendations") or "")
    for line in (rec_text.splitlines() or ["—"]):
        c.drawString(48, y, line[:110])
        y -= 12
        if y < 80:
            c.showPage(); y = height - 80
    c.showPage()
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
        # Summary sheet to mirror dashboard cards
        try:
            a11y_score = res.get("a11y_score")
            sec_score = res.get("security_score")
            ssl = (res.get("security_results") or {}).get("ssllabs") or {}
            endpoints = ssl.get("endpoints") if isinstance(ssl.get("endpoints"), list) else []
            ssl_grade = (endpoints[0].get("grade") if endpoints else ssl.get("grade")) or ""
            wcag = (res.get("wcag_results") or {})
            violations = wcag.get("violations") or []
            counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0, "unknown": 0}
            for v in violations:
                imp = str(v.get("impact", "")).lower()
                if imp in counts:
                    counts[imp] += 1
                else:
                    counts["unknown"] += 1
            import pandas as _pd
            summary_rows = []
            if mode in (ScanMode.all, ScanMode.accessibility):
                summary_rows.append({"Metric": "Accessibility Score", "Value": a11y_score})
                summary_rows.append({"Metric": "WCAG Critical", "Value": counts["critical"]})
                summary_rows.append({"Metric": "WCAG Serious", "Value": counts["serious"]})
                summary_rows.append({"Metric": "WCAG Moderate", "Value": counts["moderate"]})
                summary_rows.append({"Metric": "WCAG Minor", "Value": counts["minor"]})
            if mode in (ScanMode.all, ScanMode.security):
                summary_rows.append({"Metric": "Security Score", "Value": sec_score})
                summary_rows.append({"Metric": "SSL Labs Grade", "Value": ssl_grade})
            if summary_rows:
                _pd.DataFrame(summary_rows).to_excel(xw, index=False, sheet_name="Summary")
        except Exception:
            pass
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


# ==================== WHOLE-SITE SCANNING ENDPOINTS ====================

class SiteScanRequest(BaseModel):
    url: str
    max_pages: int = 50
    max_depth: int = 3
    scan_mode: ScanMode = ScanMode.all
    parallel_scans: int = 3
    use_selenium_crawler: bool = False
    credentials: Optional[Dict[str, str]] = None


class AuthenticatedScanRequest(BaseModel):
    url: str
    scan_mode: ScanMode = ScanMode.all
    max_pages: int = 50
    max_depth: int = 3
    parallel_scans: int = 3
    credentials: Dict[str, str]


class AuthenticationTestRequest(BaseModel):
    url: str
    credentials: Dict[str, str]


@router.post("/ui/scan-site")
async def scan_whole_site_endpoint(
    request: SiteScanRequest,
    user = Depends(get_current_user)
):
    """
    Scan an entire website by crawling and testing multiple pages.
    
    This endpoint:
    1. Discovers pages via crawling (respects robots.txt, parses sitemap.xml)
    2. Runs WCAG + Security scans on all discovered pages
    3. Aggregates results into a comprehensive site-wide report
    
    Args:
        url: Starting URL to crawl from
        max_pages: Maximum number of pages to scan (default: 50)
        max_depth: Maximum link depth to follow (default: 3)
        scan_mode: "all", "accessibility", or "security"
        parallel_scans: Number of concurrent page scans (default: 3)
        use_selenium_crawler: Use Selenium for JS-heavy sites (slower, default: False)
    
    Returns:
        {
            "summary": {...},          # Executive summary with scores and stats
            "crawl_result": {...},     # Crawl stats and discovered URLs
            "page_results": [...],     # Individual page scan results
            "wcag_aggregate": {...},   # Aggregated accessibility findings
            "security_aggregate": {...} # Aggregated security findings
        }
    """
    try:
        url = _normalize_url(request.url)
        
        # Check if authentication is requested
        if request.credentials and request.credentials.get("username") and request.credentials.get("password"):
            logger.info(
                f"Starting authenticated whole-site scan for {url} | "
                f"max_pages={request.max_pages}, max_depth={request.max_depth}, "
                f"mode={request.scan_mode}, user={request.credentials.get('username')}, org={user.organization_id}"
            )
            
            # Use authenticated site scanner
            result = await scan_authenticated_site(
                url=url,
                credentials=request.credentials,
                max_pages=request.max_pages,
                max_depth=request.max_depth,
                scan_mode=request.scan_mode.value,
                parallel_scans=request.parallel_scans,
                use_selenium_crawler=request.use_selenium_crawler,
                db=database.db,
                organization_id=str(user.organization_id) if user.organization_id else None
            )
        else:
            logger.info(
                f"Starting standard whole-site scan for {url} | "
                f"max_pages={request.max_pages}, max_depth={request.max_depth}, "
                f"mode={request.scan_mode}, org={user.organization_id}"
            )
            
            # Use standard site scanner
            from ui_testing.scanners.site_scanner import scan_whole_site
            result = await scan_whole_site(
                url=url,
                max_pages=request.max_pages,
                max_depth=request.max_depth,
                scan_mode=request.scan_mode.value,
                parallel_scans=request.parallel_scans,
                use_selenium_crawler=request.use_selenium_crawler,
                db=database.db,
                organization_id=str(user.organization_id) if user.organization_id else None
            )
        
        # Generate AI recommendations for the site scan
        try:
            from ui_testing.ai.recommendations import generate_findings_and_recommendations
            
            # Format the result for AI recommendations with complete site-wide data
            wcag_agg = result.get("wcag_aggregate", {})
            ai_input = {
                "wcag_results": {
                    "violations": wcag_agg.get("violations_summary", []),
                    "total_violations": wcag_agg.get("total_violations", 0),
                    "unique_rules_violated": wcag_agg.get("unique_rules_violated", 0),
                    "pages_with_issues": wcag_agg.get("pages_with_issues", 0),
                    "total_pages_scanned": wcag_agg.get("total_pages_scanned", 0),
                    "impact_counts": wcag_agg.get("impact_counts", {})
                },
                "security_results": result.get("security_aggregate", {}).get("primary_scan", {}),
                "_extras": {
                    "pages_scanned": result.get("summary", {}).get("pages_scanned", 0),
                    "accessibility_score": result.get("summary", {}).get("accessibility_score", 0)
                },
                "_mode": request.scan_mode.value,
            }
            
            fr = await asyncio.to_thread(
                generate_findings_and_recommendations,
                ai_input
            )
            
            # Add findings and recommendations to result
            result["findings"] = fr.get("findings", {})
            result["recommendations"] = fr.get("recommendations", "")
            
        except Exception as e:
            logger.error(f"Failed to generate AI recommendations: {e}")
            # Don't fail the entire scan if AI recommendations fail
            result["findings"] = {}
            result["recommendations"] = "AI recommendations unavailable"
        
        # Persist the result to database
        try:
            if database.db is not None:
                await database.db.ui_testing_site_results.insert_one({
                    "organization_id": user.organization_id,
                    "user_id": user.id,
                    "url": url,
                    "mode": request.scan_mode.value,
                    "result": result,
                    "created_at": int(time.time())
                })
        except Exception as e:
            logger.error(f"Failed to persist site scan result: {e}")
        
        return result
    
    except Exception as e:
        logger.exception(f"Site scan failed for {request.url}")
        raise HTTPException(status_code=500, detail=f"Site scan failed: {str(e)}")


@router.post("/ui/crawl-only")
async def crawl_website_endpoint(
    request: BaseModel,
    user = Depends(get_current_user)
):
    """
    Crawl a website to discover pages without running scans.
    Useful for previewing what pages will be scanned.
    
    Request body:
        {
            "url": "https://example.com",
            "max_pages": 50,
            "max_depth": 3,
            "use_selenium": false
        }
    
    Returns:
        {
            "urls": [...],           # List of discovered URLs
            "stats": {...},          # Crawl statistics
            "errors": [...]          # Any errors encountered
        }
    """
    try:
        from ui_testing.scanners.crawler import crawl_website
        
        data = request.dict() if hasattr(request, 'dict') else {}
        url = _normalize_url(data.get("url", ""))
        max_pages = data.get("max_pages", 50)
        max_depth = data.get("max_depth", 3)
        use_selenium = data.get("use_selenium", False)
        
        logger.info(f"Crawling {url} | max_pages={max_pages}, max_depth={max_depth}")
        
        result = await crawl_website(
            url=url,
            max_pages=max_pages,
            max_depth=max_depth,
            use_selenium=use_selenium
        )
        
        return result
    
    except Exception as e:
        logger.exception(f"Crawl failed for {request.dict().get('url')}")
        raise HTTPException(status_code=500, detail=f"Crawl failed: {str(e)}")


@router.get("/ui/site/latest")
async def get_latest_site_scan(user = Depends(get_current_user)):
    """Get the most recent whole-site scan result for the organization"""
    try:
        if database.db is None:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        doc = await database.db.ui_testing_site_results.find_one(
            {"organization_id": user.organization_id},
            sort=[("created_at", -1)]
        )
        
        if not doc:
            return {"message": "No site scans found for this organization"}
        
        # Convert ObjectId to string
        doc["_id"] = str(doc["_id"])
        
        return doc
    
    except Exception as e:
        logger.exception("Failed to fetch latest site scan")
        raise HTTPException(status_code=500, detail=f"Failed to fetch site scan: {str(e)}")


@router.get("/ui/site/history")
async def get_site_scan_history(
    limit: int = 10,
    user = Depends(get_current_user)
):
    """Get history of whole-site scans for the organization"""
    try:
        if database.db is None:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = database.db.ui_testing_site_results.find(
            {"organization_id": user.organization_id}
        ).sort("created_at", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            # Return only summary for history list (full results can be large)
            results.append({
                "_id": doc["_id"],
                "url": doc.get("url"),
                "mode": doc.get("mode"),
                "created_at": doc.get("created_at"),
                "summary": doc.get("result", {}).get("summary", {})
            })
        
        return {"results": results, "count": len(results)}
    
    except Exception as e:
        logger.exception("Failed to fetch site scan history")
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")


# ==================== AUTHENTICATION ENDPOINTS ====================

@router.post("/ui/scan-authenticated")
async def scan_authenticated(
    request: AuthenticatedScanRequest,
    user = Depends(get_current_user)
):
    """
    Scan website with authentication support for login-protected pages.
    
    This endpoint handles websites that require login credentials to access
    protected areas. It will automatically detect login pages, authenticate
    using provided credentials, and then scan the authenticated areas.
    """
    try:
        url = _normalize_url(request.url)
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
        
        if not request.credentials or not request.credentials.get("username") or not request.credentials.get("password"):
            raise HTTPException(status_code=400, detail="Username and password are required for authenticated scanning")
        
        logger.info(f"Starting authenticated scan for {url} | user={request.credentials.get('username')} | org={user.organization_id}")
        
        # Run interactive test with authentication
        interaction_result = run_interactive_test_with_auth(url, request.credentials)
        
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
        
        if request.scan_mode in (ScanMode.all, ScanMode.accessibility):
            # Use credentials if available for authenticated scans
            credentials = request.credentials if hasattr(request, 'credentials') else None
            session_cookies = None
            if interaction_result.get("session_info"):
                session_cookies = interaction_result["session_info"].get("cookies", [])
            wcag_task = asyncio.create_task(run_wcag_scan(url, credentials=credentials, session_cookies=session_cookies))
            dom_task = asyncio.to_thread(get_dom_snapshot, url)
        
        if request.scan_mode in (ScanMode.all, ScanMode.security):
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
        def ensure_dict(result: Any) -> Dict[str, Any]:
            if isinstance(result, Exception):
                logger.exception("Scan task raised an exception")
                return {"error": f"Scan failed: {str(result)}"}
            if isinstance(result, dict):
                return result
            logger.error("Scan returned unexpected type: %s", type(result))
            return {"error": f"Unexpected scan result type"}
        
        wcag_results_dict = ensure_dict(wcag_results) if wcag_results is not None else {}
        security_results_dict = ensure_dict(security_results) if security_results is not None else {}
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
                    "_mode": request.scan_mode.value,
                    "_authenticated": True
                },
            )
            findings = fr.get("findings", {}) or {}
            recommendations = fr.get("recommendations", "") or ""
        except Exception:
            logger.exception("Findings/recommendations generation failed")
            recommendations = "AI recommendations unavailable for authenticated scan."
        
        return {
            "wcag_results": wcag_results_dict,
            "security_results": security_results_dict,
            "findings": findings,
            "recommendations": recommendations,
            "authentication_required": auth_required,
            "authentication_successful": auth_successful,
            "session_used": bool(interaction_result.get("session_info"))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Authenticated scan failed for url=%s", request.url)
        raise HTTPException(status_code=500, detail=f"Authenticated scan failed: {str(e)}")


@router.post("/ui/test-authentication")
async def test_authentication(
    request: AuthenticationTestRequest,
    user = Depends(get_current_user)
):
    """
    Test authentication for a URL without running a full scan.
    
    This endpoint allows you to test if authentication works for a given URL
    and credentials before running a full authenticated scan.
    """
    try:
        url = _normalize_url(request.url)
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
        
        if not request.credentials or not request.credentials.get("username") or not request.credentials.get("password"):
            raise HTTPException(status_code=400, detail="Username and password are required")
        
        logger.info(f"Testing authentication for {url} | user={request.credentials.get('username')} | org={user.organization_id}")
        
        # Run interactive test with authentication
        auth_result = run_interactive_test_with_auth(url, request.credentials)
        
        return {
            "url": url,
            "authentication_required": auth_result.get("authentication_required", False),
            "authentication_successful": auth_result.get("authentication_successful", False),
            "login_form_detected": auth_result.get("login_form_detected", False),
            "session_info": auth_result.get("session_info", {}),
            "final_url": auth_result.get("final_url", url),
            "error": auth_result.get("error")
        }
        
    except Exception as e:
        logger.exception("Authentication test failed for url=%s", request.url)
        raise HTTPException(status_code=500, detail=f"Authentication test failed: {str(e)}")


