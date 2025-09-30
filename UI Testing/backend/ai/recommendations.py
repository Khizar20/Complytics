from typing import Any, Dict, Optional, List
import os
import json
import logging

import google.generativeai as genai

try:
    from .agents import run_agentic
except Exception:  # optional import
    run_agentic = None  # type: ignore


_MODEL = None
GOOGLE_API_KEY_FALLBACK = "AIzaSyAF5hhERrZXTudmLVJkjmTgMxPH2h5PWtI"
logger = logging.getLogger("ai.recommendations")


def configure_gemini(api_key: Optional[str]) -> None:
    global _MODEL
    key = api_key or os.getenv("GOOGLE_API_KEY") or GOOGLE_API_KEY_FALLBACK
    if not key:
        _MODEL = None
        logger.warning("Gemini not configured: no API key available")
        return
    genai.configure(api_key=key)

    generation_config = {
        "temperature": 0.3,
        "top_p": 0.9,
        "top_k": 40,
        "max_output_tokens": 1024,
    }

    safety_settings = [
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

    _MODEL = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config=generation_config,
        safety_settings=safety_settings,
    )
    logger.info("Gemini configured successfully")


def generate_recommendations(scan_results: Dict[str, Any]) -> str:
    global _MODEL
    # Agentic path when enabled
    mode = (scan_results.get("_mode") or "all").lower()
    if os.getenv("AGENTIC_MODE") == "1" and run_agentic is not None and mode == "all":
        try:
            extras = scan_results.get("_extras", {})
            dom = extras.get("dom_snapshot", "")
            interaction = extras.get("interaction_log", {})
            headers_summary = json.dumps(scan_results.get("security_results", {}))
            out = run_agentic(scan_results, dom, headers_summary, interaction)
            text = out.get("final_report_md") or ""
            if text:
                return text
        except Exception:
            logger.exception("Agentic pipeline failed; falling back to single-shot Gemini")
    if _MODEL is None:
        logger.warning("AI recommendations requested but Gemini is not configured")
        return (
            "Set GOOGLE_API_KEY to enable AI recommendations. Meanwhile, prioritize fixing Critical and Serious WCAG issues and add security headers like Content-Security-Policy, Strict-Transport-Security, X-Content-Type-Options, Referrer-Policy, and Permissions-Policy."
        )

    if mode == "accessibility":
        prompt = f"""
        You are an accessibility auditor.
        Only analyze accessibility. Ignore any security content.

        WCAG Issues: {scan_results.get('wcag_results')}

        Generate clear, actionable, human-friendly accessibility recommendations with severity levels (Critical, Major, Minor).
        Use concise bullet points. If data is missing, state assumptions.
        """
    elif mode == "security":
        prompt = f"""
        You are a security auditor.
        Only analyze security. Ignore any accessibility content.

        Security Issues: {scan_results.get('security_results')}

        Generate clear, actionable, human-friendly security recommendations with severity levels (Critical, Major, Minor).
        Use concise bullet points. If data is missing, state assumptions.
        """
    else:
        prompt = f"""
        You are an accessibility and security auditor.
        The following scan results were found on a website:

        WCAG Issues: {scan_results.get('wcag_results')}
        Security Issues: {scan_results.get('security_results')}

        Generate clear, actionable, human-friendly recommendations with severity levels (Critical, Major, Minor).
        Group items by Accessibility vs Security. Use concise bullet points. If data is missing, state assumptions.
        """

    try:
        response = _MODEL.generate_content(prompt)
        text = getattr(response, "text", "") or "No recommendations generated."
        logger.info("Generated AI recommendations (length=%d)", len(text))
        return text
    except Exception:
        logger.exception("Gemini generation failed")
        return "AI recommendations failed to generate. Check API key and network connectivity."


def _impact_to_severity(impact: Optional[str]) -> str:
    lvl = (impact or "").lower()
    if lvl in {"critical"}:
        return "Critical"
    if lvl in {"serious", "high"}:
        return "Major"
    return "Minor"


def _header_fix(header_name: str) -> str:
    h = header_name.lower()
    if h == "content-security-policy":
        return "Define a strict Content-Security-Policy (default-src 'self'; object-src 'none'; base-uri 'self')."
    if h == "strict-transport-security":
        return "Enable HSTS (Strict-Transport-Security: max-age=15552000; includeSubDomains)."
    if h == "x-content-type-options":
        return "Send X-Content-Type-Options: nosniff to prevent MIME sniffing."
    if h == "referrer-policy":
        return "Send Referrer-Policy: no-referrer or strict-origin-when-cross-origin."
    if h == "permissions-policy":
        return "Add a Permissions-Policy to disable unused powerful features."
    return f"Add or harden {header_name} response header."


def _header_severity(header_name: str) -> str:
    h = header_name.lower()
    if h in {"content-security-policy", "strict-transport-security"}:
        return "Critical"
    if h in {"x-content-type-options", "referrer-policy", "permissions-policy"}:
        return "Major"
    return "Minor"


def _safe_json_extract(text: str) -> Any:
    import json as _json
    if not text:
        return None
    try:
        return _json.loads(text)
    except Exception:
        pass
    # Try to recover JSON array/object substring
    start = None
    end = None
    for i, ch in enumerate(text):
        if ch in "[{":
            start = i
            break
    for j in range(len(text) - 1, -1, -1):
        if text[j] in "]}":
            end = j + 1
            break
    if start is not None and end is not None and end > start:
        try:
            return _json.loads(text[start:end])
        except Exception:
            return None
    return None


