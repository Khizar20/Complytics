import asyncio
import io
import os
import time
import logging
import re
from enum import Enum
from typing import Any, Dict, Optional, List
from html import unescape

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
                
                # Create activity log for failed scheduled scan
                try:
                    if database.db is not None:
                        activity_log = {
                            'user_id': requested_by,
                            'user_email': email_to,
                            'organization_id': org_id,
                            'activity_type': 'schedule_scan',
                            'activity_label': 'Scheduled Scan Failed',
                            'description': f"Scheduled scan failed: No previous scan URL found",
                            'status': 'failed',
                            'details': {
                                'schedule_id': schedule_id,
                                'error': 'No previous scan URL found'
                            },
                            'timestamp': datetime.utcnow(),
                            'icon': '❌'
                        }
                        await database.db.activity_logs.insert_one(activity_log)
                except Exception as e:
                    logger.error(f"Error creating activity log for failed scheduled scan: {e}")
                
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
            
            # Create activity log for scheduled scan execution
            try:
                if database.db is not None:
                    summary = result.get("summary", {})
                    pages_scanned = summary.get("pages_scanned", 0)
                    a11y_score = summary.get("accessibility_score")
                    security_agg = result.get("security_aggregate", {})
                    security_primary = security_agg.get("primary_scan", {})
                    security_headers = security_primary.get("securityheaders", {})
                    security_score = security_headers.get("score") if security_headers else None
                    
                    activity_log = {
                        'user_id': requested_by,
                        'user_email': email_to,
                        'organization_id': org_id,
                        'activity_type': 'schedule_scan',
                        'activity_label': 'Scheduled Scan Executed',
                        'description': f"Executed scheduled whole-site scan on {url} - {pages_scanned} pages scanned",
                        'status': 'success',
                        'details': {
                            'schedule_id': schedule_id,
                            'url': url,
                            'scan_mode': 'all',
                            'pages_scanned': pages_scanned,
                            'accessibility_score': a11y_score,
                            'security_score': security_score,
                            'executed_at': datetime.utcnow().isoformat()
                        },
                        'timestamp': datetime.utcnow(),
                        'icon': '✅'
                    }
                    await database.db.activity_logs.insert_one(activity_log)
                    logger.info(f"Activity log created for scheduled scan execution: {schedule_id}")
            except Exception as e:
                logger.error(f"Error creating activity log for scheduled scan execution: {e}")
            
        except Exception as e:
            logger.error(f"Scheduled whole-site scan failed: {e}")
            
            # Create activity log for failed scheduled scan execution
            try:
                if database.db is not None:
                    doc = await database.db.scheduled_scans.find_one({"_id": ObjectId(schedule_id)})
                    activity_log = {
                        'user_id': doc.get("scheduled_by") if doc else requested_by,
                        'user_email': doc.get("email") if doc else email_to,
                        'organization_id': org_id,
                        'activity_type': 'schedule_scan',
                        'activity_label': 'Scheduled Scan Failed',
                        'description': f"Scheduled scan execution failed: {str(e)[:100]}",
                        'status': 'failed',
                        'details': {
                            'schedule_id': schedule_id,
                            'url': doc.get("url") if doc else url,
                            'error': str(e)[:200]
                        },
                        'timestamp': datetime.utcnow(),
                        'icon': '❌'
                    }
                    await database.db.activity_logs.insert_one(activity_log)
            except Exception as log_error:
                logger.error(f"Error creating activity log for failed scheduled scan: {log_error}")
            
            # Fallback to single-page scan if whole-site scan fails
            logger.info("Falling back to single-page scan...")
            result = await _run_scan_and_persist(url=url, mode=ScanMode.all, org_id=org_id, requested_by=requested_by)

        # Run Azure compliance analysis if snapshot exists
        azure_result = None
        try:
            import json
            import hashlib
            from routes import azure_checker
            
            # Get latest Azure snapshot for the organization
            snapshot = await database.db.azure_config_snapshots.find_one(
                {"organization_id": org_id},
                sort=[("timestamp", -1)]
            )
            
            if snapshot and snapshot.get("settings"):
                logger.info(f"Found Azure snapshot for org {org_id}, analyzing for scheduled scan")
                
                # Get user object for Azure analysis
                user_doc = await database.db.users.find_one({"_id": ObjectId(requested_by)})
                if user_doc:
                    # Create a simple user object for Azure analysis
                    user_obj = SimpleNamespace(
                        id=str(user_doc.get("_id")),
                        organization_id=org_id,
                        email=user_doc.get("email"),
                        role=user_doc.get("role", "")
                    )
                    
                    settings_text = json.dumps(snapshot.get("settings"), indent=2)
                    text = settings_text
                    # Clean text if needed (basic cleaning)
                    text = text.replace('\x00', '').strip()
                    
                    max_text_length = 60000
                    if len(text) > max_text_length:
                        logger.info(f"Snapshot text length {len(text)} exceeds limit, truncating")
                        text = text[:max_text_length]
                    
                    snapshot_id = snapshot.get("_id")
                    snapshot_timestamp = snapshot.get("timestamp")
                    snapshot_iso = snapshot_timestamp.isoformat() if isinstance(snapshot_timestamp, datetime) else str(snapshot_timestamp)
                    
                    document_name = f"Azure Config Snapshot ({snapshot_iso})"
                    document_hash = hashlib.sha256(f"{snapshot_id}-{text}".encode('utf-8')).hexdigest()
                    
                    azure_result = await azure_checker._perform_compliance_analysis(
                        text=text,
                        document_name=document_name,
                        current_user=user_obj,
                        document_hash=document_hash,
                        source_type="snapshot",
                        source_metadata={
                            "snapshot_id": str(snapshot_id),
                            "snapshot_timestamp": snapshot_iso,
                            "scheduled_scan_id": schedule_id
                        },
                        max_chunks=12
                    )
                    logger.info(f"Azure compliance analysis completed for scheduled scan")
        except Exception as azure_error:
            logger.warning(f"Azure compliance analysis failed for scheduled scan: {azure_error}")
            # Don't fail the entire scan if Azure analysis fails
            azure_result = None

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
                
                # Get security score
                security_agg = result.get("security_aggregate", {})
                security_primary = security_agg.get("primary_scan", {})
                security_headers = security_primary.get("securityheaders", {})
                security_score = security_headers.get("score") if security_headers else None
                ssl_data = security_primary.get("ssllabs", {})
                endpoints = ssl_data.get("endpoints") if isinstance(ssl_data.get("endpoints"), list) else []
                ssl_grade = (endpoints[0].get("grade") if endpoints else ssl_data.get("grade")) or "N/A"
                
                # Build Azure compliance section for email
                azure_section = ""
                if azure_result and azure_result.get("result"):
                    azure_data = azure_result.get("result", {})
                    compliance_summary = azure_data.get("compliance_summary", {})
                    overall_score = compliance_summary.get("overall_score", "N/A")
                    overall_status = compliance_summary.get("overall_status", "N/A")
                    total_gaps = compliance_summary.get("total_gaps", 0)
                    frameworks = compliance_summary.get("frameworks_analyzed", [])
                    framework_scores = compliance_summary.get("framework_scores", {})
                    
                    azure_section = f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="color: white; margin: 0 0 15px 0; font-size: 20px;">☁️ Azure Compliance Analysis</h3>
                        <div style="background: white; padding: 15px; border-radius: 6px;">
                            <p style="margin: 8px 0;"><strong>Overall Compliance Score:</strong> <span style="font-size: 18px; color: #667eea; font-weight: bold;">{overall_score}</span></p>
                            <p style="margin: 8px 0;"><strong>Compliance Status:</strong> {overall_status}</p>
                            <p style="margin: 8px 0;"><strong>Total Compliance Gaps:</strong> {total_gaps}</p>
                            <p style="margin: 8px 0;"><strong>Frameworks Analyzed:</strong> {', '.join(frameworks) if frameworks else 'N/A'}</p>
                            {f'<div style="margin-top: 10px;"><strong>Framework Scores:</strong><ul style="margin: 5px 0; padding-left: 20px;">' + ''.join([f'<li>{fw}: {score}</li>' for fw, score in framework_scores.items()]) + '</ul></div>' if framework_scores else ''}
                        </div>
                    </div>
                    """
                
                # Determine score color
                def get_score_color(score):
                    if score is None:
                        return "#666"
                    if score >= 90:
                        return "#10b981"
                    elif score >= 75:
                        return "#3b82f6"
                    elif score >= 50:
                        return "#f59e0b"
                    else:
                        return "#ef4444"
                
                subject = "Complytics: Scheduled Compliance Scan Completed"
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }}
                        .header h1 {{ margin: 0; font-size: 24px; }}
                        .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                        .section {{ background: white; padding: 20px; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                        .section h2 {{ margin: 0 0 15px 0; color: #1f2937; font-size: 18px; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; }}
                        .metric {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #e5e7eb; }}
                        .metric:last-child {{ border-bottom: none; }}
                        .metric-label {{ font-weight: 500; color: #6b7280; }}
                        .metric-value {{ font-size: 18px; font-weight: bold; }}
                        .score-badge {{ display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 16px; }}
                        .violations-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 15px; }}
                        .violation-item {{ background: #f3f4f6; padding: 12px; border-radius: 6px; text-align: center; }}
                        .violation-count {{ font-size: 24px; font-weight: bold; color: #1f2937; }}
                        .violation-label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; margin-top: 5px; }}
                        .cta {{ background: #667eea; color: white; padding: 15px 30px; border-radius: 6px; text-align: center; margin-top: 20px; }}
                        .cta a {{ color: white; text-decoration: none; font-weight: bold; }}
                        .footer {{ text-align: center; color: #9ca3af; font-size: 12px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>✅ Compliance Scan Completed</h1>
                        <p style="margin: 10px 0 0 0; opacity: 0.9;">Scheduled scan results are ready</p>
                    </div>
                    
                    <div class="content">
                        <div class="section">
                            <h2>📊 Scan Overview</h2>
                            <div class="metric">
                                <span class="metric-label">Website URL</span>
                                <span class="metric-value" style="font-size: 14px; word-break: break-all;">{url}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Scan Date</span>
                                <span class="metric-value" style="font-size: 14px;">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Pages Scanned</span>
                                <span class="metric-value">{pages_scanned}</span>
                            </div>
                        </div>
                        
                        <div class="section">
                            <h2>🎯 UI Testing Results</h2>
                            <div class="metric">
                                <span class="metric-label">Accessibility Score</span>
                                <span class="score-badge" style="background: {get_score_color(accessibility_score)}; color: white;">{accessibility_score}/100</span>
                            </div>
                            {f'<div class="metric"><span class="metric-label">Security Score</span><span class="score-badge" style="background: {get_score_color(security_score)}; color: white;">{security_score}/100</span></div>' if security_score is not None else ''}
                            {f'<div class="metric"><span class="metric-label">SSL/TLS Grade</span><span class="metric-value">{ssl_grade}</span></div>' if ssl_grade != "N/A" else ''}
                            
                            <div style="margin-top: 20px;">
                                <strong style="color: #374151;">WCAG Violations Breakdown:</strong>
                                <div class="violations-grid">
                                    <div class="violation-item">
                                        <div class="violation-count" style="color: #dc2626;">{sev_counts.get('critical', 0)}</div>
                                        <div class="violation-label">Critical</div>
                                    </div>
                                    <div class="violation-item">
                                        <div class="violation-count" style="color: #ea580c;">{sev_counts.get('serious', 0)}</div>
                                        <div class="violation-label">Serious</div>
                                    </div>
                                    <div class="violation-item">
                                        <div class="violation-count" style="color: #f59e0b;">{sev_counts.get('moderate', 0)}</div>
                                        <div class="violation-label">Moderate</div>
                                    </div>
                                    <div class="violation-item">
                                        <div class="violation-count" style="color: #3b82f6;">{sev_counts.get('minor', 0)}</div>
                                        <div class="violation-label">Minor</div>
                                    </div>
                                </div>
                                <div style="margin-top: 15px; padding: 12px; background: #f3f4f6; border-radius: 6px;">
                                    <p style="margin: 5px 0;"><strong>Total Violations:</strong> {total_violations}</p>
                                    <p style="margin: 5px 0;"><strong>Unique Issues:</strong> {unique_issues}</p>
                                </div>
                            </div>
                        </div>
                        
                        {azure_section}
                        
                        <div class="cta">
                            <a href="#">View Detailed Results in Dashboard →</a>
                        </div>
                        
                        <div class="footer">
                            <p>For detailed analysis, recommendations, and full compliance reports, please visit your Complytics dashboard.</p>
                            <p style="margin-top: 10px;">This is an automated notification from Complytics Compliance Platform.</p>
                        </div>
                    </div>
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
                
                # Get security data if available
                security_results = result.get("security_results", {})
                security_score = security_results.get("security_score")
                ssl_grade = security_results.get("ssl_grade") or "N/A"
                
                # Build Azure compliance section for email
                azure_section = ""
                if azure_result and azure_result.get("result"):
                    azure_data = azure_result.get("result", {})
                    compliance_summary = azure_data.get("compliance_summary", {})
                    overall_score = compliance_summary.get("overall_score", "N/A")
                    overall_status = compliance_summary.get("overall_status", "N/A")
                    total_gaps = compliance_summary.get("total_gaps", 0)
                    frameworks = compliance_summary.get("frameworks_analyzed", [])
                    framework_scores = compliance_summary.get("framework_scores", {})
                    
                    azure_section = f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="color: white; margin: 0 0 15px 0; font-size: 20px;">☁️ Azure Compliance Analysis</h3>
                        <div style="background: white; padding: 15px; border-radius: 6px;">
                            <p style="margin: 8px 0;"><strong>Overall Compliance Score:</strong> <span style="font-size: 18px; color: #667eea; font-weight: bold;">{overall_score}</span></p>
                            <p style="margin: 8px 0;"><strong>Compliance Status:</strong> {overall_status}</p>
                            <p style="margin: 8px 0;"><strong>Total Compliance Gaps:</strong> {total_gaps}</p>
                            <p style="margin: 8px 0;"><strong>Frameworks Analyzed:</strong> {', '.join(frameworks) if frameworks else 'N/A'}</p>
                            {f'<div style="margin-top: 10px;"><strong>Framework Scores:</strong><ul style="margin: 5px 0; padding-left: 20px;">' + ''.join([f'<li>{fw}: {score}</li>' for fw, score in framework_scores.items()]) + '</ul></div>' if framework_scores else ''}
                        </div>
                    </div>
                    """
                
                # Calculate accessibility score
                a11y_score = 100 - (sev_counts['critical'] * 25 + sev_counts['serious'] * 15 + sev_counts['moderate'] * 8 + sev_counts['minor'] * 3)
                a11y_score = max(0, min(100, a11y_score))
                
                # Determine score color
                def get_score_color(score):
                    if score is None:
                        return "#666"
                    if score >= 90:
                        return "#10b981"
                    elif score >= 75:
                        return "#3b82f6"
                    elif score >= 50:
                        return "#f59e0b"
                    else:
                        return "#ef4444"
                
                subject = "Complytics: Scheduled Compliance Scan Completed"
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }}
                        .header h1 {{ margin: 0; font-size: 24px; }}
                        .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                        .section {{ background: white; padding: 20px; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                        .section h2 {{ margin: 0 0 15px 0; color: #1f2937; font-size: 18px; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; }}
                        .metric {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #e5e7eb; }}
                        .metric:last-child {{ border-bottom: none; }}
                        .metric-label {{ font-weight: 500; color: #6b7280; }}
                        .metric-value {{ font-size: 18px; font-weight: bold; }}
                        .score-badge {{ display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 16px; }}
                        .violations-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 15px; }}
                        .violation-item {{ background: #f3f4f6; padding: 12px; border-radius: 6px; text-align: center; }}
                        .violation-count {{ font-size: 24px; font-weight: bold; color: #1f2937; }}
                        .violation-label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; margin-top: 5px; }}
                        .cta {{ background: #667eea; color: white; padding: 15px 30px; border-radius: 6px; text-align: center; margin-top: 20px; }}
                        .cta a {{ color: white; text-decoration: none; font-weight: bold; }}
                        .footer {{ text-align: center; color: #9ca3af; font-size: 12px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>✅ Compliance Scan Completed</h1>
                        <p style="margin: 10px 0 0 0; opacity: 0.9;">Scheduled scan results are ready</p>
                    </div>
                    
                    <div class="content">
                        <div class="section">
                            <h2>📊 Scan Overview</h2>
                            <div class="metric">
                                <span class="metric-label">Website URL</span>
                                <span class="metric-value" style="font-size: 14px; word-break: break-all;">{url}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Scan Date</span>
                                <span class="metric-value" style="font-size: 14px;">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</span>
                            </div>
                        </div>
                        
                        <div class="section">
                            <h2>🎯 UI Testing Results</h2>
                            <div class="metric">
                                <span class="metric-label">Accessibility Score</span>
                                <span class="score-badge" style="background: {get_score_color(a11y_score)}; color: white;">{a11y_score}/100</span>
                            </div>
                            {f'<div class="metric"><span class="metric-label">Security Score</span><span class="score-badge" style="background: {get_score_color(security_score)}; color: white;">{security_score}/100</span></div>' if security_score is not None else ''}
                            {f'<div class="metric"><span class="metric-label">SSL/TLS Grade</span><span class="metric-value">{ssl_grade}</span></div>' if ssl_grade != "N/A" else ''}
                            
                            <div style="margin-top: 20px;">
                                <strong style="color: #374151;">WCAG Violations Breakdown:</strong>
                                <div class="violations-grid">
                                    <div class="violation-item">
                                        <div class="violation-count" style="color: #dc2626;">{sev_counts['critical']}</div>
                                        <div class="violation-label">Critical</div>
                                    </div>
                                    <div class="violation-item">
                                        <div class="violation-count" style="color: #ea580c;">{sev_counts['serious']}</div>
                                        <div class="violation-label">Serious</div>
                                    </div>
                                    <div class="violation-item">
                                        <div class="violation-count" style="color: #f59e0b;">{sev_counts['moderate']}</div>
                                        <div class="violation-label">Moderate</div>
                                    </div>
                                    <div class="violation-item">
                                        <div class="violation-count" style="color: #3b82f6;">{sev_counts['minor']}</div>
                                        <div class="violation-label">Minor</div>
                                    </div>
                                </div>
                                <div style="margin-top: 15px; padding: 12px; background: #f3f4f6; border-radius: 6px;">
                                    <p style="margin: 5px 0;"><strong>Total Violations:</strong> {len(violations)}</p>
                                </div>
                            </div>
                        </div>
                        
                        {azure_section}
                        
                        <div class="cta">
                            <a href="#">View Detailed Results in Dashboard →</a>
                        </div>
                        
                        <div class="footer">
                            <p>For detailed analysis, recommendations, and full compliance reports, please visit your Complytics dashboard.</p>
                            <p style="margin-top: 10px;">This is an automated notification from Complytics Compliance Platform.</p>
                        </div>
                    </div>
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
            ssl = (s or {}).get("ssllabs") or {}
            
            # If SecurityHeaders provides a score, use it as base (0-100 scale)
            base_score = None
            if isinstance(sh.get("score"), (int, float)):
                base_score = int(sh["score"])
            
            # Calculate from missing headers if no base score
            if base_score is None:
                missing = len((sh.get("missing") or []))
                # Headers are worth 60% of total score (60 points max)
                base_score = max(0, 60 - missing * 10)  # -10 points per missing header
            
            # SSL/TLS grade contributes 40% of total score (40 points max)
            ssl_score = 0
            endpoints = ssl.get("endpoints") if isinstance(ssl.get("endpoints"), list) else []
            ssl_grade = (endpoints[0].get("grade") if endpoints else ssl.get("grade")) or ""
            
            if ssl_grade:
                # Map SSL grades to points (A+ = 40, A = 35, B = 25, C = 15, D = 5, F = 0)
                grade_map = {
                    "A+": 40,
                    "A": 35,
                    "B": 25,
                    "C": 15,
                    "D": 5,
                    "F": 0,
                    "T": 0,  # Trust issues
                    "M": 0,  # Certificate problems
                }
                ssl_score = grade_map.get(ssl_grade.upper(), 0)
            else:
                # If no SSL grade available, assume neutral (20 points)
                ssl_score = 20
            
            # Total score = headers (60%) + SSL (40%)
            total_score = base_score + ssl_score
            return max(0, min(100, total_score))
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

    # Create activity log for schedule scan creation
    try:
        if database.db is not None:
            scheduled_for_str = run_at_utc.strftime('%Y-%m-%d %H:%M:%S UTC')
            activity_log = {
                'user_id': getattr(user, 'id', None) or getattr(user, '_id', None),
                'user_email': getattr(user, 'email', None),
                'organization_id': org_id,
                'activity_type': 'schedule_scan',
                'activity_label': 'Scan Scheduled',
                'description': f"Scheduled whole-site scan for {scheduled_for_str}" + (f" on {payload.url}" if payload.url else " (using previous URL)"),
                'status': 'success',
                'details': {
                    'schedule_id': schedule_id,
                    'scheduled_for': run_ts,
                    'scheduled_for_readable': scheduled_for_str,
                    'url': payload.url if payload.url else 'previous_url',
                    'status': 'scheduled'
                },
                'timestamp': datetime.utcnow(),
                'icon': '📅'
            }
            await database.db.activity_logs.insert_one(activity_log)
            logger.info(f"Activity log created for schedule scan: {schedule_id}")
    except Exception as e:
        logger.error(f"Error creating activity log for schedule scan: {e}")

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


def _sanitize_text_for_pdf(text: str) -> str:
    """Remove HTML tags and clean text for PDF export"""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    text = unescape(text)
    # Remove markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Italic
    text = re.sub(r'`([^`]+)`', r'\1', text)  # Code
    # Remove any remaining HTML-like patterns
    text = re.sub(r'&[a-zA-Z]+;', '', text)  # HTML entities
    return text.strip()


@router.post("/ui/export/pdf")
async def export_pdf(payload: ScanRequest, user=Depends(get_current_user)) -> StreamingResponse:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from datetime import datetime
    import textwrap

    url = _normalize_url((payload.url or "").strip())
    mode = payload.mode or ScanMode.all
    
    # Try to get results from database first (whole-site scan)
    res = None
    is_site_scan = False
    
    if database.db is not None:
        # Check for whole-site scan results first (including specific URLs scans)
        site_doc = await database.db.ui_testing_site_results.find_one(
            {
                "organization_id": user.organization_id,
                "mode": mode.value
            },
            sort=[("created_at", -1)]
        )
        
        if site_doc and site_doc.get("result"):
            # Check if this is a specific URLs scan and if URL matches
            result_data = site_doc.get("result", {})
            is_specific_urls = result_data.get("specific_urls_mode", False)
            
            if is_specific_urls:
                # For specific URLs scans, check if the requested URL is in the scanned URLs
                crawl_result = result_data.get("crawl_result", {})
                scanned_urls = crawl_result.get("urls", [])
                if url in scanned_urls or (scanned_urls and url == scanned_urls[0]):
                    res = result_data
                    is_site_scan = True
                    logger.info(f"Using cached specific URLs scan results from DB for export")
            else:
                # Regular whole-site scan - check URL match
                if site_doc.get("url") == url:
                    res = result_data
                    is_site_scan = True
                    logger.info(f"Using cached whole-site scan results from DB for export")
        
        # If still no results, check for single-page scan results
        if res is None:
            single_doc = await database.db.ui_testing_results.find_one(
                {
                    "organization_id": user.organization_id,
                    "url": url,
                    "mode": mode.value
                },
                sort=[("created_at", -1)]
            )
            
            if single_doc and single_doc.get("result"):
                res = single_doc.get("result")
                logger.info(f"Using cached single-page scan results from DB for export")
    
    # Fallback to in-memory cache
    if res is None:
        res = _get_cached_scan(url, mode)
    
    # Last resort: run new scan (should rarely happen)
    # Note: Don't run scan for specific URLs mode as it requires specific_urls parameter
    if res is None:
        logger.warning(f"No cached results found for export")
        # Check if we should try a whole-site scan instead
        # For now, raise an error asking user to run scan first
        raise HTTPException(
            status_code=400, 
            detail="No scan results found. Please run a scan first before exporting."
        )
    # Extract data based on scan type (whole-site vs single-page)
    if is_site_scan:
        # Whole-site scan data structure
        summary = res.get("summary", {})
        wcag_agg = res.get("wcag_aggregate", {})
        security_agg = res.get("security_aggregate", {})
        
        a11y_score = summary.get("accessibility_score")
        pages_scanned = summary.get("pages_scanned", 0)
        pages_discovered = summary.get("pages_discovered", 0)
        
        # Security data
        security_primary = security_agg.get("primary_scan", {})
        security_score = None
        ssl_data = security_primary.get("ssllabs", {})
        endpoints = ssl_data.get("endpoints") if isinstance(ssl_data.get("endpoints"), list) else []
        ssl_grade = (endpoints[0].get("grade") if endpoints else ssl_data.get("grade")) or ""
        
        # WCAG violations
        violations_summary = wcag_agg.get("violations_summary", [])
        impact_counts = wcag_agg.get("impact_counts", {})
        counts = {
            "critical": impact_counts.get("critical", 0),
            "serious": impact_counts.get("serious", 0),
            "moderate": impact_counts.get("moderate", 0),
            "minor": impact_counts.get("minor", 0),
            "unknown": 0
        }
        
        # Security headers
        security_headers = security_primary.get("securityheaders", {})
        if security_headers:
            missing_headers = security_headers.get("missing", [])
            security_score = security_headers.get("score")
            if security_score is None:
                security_score = max(0, 100 - len(missing_headers) * 15)
    else:
        # Single-page scan data structure
        a11y_score = res.get("a11y_score")
        security_score = res.get("security_score")
        security_results = res.get("security_results") or {}
        ssl = security_results.get("ssllabs") or {}
        endpoints = ssl.get("endpoints") if isinstance(ssl.get("endpoints"), list) else []
        ssl_grade = (endpoints[0].get("grade") if endpoints else ssl.get("grade")) or ""
        wcag = (res.get("wcag_results") or {})
        violations = wcag.get("violations") or []
        violations_summary = violations[:20]  # Limit for display
        counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0, "unknown": 0}
        for v in violations:
            imp = str(v.get("impact", "")).lower()
            if imp in counts:
                counts[imp] += 1
            else:
                counts["unknown"] += 1
        pages_scanned = 1
        pages_discovered = 1
        # Security headers for single-page scan
        security_headers = security_results.get("securityheaders", {})

    # Create PDF with professional formatting
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)
    
    # Professional color scheme
    primary_color = colors.HexColor('#1e40af')  # Blue
    secondary_color = colors.HexColor('#059669')  # Green
    accent_color = colors.HexColor('#dc2626')  # Red
    warning_color = colors.HexColor('#f59e0b')  # Orange
    dark_gray = colors.HexColor('#374151')
    light_gray = colors.HexColor('#f3f4f6')
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=primary_color,
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=primary_color,
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=dark_gray,
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        spaceAfter=6,
        leading=14
    )
    
    # Build PDF content
    story = []
    
    # Title
    story.append(Paragraph(_sanitize_text_for_pdf("UI Compliance Testing Report"), title_style))
    story.append(Spacer(1, 12))
    
    # Report metadata
    # Sanitize all text before adding to table
    safe_url = _sanitize_text_for_pdf(url)
    metadata_data = [
        ['URL:', safe_url],
        ['Scan Mode:', mode.value.upper()],
        ['Scan Type:', 'Whole-Site Scan' if is_site_scan else 'Single-Page Scan'],
        ['Date:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
    ]
    
    if is_site_scan:
        metadata_data.append(['Pages Scanned:', str(pages_scanned)])
        metadata_data.append(['Pages Discovered:', str(pages_discovered)])
    
    # Sanitize all table cell values
    sanitized_metadata = []
    for row in metadata_data:
        sanitized_row = [_sanitize_text_for_pdf(str(cell)) for cell in row]
        sanitized_metadata.append(sanitized_row)
    
    metadata_table = Table(sanitized_metadata, colWidths=[2*inch, 4*inch])
    metadata_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), light_gray),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(metadata_table)
    story.append(Spacer(1, 20))
    
    # Summary metrics section
    story.append(Paragraph(_sanitize_text_for_pdf("Executive Summary"), heading_style))
    
    summary_data = []
    if mode in (ScanMode.all, ScanMode.accessibility):
        summary_data.append(['Accessibility Score', str(a11y_score) if a11y_score is not None else '—'])
        summary_data.append(['Critical Violations', str(counts['critical'])])
        summary_data.append(['Serious Violations', str(counts['serious'])])
        summary_data.append(['Moderate Violations', str(counts['moderate'])])
        summary_data.append(['Minor Violations', str(counts['minor'])])
    
    if mode in (ScanMode.all, ScanMode.security):
        summary_data.append(['Security Score', str(security_score) if security_score is not None else '—'])
        if mode == ScanMode.all or mode == ScanMode.security:
            # Calculate SSL grade fallback if needed
            if not ssl_grade or ssl_grade == 'None':
                missing_headers_count = len(security_headers.get("missing", [])) if security_headers else 0
                if missing_headers_count == 0:
                    ssl_grade = "A"
                elif missing_headers_count <= 2:
                    ssl_grade = "B"
                else:
                    ssl_grade = "C"
            summary_data.append(['SSL Grade', ssl_grade])
    
    if summary_data:
        # Sanitize all summary data
        sanitized_summary = []
        for row in summary_data:
            sanitized_row = [_sanitize_text_for_pdf(str(cell)) for cell in row]
            sanitized_summary.append(sanitized_row)
        summary_table = Table(sanitized_summary, colWidths=[3*inch, 3*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), light_gray),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, primary_color),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, light_gray]),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
    
    # Accessibility Findings
    if mode in (ScanMode.all, ScanMode.accessibility) and violations_summary:
        story.append(Paragraph(_sanitize_text_for_pdf("Accessibility Findings"), heading_style))
        
        findings_data = [['Severity', 'Rule ID', 'Description', 'Pages Affected']]
        for v in violations_summary[:15]:
            severity = v.get("impact", "unknown").upper()
            rule_id = v.get("id", "N/A")
            # Sanitize description for PDF
            raw_description = v.get("description") or ""
            clean_description = _sanitize_text_for_pdf(raw_description)
            # Truncate if too long
            description = clean_description[:80] + "..." if len(clean_description) > 80 else clean_description
            pages_affected = v.get("pages_affected", 0) if is_site_scan else 1
            
            # Sanitize all values
            findings_data.append([
                _sanitize_text_for_pdf(severity),
                _sanitize_text_for_pdf(rule_id),
                description,
                str(pages_affected)
            ])
        
        findings_table = Table(findings_data, colWidths=[1*inch, 1.2*inch, 3*inch, 0.8*inch])
        findings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_gray]),
            ('TEXTCOLOR', (0, 1), (0, -1), accent_color),  # Severity column
        ]))
        story.append(findings_table)
        story.append(Spacer(1, 20))
    
    # Security Findings
    if mode in (ScanMode.all, ScanMode.security):
        story.append(Paragraph(_sanitize_text_for_pdf("Security Findings"), heading_style))
        
        security_data = []
        if security_headers:
            missing = security_headers.get("missing", [])
            present = security_headers.get("present", [])
            
            security_data.append(['Header', 'Status'])
            for header in missing:
                security_data.append([header, 'Missing'])
            for header in present:
                security_data.append([header, 'Present'])
        
        if security_data:
            sec_table = Table(security_data, colWidths=[3*inch, 3*inch])
            sec_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), secondary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_gray]),
                ('TEXTCOLOR', (1, 1), (1, -1), accent_color),  # Status column
            ]))
            story.append(sec_table)
            story.append(Spacer(1, 20))
    
    # AI Recommendations
    rec_text = res.get("recommendations") or ""
    if rec_text:
        story.append(PageBreak())
        story.append(Paragraph(_sanitize_text_for_pdf("AI Recommendations"), heading_style))
        
        # Sanitize recommendations text first - remove all HTML
        rec_text = _sanitize_text_for_pdf(rec_text)
        
        # Process recommendations text - split by sections
        rec_lines = rec_text.split('\n')
        current_section = None
        
        for line in rec_lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 6))
                continue
            
            # Check for headings
            if line.startswith('## '):
                current_section = line[3:].strip()
                story.append(Paragraph(_sanitize_text_for_pdf(current_section), heading_style))
            elif line.startswith('### '):
                current_section = line[4:].strip()
                story.append(Paragraph(_sanitize_text_for_pdf(current_section), subheading_style))
            elif line.startswith('**') and line.endswith('**'):
                # Bold text - sanitize first, then add bold tags
                bold_text = line.replace('**', '').replace('*', '')
                bold_text = _sanitize_text_for_pdf(bold_text)
                story.append(Paragraph(f"<b>{bold_text}</b>", normal_style))
            elif line.startswith('```'):
                # Code block - skip language identifier
                continue
            elif line.startswith('---'):
                story.append(Spacer(1, 12))
            else:
                # Regular paragraph - sanitize before adding
                if line:
                    clean_line = _sanitize_text_for_pdf(line)
                    story.append(Paragraph(clean_line, normal_style))
        
        story.append(Spacer(1, 20))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=ui-testing-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.pdf"})


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
    
    # Try to get results from database first (whole-site scan)
    res = None
    is_site_scan = False
    
    if database.db is not None:
        # Check for whole-site scan results first (including specific URLs scans)
        site_doc = await database.db.ui_testing_site_results.find_one(
            {
                "organization_id": user.organization_id,
                "mode": mode.value
            },
            sort=[("created_at", -1)]
        )
        
        if site_doc and site_doc.get("result"):
            # Check if this is a specific URLs scan and if URL matches
            result_data = site_doc.get("result", {})
            is_specific_urls = result_data.get("specific_urls_mode", False)
            
            if is_specific_urls:
                # For specific URLs scans, check if the requested URL is in the scanned URLs
                crawl_result = result_data.get("crawl_result", {})
                scanned_urls = crawl_result.get("urls", [])
                if url in scanned_urls or (scanned_urls and url == scanned_urls[0]):
                    res = result_data
                    is_site_scan = True
                    logger.info(f"Using cached specific URLs scan results from DB for Excel export")
            else:
                # Regular whole-site scan - check URL match
                if site_doc.get("url") == url:
                    res = result_data
                    is_site_scan = True
                    logger.info(f"Using cached whole-site scan results from DB for Excel export")
        
        # If still no results, check for single-page scan results
        if res is None:
            single_doc = await database.db.ui_testing_results.find_one(
                {
                    "organization_id": user.organization_id,
                    "url": url,
                    "mode": mode.value
                },
                sort=[("created_at", -1)]
            )
            
            if single_doc and single_doc.get("result"):
                res = single_doc.get("result")
                logger.info(f"Using cached single-page scan results from DB for Excel export")
    
    # Fallback to in-memory cache
    if res is None:
        res = _get_cached_scan(url, mode)
    
    # Last resort: run new scan (should rarely happen)
    # Note: Don't run scan for specific URLs mode as it requires specific_urls parameter
    if res is None:
        logger.warning(f"No cached results found for Excel export")
        # Check if we should try a whole-site scan instead
        # For now, raise an error asking user to run scan first
        raise HTTPException(
            status_code=400, 
            detail="No scan results found. Please run a scan first before exporting."
        )
    # Extract data based on scan type
    if is_site_scan:
        # Whole-site scan data structure
        summary = res.get("summary", {})
        wcag_agg = res.get("wcag_aggregate", {})
        security_agg = res.get("security_aggregate", {})
        
        a11y_score = summary.get("accessibility_score")
        pages_scanned = summary.get("pages_scanned", 0)
        
        # Security data
        security_primary = security_agg.get("primary_scan", {})
        sec_score = None
        ssl_data = security_primary.get("ssllabs", {})
        endpoints = ssl_data.get("endpoints") if isinstance(ssl_data.get("endpoints"), list) else []
        ssl_grade = (endpoints[0].get("grade") if endpoints else ssl_data.get("grade")) or ""
        
        # WCAG violations
        violations_summary = wcag_agg.get("violations_summary", [])
        impact_counts = wcag_agg.get("impact_counts", {})
        counts = {
            "critical": impact_counts.get("critical", 0),
            "serious": impact_counts.get("serious", 0),
            "moderate": impact_counts.get("moderate", 0),
            "minor": impact_counts.get("minor", 0),
            "unknown": 0
        }
        
        # Security headers
        security_headers = security_primary.get("securityheaders", {})
        if security_headers:
            sec_score = security_headers.get("score")
            if sec_score is None:
                missing_headers_count = len(security_headers.get("missing", []))
                sec_score = max(0, 100 - missing_headers_count * 15)
        
        # Convert violations_summary to DataFrame format
        violations_for_df = []
        for v in violations_summary:
            violations_for_df.append({
                "id": v.get("id"),
                "impact": v.get("impact"),
                "description": v.get("description"),
                "help": v.get("help", ""),
                "pages_affected": v.get("pages_affected", 0),
                "total_instances": v.get("total_instances", 0)
            })
    else:
        # Single-page scan data structure
        a11y_score = res.get("a11y_score")
        sec_score = res.get("security_score")
        ssl = (res.get("security_results") or {}).get("ssllabs") or {}
        endpoints = ssl.get("endpoints") if isinstance(ssl.get("endpoints"), list) else []
        ssl_grade = (endpoints[0].get("grade") if endpoints else ssl.get("grade")) or ""
        wcag = (res.get("wcag_results") or {})
        violations = wcag.get("violations", [])
        violations_for_df = violations
        counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0, "unknown": 0}
        for v in violations:
            imp = str(v.get("impact", "")).lower()
            if imp in counts:
                counts[imp] += 1
            else:
                counts["unknown"] += 1
        pages_scanned = 1
        security_primary = res.get("security_results", {})
        security_headers = security_primary.get("securityheaders", {}) if security_primary else {}

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine=engine) as xw:
        # Summary sheet
        try:
            import pandas as _pd
            summary_rows = [
                {"Metric": "URL", "Value": url},
                {"Metric": "Scan Mode", "Value": mode.value.upper()},
                {"Metric": "Scan Type", "Value": "Whole-Site Scan" if is_site_scan else "Single-Page Scan"},
                {"Metric": "Pages Scanned", "Value": pages_scanned}
            ]
            
            if mode in (ScanMode.all, ScanMode.accessibility):
                summary_rows.append({"Metric": "Accessibility Score", "Value": a11y_score if a11y_score is not None else "—"})
                summary_rows.append({"Metric": "WCAG Critical", "Value": counts["critical"]})
                summary_rows.append({"Metric": "WCAG Serious", "Value": counts["serious"]})
                summary_rows.append({"Metric": "WCAG Moderate", "Value": counts["moderate"]})
                summary_rows.append({"Metric": "WCAG Minor", "Value": counts["minor"]})
            
            if mode in (ScanMode.all, ScanMode.security):
                summary_rows.append({"Metric": "Security Score", "Value": sec_score if sec_score is not None else "—"})
                # Calculate SSL grade fallback if needed
                if not ssl_grade or ssl_grade == 'None':
                    missing_headers_count = len(security_headers.get("missing", [])) if security_headers else 0
                    if missing_headers_count == 0:
                        ssl_grade = "A"
                    elif missing_headers_count <= 2:
                        ssl_grade = "B"
                    else:
                        ssl_grade = "C"
                summary_rows.append({"Metric": "SSL Labs Grade", "Value": ssl_grade})
            
            if summary_rows:
                summary_df = _pd.DataFrame(summary_rows)
                summary_df.to_excel(xw, index=False, sheet_name="Summary")
                
                # Format summary sheet if using xlsxwriter
                if engine == "xlsxwriter":
                    workbook = xw.book
                    worksheet = xw.sheets["Summary"]
                    header_format = workbook.add_format({
                        'bold': True,
                        'bg_color': '#1e40af',
                        'font_color': 'white',
                        'border': 1
                    })
                    worksheet.set_row(0, None, header_format)
        except Exception as e:
            logger.error(f"Error creating summary sheet: {e}")
            pass
        
        # WCAG Violations sheet
        if mode in (ScanMode.all, ScanMode.accessibility) and violations_for_df:
            try:
                wcag_df = pd.DataFrame(violations_for_df)
                if not wcag_df.empty:
                    wcag_df.to_excel(xw, index=False, sheet_name="WCAG Violations")
            except Exception as e:
                logger.error(f"Error creating WCAG sheet: {e}")
                pass
        
        # Security Headers sheet
        if mode in (ScanMode.all, ScanMode.security) and security_headers:
            try:
                security_data = []
                missing = security_headers.get("missing", [])
                present = security_headers.get("present", [])
                
                for header in missing:
                    security_data.append({"Header": header, "Status": "Missing"})
                for header in present:
                    security_data.append({"Header": header, "Status": "Present"})
                
                if security_data:
                    sec_df = pd.DataFrame(security_data)
                    sec_df.to_excel(xw, index=False, sheet_name="Security Headers")
            except Exception as e:
                logger.error(f"Error creating security sheet: {e}")
                pass
        
        # Recommendations sheet
        rec_text = res.get("recommendations") or ""
        if rec_text:
            try:
                # Split recommendations into sections for better readability
                rec_lines = rec_text.split('\n')
                recommendations_data = []
                current_section = "General"
                
                for line in rec_lines:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith('## '):
                        current_section = line[3:].strip()
                    elif line.startswith('### '):
                        current_section = line[4:].strip()
                    elif not line.startswith('```') and not line.startswith('---'):
                        # Clean markdown formatting
                        clean_line = line.replace('**', '').replace('*', '')
                        if clean_line:
                            recommendations_data.append({
                                "Section": current_section,
                                "Recommendation": clean_line
                            })
                
                if recommendations_data:
                    rec_df = pd.DataFrame(recommendations_data)
                    rec_df.to_excel(xw, index=False, sheet_name="Recommendations")
            except Exception as e:
                logger.error(f"Error creating recommendations sheet: {e}")
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
    specific_urls: Optional[List[str]] = None  # If provided, scan only these URLs (skip crawling)
    login_url: Optional[str] = None  # Login URL for specific URLs mode authentication
    authenticated_urls: Optional[List[str]] = None  # Authenticated page URLs to test after login (required when credentials are provided)


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
        
        # If specific URLs are provided, scan only those URLs (skip crawling)
        if request.specific_urls and len(request.specific_urls) > 0:
            logger.info(
                f"Starting specific URLs scan mode | "
                f"URLs provided: {len(request.specific_urls)}, "
                f"mode={request.scan_mode}, org={user.organization_id}"
            )
            
            # Normalize all specific URLs
            normalized_urls = []
            for u in request.specific_urls:
                normalized = _normalize_url(u.strip())
                if normalized:
                    normalized_urls.append(normalized)
            
            if not normalized_urls:
                raise HTTPException(status_code=400, detail="No valid URLs provided in specific_urls")
            
            # Limit to max_pages if more URLs provided
            if len(normalized_urls) > request.max_pages:
                logger.warning(f"Limiting {len(normalized_urls)} URLs to {request.max_pages} max_pages")
                normalized_urls = normalized_urls[:request.max_pages]
            
            # Check if authentication is requested for specific URLs
            if request.credentials and request.credentials.get("username") and request.credentials.get("password") and request.scan_mode != ScanMode.security:
                logger.info(f"Authentication enabled for specific URLs scan (user: {request.credentials.get('username')})")
                
                # Validate that authenticated URLs are provided (required for authenticated scans)
                if not request.authenticated_urls or len(request.authenticated_urls) == 0:
                    raise HTTPException(
                        status_code=400,
                        detail="Authenticated page URLs are required when authentication is enabled. Please provide at least one URL to test after login."
                    )
                
                # Validate and normalize authenticated URLs
                normalized_authenticated_urls = []
                for auth_url in request.authenticated_urls:
                    normalized = _normalize_url(auth_url)
                    if normalized:
                        normalized_authenticated_urls.append(normalized)
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid authenticated URL provided: {auth_url}. Please provide a valid URL."
                        )
                
                if len(normalized_authenticated_urls) == 0:
                    raise HTTPException(
                        status_code=400,
                        detail="No valid authenticated URLs provided. Please provide at least one valid URL to test after login."
                    )
                
                # Use AuthenticatedSiteScanOrchestrator for authenticated specific URLs scanning
                from ui_testing.scanners.authenticated_site_scanner import AuthenticatedSiteScanOrchestrator
                
                orchestrator = AuthenticatedSiteScanOrchestrator(
                    credentials=request.credentials,
                    max_pages=request.max_pages,
                    max_depth=3,  # Allow some depth for discovering authenticated pages
                    scan_mode=request.scan_mode.value,
                    parallel_scans=request.parallel_scans,
                    db=database.db,
                    organization_id=str(user.organization_id) if user.organization_id else None
                )
                
                all_page_results = []
                authenticated_urls_to_scan = []
                
                # Step 1: Determine login page(s) - use provided login_url or detect from specific URLs
                login_pages = []
                if request.login_url:
                    # Use provided login URL
                    normalized_login_url = _normalize_url(request.login_url)
                    if normalized_login_url:
                        login_pages = [normalized_login_url]
                        logger.info(f"Using provided login URL: {normalized_login_url}")
                    else:
                        logger.warning(f"Invalid login URL provided: {request.login_url}")
                else:
                    # Detect login pages from specific URLs
                    login_pages = orchestrator._find_login_pages_in_crawl({
                        "urls": normalized_urls,
                        "stats": {},
                        "start_url": url
                    })
                    if login_pages:
                        logger.info(f"Found {len(login_pages)} login page(s) in specific URLs: {login_pages}")
                
                # Step 2: Test accessibility of login pages BEFORE authentication
                if login_pages and request.scan_mode in (ScanMode.all, ScanMode.accessibility):
                    
                    # Authenticate on login pages (this also tests login page accessibility)
                    auth_success = await orchestrator._authenticate_on_login_pages(login_pages)
                    
                    if auth_success:
                        logger.info("✅ Authentication successful - discovering authenticated pages")
                        # Add login page results
                        all_page_results.extend(orchestrator.login_page_results)
                        
                        # Step 3: After authentication, use provided authenticated URLs (required)
                        # Normalize provided authenticated URLs
                        authenticated_urls_to_test = normalized_authenticated_urls
                        logger.info(f"Using {len(authenticated_urls_to_test)} provided authenticated page URL(s): {authenticated_urls_to_test}")
                        
                        # Step 4: Test authenticated pages according to selected mode
                        if authenticated_urls_to_test:
                            logger.info(f"Testing {len(authenticated_urls_to_test)} authenticated pages (mode: {request.scan_mode.value})")
                            # Set credentials and session cookies on orchestrator
                            orchestrator.credentials = request.credentials
                            orchestrator.session_cookies = orchestrator.session_cookies if hasattr(orchestrator, 'session_cookies') else None
                            
                            if request.scan_mode == ScanMode.accessibility:
                                authenticated_page_results = await orchestrator.scan_pages_accessibility_only(authenticated_urls_to_test)
                            else:  # "all" mode
                                authenticated_page_results = await orchestrator.scan_pages_accessibility_only(authenticated_urls_to_test)
                            
                            all_page_results.extend(authenticated_page_results)
                            logger.info(f"✅ Completed testing of {len(authenticated_urls_to_test)} authenticated pages")
                        
                        # Step 5: Now test the specific URLs that were provided (excluding login page)
                        # Remove login pages from the list to avoid duplicate scanning
                        specific_urls_to_test = [
                            u for u in normalized_urls if u not in login_pages
                        ]
                        
                        if specific_urls_to_test:
                            logger.info(f"Testing {len(specific_urls_to_test)} specific URLs (mode: {request.scan_mode.value})")
                            authenticated_urls_to_scan = specific_urls_to_test
                        else:
                            logger.info("No specific URLs to test (all were login pages)")
                            authenticated_urls_to_scan = []
                    else:
                        logger.warning("❌ Authentication failed - scanning provided URLs without authentication")
                        authenticated_urls_to_scan = normalized_urls
                else:
                    # No login pages detected or security mode - scan URLs normally
                    if login_pages:
                        logger.info(f"Login pages detected but security mode - scanning without authentication")
                    authenticated_urls_to_scan = normalized_urls
                
                # Step 6: Scan specific URLs (if not already scanned in Step 5)
                # Set credentials and session cookies on orchestrator for use in scan methods
                orchestrator.credentials = request.credentials
                orchestrator.session_cookies = orchestrator.session_cookies if hasattr(orchestrator, 'session_cookies') else None
                
                scan_started_at = time.time()
                if authenticated_urls_to_scan:
                    logger.info(f"Testing {len(authenticated_urls_to_scan)} specific URLs (mode: {request.scan_mode.value})")
                    if request.scan_mode == ScanMode.accessibility:
                        specific_url_results = await orchestrator.scan_pages_accessibility_only(authenticated_urls_to_scan)
                    else:
                        # For "all" mode, scan accessibility with authentication
                        specific_url_results = await orchestrator.scan_pages_accessibility_only(authenticated_urls_to_scan)
                    
                    all_page_results.extend(specific_url_results)
                    logger.info(f"✅ Completed testing of {len(authenticated_urls_to_scan)} specific URLs")
                
                # Step 4: Scan security if needed (domain-level)
                security_aggregate = {}
                if request.scan_mode in (ScanMode.all, ScanMode.security):
                    logger.info("Running domain-level security scan...")
                    security_result = await asyncio.to_thread(
                        run_security_scan,
                        normalized_urls[0] if normalized_urls else ""
                    )
                    security_aggregate = {
                        "primary_scan": security_result,
                        "variations_detected": 0,
                        "note": "Security headers are typically consistent across a domain"
                    }
                
                scan_duration_seconds = max(1, int(time.time() - scan_started_at))
                
                # Aggregate results including login page results
                wcag_aggregate = orchestrator.aggregate_wcag_results(all_page_results)
                
                # Add login page detection metadata
                if orchestrator.login_page_results:
                    login_urls = [r["url"] for r in orchestrator.login_page_results]
                    if not wcag_aggregate.get("login_page_detection"):
                        wcag_aggregate["login_page_detection"] = {
                            "total_checked": len(orchestrator.login_page_results),
                            "pages_with_login_detected": login_urls,
                            "pages_without_login_detected": []
                        }
            else:
                # No authentication - use standard SiteScanOrchestrator
                from ui_testing.scanners.site_scanner import SiteScanOrchestrator
                
                orchestrator = SiteScanOrchestrator(
                    max_pages=len(normalized_urls),
                    max_depth=0,  # No depth needed for specific URLs
                    scan_mode=request.scan_mode.value,
                    parallel_scans=request.parallel_scans,
                    db=database.db,
                    organization_id=str(user.organization_id) if user.organization_id else None
                )
                
                # Scan the specific URLs
                scan_started_at = time.time()
                if request.scan_mode == ScanMode.accessibility:
                    # Accessibility-only mode
                    page_results = await orchestrator.scan_pages_accessibility_only(normalized_urls)
                else:
                    # All mode or security mode
                    page_results = await orchestrator.scan_pages_batch(normalized_urls)
                scan_duration_seconds = max(1, int(time.time() - scan_started_at))
                
                # Aggregate results
                wcag_aggregate = orchestrator.aggregate_wcag_results(page_results)
                security_aggregate = orchestrator.aggregate_security_results(page_results)
                all_page_results = page_results
            
            # Create crawl_result-like structure for consistency
            # Use all_page_results count for authenticated scans, normalized_urls for regular scans
            pages_scanned_count = len(all_page_results) if 'all_page_results' in locals() else len(normalized_urls)
            
            crawl_result = {
                "urls": normalized_urls,
                "stats": {
                    "from_sitemap": 0,
                    "from_crawl": 0,
                    "duration_seconds": 0,
                    "total_discovered": pages_scanned_count,
                    "total_visited": pages_scanned_count
                },
                "start_url": url,
                "note": f"Specific URLs scan mode - {pages_scanned_count} pages scanned"
            }
            
            # Generate summary using all_page_results if available
            summary = orchestrator.generate_site_summary(
                crawl_result,
                all_page_results if 'all_page_results' in locals() else page_results,
                wcag_aggregate,
                security_aggregate if security_aggregate else {}
            )
            if isinstance(summary, dict):
                summary["scan_duration_seconds"] = scan_duration_seconds
                # Add authentication metadata
                if request.credentials and request.credentials.get("username"):
                    summary["authenticated"] = True
                    if 'orchestrator' in locals() and hasattr(orchestrator, 'login_page_results') and orchestrator.login_page_results:
                        summary["login_pages_scanned"] = len(orchestrator.login_page_results)
                        summary["authentication_successful"] = bool(orchestrator.authenticated_session)
            
            result = {
                "summary": summary,
                "crawl_result": crawl_result,
                "page_results": all_page_results if 'all_page_results' in locals() else page_results,
                "wcag_aggregate": wcag_aggregate,
                "security_aggregate": security_aggregate if security_aggregate else {},
                "duration_seconds": scan_duration_seconds,
                "specific_urls_mode": True
            }
            
            # Add authentication metadata to result
            if request.credentials and request.credentials.get("username"):
                result["authentication_required"] = True
                if 'orchestrator' in locals() and hasattr(orchestrator, 'authenticated_session'):
                    result["authentication_successful"] = bool(orchestrator.authenticated_session)
                    result["session_used"] = bool(orchestrator.authenticated_session)
                    if hasattr(orchestrator, 'login_page_results'):
                        result["login_page_results"] = orchestrator.login_page_results
            
            # Generate AI recommendations for specific URLs scan
            try:
                from ui_testing.ai.recommendations import generate_findings_and_recommendations
                
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
                
                result["findings"] = fr.get("findings", {})
                result["recommendations"] = fr.get("recommendations", "")
                
            except Exception as e:
                logger.error(f"Failed to generate AI recommendations: {e}")
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
                        "created_at": int(time.time()),
                        "specific_urls_mode": True
                    })
            except Exception as e:
                logger.error(f"Failed to persist site scan result: {e}")
            
            # Create activity log
            try:
                if database.db is not None:
                    summary = result.get("summary", {})
                    pages_scanned = summary.get("pages_scanned", 0)
                    a11y_score = summary.get("accessibility_score")
                    security_agg = result.get("security_aggregate", {})
                    security_primary = security_agg.get("primary_scan", {})
                    security_headers = security_primary.get("securityheaders", {})
                    security_score = security_headers.get("score") if security_headers else None
                    
                    activity_log = {
                        'user_id': user.id,
                        'user_email': getattr(user, 'email', None),
                        'organization_id': user.organization_id,
                        'activity_type': 'ui_testing',
                        'activity_label': 'UI Testing Scan (Specific Pages)',
                        'description': f"Performed {request.scan_mode.value} scan on {len(normalized_urls)} specific pages",
                        'status': 'success',
                        'details': {
                            'url': url,
                            'scan_mode': request.scan_mode.value,
                            'pages_scanned': pages_scanned,
                            'specific_urls_count': len(normalized_urls),
                            'accessibility_score': a11y_score,
                            'security_score': security_score,
                            'authenticated': bool(request.credentials and request.credentials.get("username"))
                        },
                        'timestamp': datetime.utcnow(),
                        'icon': '🔍'
                    }
                    await database.db.activity_logs.insert_one(activity_log)
                    logger.info(f"Activity log created for specific URLs scan")
            except Exception as e:
                logger.error(f"Error creating activity log: {e}")
            
            return result
        
        # Check if authentication is requested
        if request.credentials and request.credentials.get("username") and request.credentials.get("password") and request.scan_mode != ScanMode.security:
            logger.info(
                f"Starting authenticated whole-site scan for {url} | "
                f"max_pages={request.max_pages}, max_depth={request.max_depth}, "
                f"mode={request.scan_mode}, user={request.credentials.get('username')}, org={user.organization_id}"
            )
            
            # Validate that authenticated URLs are provided (required for authenticated scans)
            if not request.authenticated_urls or len(request.authenticated_urls) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Authenticated page URLs are required when authentication is enabled. Please provide at least one URL to test after login."
                )
            
            # Validate and normalize authenticated URLs
            normalized_authenticated_urls = []
            for auth_url in request.authenticated_urls:
                normalized = _normalize_url(auth_url)
                if normalized:
                    normalized_authenticated_urls.append(normalized)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid authenticated URL provided: {auth_url}. Please provide a valid URL."
                    )
            
            if len(normalized_authenticated_urls) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="No valid authenticated URLs provided. Please provide at least one valid URL to test after login."
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
                authenticated_urls=normalized_authenticated_urls,
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
        
        # Create activity log for UI testing scan
        try:
            if database.db is not None:
                summary = result.get("summary", {})
                pages_scanned = summary.get("pages_scanned", 0)
                a11y_score = summary.get("accessibility_score")
                security_agg = result.get("security_aggregate", {})
                security_primary = security_agg.get("primary_scan", {})
                security_headers = security_primary.get("securityheaders", {})
                security_score = security_headers.get("score") if security_headers else None
                
                activity_log = {
                    'user_id': user.id,
                    'user_email': getattr(user, 'email', None),
                    'organization_id': user.organization_id,
                    'activity_type': 'ui_testing',
                    'activity_label': 'UI Testing Scan',
                    'description': f"Performed {request.scan_mode.value} scan on {url} - {pages_scanned} pages scanned",
                    'status': 'success',
                    'details': {
                        'url': url,
                        'scan_mode': request.scan_mode.value,
                        'pages_scanned': pages_scanned,
                        'max_pages': request.max_pages,
                        'max_depth': request.max_depth,
                        'accessibility_score': a11y_score,
                        'security_score': security_score,
                        'authenticated': bool(request.credentials and request.credentials.get("username"))
                    },
                    'timestamp': datetime.utcnow(),
                    'icon': '🔍'
                }
                await database.db.activity_logs.insert_one(activity_log)
                logger.info(f"Activity log created for UI testing scan: {url}")
        except Exception as e:
            logger.error(f"Error creating activity log for UI testing scan: {e}")
        
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


