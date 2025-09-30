from typing import Any, Dict, Optional, List
import os
import json
import logging

import google.generativeai as genai

_MODEL = None
logger = logging.getLogger("ai.recommendations")


def configure_gemini(api_key: Optional[str]) -> None:
    global _MODEL
    key = api_key or os.getenv("GOOGLE_API_KEY")
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

    _MODEL = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config=generation_config,
    )
    logger.info("Gemini configured successfully")


def generate_recommendations(scan_results: Dict[str, Any]) -> str:
    global _MODEL
    if _MODEL is None:
        logger.warning("AI recommendations requested but Gemini is not configured")
        return (
            "Set GOOGLE_API_KEY to enable AI recommendations. Meanwhile, prioritize fixing Critical and Serious WCAG issues and add security headers like Content-Security-Policy, Strict-Transport-Security, X-Content-Type-Options, Referrer-Policy, and Permissions-Policy."
        )

    mode = (scan_results.get("_mode") or "all").lower()
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


def generate_structured_findings(scan_bundle: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    wcag_results: Dict[str, Any] = scan_bundle.get("wcag_results", {}) or {}
    security_results: Dict[str, Any] = scan_bundle.get("security_results", {}) or {}
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

    return {
        "security": findings_security,
        "accessibility": findings_accessibility,
        "navigation": [],
    }


def generate_findings_and_recommendations(scan_bundle: Dict[str, Any]) -> Dict[str, Any]:
    findings = generate_structured_findings(scan_bundle)
    try:
        counts = {k: len(v) for k, v in findings.items()}
    except Exception:
        counts = {}
    annotated_bundle = dict(scan_bundle)
    annotated_bundle["_findings_counts"] = counts
    recs = generate_recommendations(annotated_bundle)
    return {"findings": findings, "recommendations": recs}