def generate_structured_findings(scan_bundle: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    wcag_results: Dict[str, Any] = scan_bundle.get("wcag_results", {}) or {}
    security_results: Dict[str, Any] = scan_bundle.get("security_results", {}) or {}
    extras: Dict[str, Any] = scan_bundle.get("_extras", {}) or {}
    dom_snapshot: str = extras.get("dom_snapshot", "") or ""
    interaction_log: Dict[str, Any] = extras.get("interaction_log", {}) or {}

    # Prefer agentic structured outputs when available
    if os.getenv("AGENTIC_MODE") == "1" and run_agentic is not None:
        try:
            agent_state = run_agentic(scan_bundle, dom_snapshot, json.dumps(security_results), interaction_log)
            sec_ai = _safe_json_extract(agent_state.get("security_ai", ""))
            acc_ai = _safe_json_extract(agent_state.get("accessibility_ai", ""))
            nav_ai = _safe_json_extract(agent_state.get("navigation_ai", ""))
            def _normalize(items: Any) -> List[Dict[str, Any]]:
                if isinstance(items, list):
                    out = []
                    for it in items:
                        if isinstance(it, dict):
                            out.append({
                                "title": it.get("title") or it.get("rule") or "Issue",
                                "severity": it.get("severity") or "Major",
                                "rule": it.get("rule") or "",
                                "evidence": it.get("evidence") or "",
                                "fix": it.get("fix") or "",
                            })
                    return out
                return []
            findings = {
                "security": _normalize(sec_ai),
                "accessibility": _normalize(acc_ai),
                "navigation": _normalize(nav_ai),
            }
            # If we got at least something, return
            if any(findings.values()):
                return findings
        except Exception:
            logger.exception("Agentic findings generation failed; falling back to deterministic findings")

    # Deterministic fallback: derive structured findings from scans
    findings_security: List[Dict[str, Any]] = []
    sh = (security_results.get("securityheaders") or {})
    for missing in sh.get("missing", []) or []:
        severity = _header_severity(missing)
        findings_security.append({
            "title": f"Missing {missing} header",
            "severity": severity,
            "rule": "OWASP ASVS 14.4.2",
            "evidence": f"SecurityHeaders: {missing} not present",
            "fix": _header_fix(missing),
        })
    sl = (security_results.get("ssllabs") or {})
    if (sl.get("status") or "").upper() != "READY":
        findings_security.append({
            "title": "TLS analysis not ready",
            "severity": "Major",
            "rule": "OWASP ASVS 9.1",
            "evidence": f"SSL Labs status: {sl.get('status')}",
            "fix": "Ensure TLS is properly configured; re-run SSL Labs until READY with strong ciphers.",
        })
    for ep in (sl.get("endpoints") or []):
        grade = (ep.get("grade") or "").upper()
        if grade and grade not in {"A", "A+"}:
            findings_security.append({
                "title": f"Endpoint {ep.get('ipAddress')} grade {grade}",
                "severity": "Major" if grade in {"B", "C"} else "Minor",
                "rule": "OWASP ASVS 9.1",
                "evidence": f"SSL Labs grade {grade}",
                "fix": "Harden TLS configuration (disable weak protocols/ciphers, enable forward secrecy).",
            })

    findings_accessibility: List[Dict[str, Any]] = []
    for v in (wcag_results.get("violations") or []):
        severity = _impact_to_severity(v.get("impact"))
        findings_accessibility.append({
            "title": v.get("description") or v.get("id") or "WCAG issue",
            "severity": severity,
            "rule": v.get("id") or "WCAG",
            "evidence": ", ".join([" ".join(n.get("target", [])) for n in v.get("nodes", [])])[:400],
            "fix": (v.get("help") or "See guidance") + (f" ({v.get('helpUrl')})" if v.get("helpUrl") else ""),
        })

    findings_navigation: List[Dict[str, Any]] = []
    steps = interaction_log.get("steps") or []
    # If no forms are detected, add an informational navigation finding
    try:
        meta = next((s for s in steps if s.get("action") == "forms-meta"), None)
        if meta and (meta.get("forms_count") == 0):
            findings_navigation.append({
                "title": "No forms detected on the scanned page",
                "severity": "Minor",
                "rule": "Informational",
                "evidence": "Interactive scanner found 0 <form> elements",
                "fix": "No action required unless forms are expected on this page.",
            })
    except Exception:
        pass
    for step in steps:
        if step.get("error"):
            findings_navigation.append({
                "title": f"Interaction error during {step.get('action')}",
                "severity": "Major",
                "rule": "WCAG 2.1.1 / 2.4.3",
                "evidence": step.get("error"),
                "fix": "Ensure forms and keyboard navigation work without errors; provide proper focus management.",
            })

    return {
        "security": findings_security,
        "accessibility": findings_accessibility,
        "navigation": findings_navigation,
    }


def generate_findings_and_recommendations(scan_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Return structured findings and a recommendations text.

    Output shape:
      {
        "findings": { "security": [...], "accessibility": [...], "navigation": [...] },
        "recommendations": "...markdown..."
      }
    """
    findings = generate_structured_findings(scan_bundle)

    # Reuse existing single-shot recommendations, but include hint of counts
    try:
        counts = {k: len(v) for k, v in findings.items()}
    except Exception:
        counts = {}
    annotated_bundle = dict(scan_bundle)
    annotated_bundle["_findings_counts"] = counts
    recs = generate_recommendations(annotated_bundle)
    return {"findings": findings, "recommendations": recs}


