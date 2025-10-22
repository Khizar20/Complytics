from typing import Any, Dict, Optional, List, Tuple
import os
import json
import logging
import time
import hashlib
import requests

import google.generativeai as genai
try:
    from groq import Groq  # type: ignore
except Exception:
    Groq = None  # type: ignore

_MODEL = None
_GROQ: Optional[Dict[str, Any]] = None
_LAST_CALL_TS: float = 0.0
_MIN_CALL_INTERVAL_SEC: float = float(os.getenv("UI_AI_MIN_INTERVAL_SEC", "1.5"))
_UI_REC_CACHE: Dict[str, str] = {}
_UI_MAX_TOKENS: int = int(os.getenv("UI_AI_MAX_TOKENS", "8192"))
logger = logging.getLogger("ai.recommendations")


def _hash_text(text: str) -> str:
    try:
        return hashlib.md5(text.encode("utf-8")).hexdigest()
    except Exception:
        return str(abs(hash(text)))


def _safe_json_dumps(obj: Any) -> str:
    try:
        return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        try:
            return json.dumps(str(obj))
        except Exception:
            return "{}"


def _load_cache(base_dir: Optional[str]) -> None:
    # Caching disabled by request; function kept as no-op for compatibility
    return


def _save_cache() -> None:
    # Caching disabled by request; function kept as no-op for compatibility
    return


def configure_gemini(api_key: Optional[str]) -> None:
    global _MODEL
    # Caching disabled
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
        "max_output_tokens": 8192,  # Maximum for Gemini 2.0 Flash - for comprehensive site-wide recommendations
    }

    _MODEL = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config=generation_config,
    )
    logger.info("Gemini configured successfully")


def configure_ollama(base_url: Optional[str], model: Optional[str]) -> None:
    # Removed by request: Ollama is no longer used for UI testing
    return


def _ensure_groq():
    """Lazy init Groq client or HTTP config from env."""
    global _GROQ
    if _GROQ is not None:
        return
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        _GROQ = None
        return
    if Groq is not None:
        try:
            client = Groq(api_key=api_key)
            _GROQ = {"sdk": client}
            return
        except Exception as e:
            logger.warning("Groq SDK init failed, will use HTTP fallback: %s", e)
    _GROQ = {"http": True, "api_key": api_key}


def configure_huggingface(api_key: Optional[str]) -> None:
    # Removed by request: Hugging Face/DeepSeek not used anymore
    return


def _cleanup_recommendations(text: str) -> str:
    try:
        import re
        # Collapse excessive repeated aria-label tokens
        text = re.sub(r'(aria-label=\"aria-label\"\s*){3,}', 'aria-label="aria-label" ', text, flags=re.IGNORECASE)
        # Remove very long runs of the same short token
        text = re.sub(r'(\b(\w{1,20})\b\s*)(?=\1{10,})', '', text)
    except Exception:
        pass
    return text.strip()


def generate_recommendations(scan_results: Dict[str, Any]) -> Tuple[str, str, str]:
    global _MODEL
    # Agentic switch
    try:
        agentic_enabled = str(os.getenv("AGENTIC_MODE", "0")).strip() == "1"
    except Exception:
        agentic_enabled = False

    if _MODEL is None and not agentic_enabled:
        logger.warning("AI recommendations requested but Gemini is not configured")
        return (
            "Set GOOGLE_API_KEY to enable AI recommendations. Meanwhile, prioritize fixing Critical and Serious WCAG issues and add security headers like Content-Security-Policy, Strict-Transport-Security, X-Content-Type-Options, Referrer-Policy, and Permissions-Policy.",
            "none",
            "none",
        )

    mode = (scan_results.get("_mode") or "all").lower()

    # Build compact summaries for ALL providers to prevent echoing raw HTML/ARIA
    wcag = scan_results.get("wcag_results") or {}
    sec = scan_results.get("security_results") or {}

    def _truncate(text: str, n: int) -> str:
        return (text[: n - 1] + "…") if isinstance(text, str) and len(text) > n else (text or "")

    def _summarize_wcag(w: Dict[str, Any], limit: int = 12, nodes_per: int = 2) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for v in (w.get("violations") or [])[:limit]:
            nodes = []
            for n in (v.get("nodes") or [])[:nodes_per]:
                targets = " ".join(n.get("target") or [])
                nodes.append(_truncate(targets, 160))
            out.append({
                "id": v.get("id"),
                "impact": v.get("impact"),
                "description": _truncate(v.get("description") or v.get("help") or "", 220),
                "targets": nodes,
            })
        return out

    def _summarize_wcag_full(w: Dict[str, Any], nodes_example: int = 1) -> List[Dict[str, Any]]:
        """Include all violations, summarize targets to counts and example(s)."""
        out: List[Dict[str, Any]] = []
        for v in (w.get("violations") or []):
            nodes_list = v.get("nodes") or []
            example_targets: List[str] = []
            for n in nodes_list[:nodes_example]:
                example_targets.append(_truncate(" ".join(n.get("target") or []), 120))
            out.append({
                "id": v.get("id"),
                "impact": v.get("impact"),
                "description": _truncate(v.get("description") or v.get("help") or "", 180),
                "nodes": len(nodes_list),
                "example_targets": example_targets,
            })
        return out

    def _summarize_security(s: Dict[str, Any]) -> Dict[str, Any]:
        sh = (s.get("securityheaders") or {})
        ssll = (s.get("ssllabs") or {})
        endpoints = ssll.get("endpoints") if isinstance(ssll.get("endpoints"), list) else []
        grade = (endpoints[0].get("grade") if endpoints else ssll.get("grade")) or ""
        return {
            "missing_headers": (sh.get("missing") or [])[:20],
            "ssl_grade": grade,
            "notes": _truncate(str({k: v for k, v in ssll.items() if k in {"status", "criteriaVersion"}}), 180)
        }

    wcag_summary = _summarize_wcag(wcag)
    # Build summaries only for available sections
    wcag_summary = _summarize_wcag(wcag) if (wcag.get("violations") or []) else []
    sec_summary = _summarize_security(sec) if sec else {"missing_headers": [], "ssl_grade": "", "notes": ""}

    # Lightweight fingerprint (for logging only)
    fingerprint_raw = _safe_json_dumps({
        "mode": mode,
        "wcag_count": len(wcag_summary),
        "sec_missing": len(sec_summary.get("missing_headers", [])),
        "ssl_grade": sec_summary.get("ssl_grade", "")
    })

    common_rules = (
        "Do NOT repeat or echo raw HTML or ARIA attributes (e.g., aria-*, role, class). "
        "Only provide human-readable recommendations. Use concise bullet points."
    )

    if agentic_enabled:
        try:
            # Build agentic prompt and attempt using Gemini if available; else fallback to Groq/plain
            from .agents import build_agentic_prompt
            prompt = build_agentic_prompt(scan_results)
            # Cache by bundle fingerprint to avoid re-calling when inputs unchanged
            bundle_fingerprint = _hash_text(_safe_json_dumps({
                "mode": mode,
                "wcag": wcag_summary,
                "sec": sec_summary
            }))
            if bundle_fingerprint in _UI_REC_CACHE:
                text = _UI_REC_CACHE[bundle_fingerprint]
                return text, "cache", "agentic"
            if _MODEL is not None:
                response = _MODEL.generate_content(prompt, generation_config={"max_output_tokens": _UI_MAX_TOKENS})
                text = (getattr(response, "text", "") or "No recommendations generated.").strip()
                text = _cleanup_recommendations(text)
                logger.info("Recommendations provider: Gemini(agentic) model=gemini-2.0-flash (len=%d)", len(text))
                _UI_REC_CACHE[bundle_fingerprint] = text
                return text, "gemini", "gemini-2.0-flash"
            # Gemini not configured → try Groq fallback
            _ensure_groq()
            if _GROQ:
                try:
                    if _GROQ.get("sdk"):
                        comp = _GROQ["sdk"].chat.completions.create(
                            model="openai/gpt-oss-120b",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=1,
                            max_tokens=2048,
                            top_p=1,
                        )
                        text_g = (comp.choices[0].message.content or "").strip()
                    else:
                        headers = {"Authorization": f"Bearer {_GROQ['api_key']}", "Content-Type": "application/json"}
                        payload = {"model": "openai/gpt-oss-120b", "messages": [{"role": "user", "content": prompt}], "temperature": 1, "max_tokens": 2048, "top_p": 1}
                        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=60)
                        r.raise_for_status()
                        data = r.json()
                        text_g = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
                        text_g = text_g.strip()
                    if text_g:
                        text_g = _cleanup_recommendations(text_g)
                        logger.info("Recommendations provider: Groq(agentic) model=openai/gpt-oss-120b")
                        return text_g, "groq", "openai/gpt-oss-120b"
                except Exception as ge:
                    logger.info("Groq(agentic) fallback failed: %s", ge)
            # Last resort: compact deterministic baseline
            baseline = (
                "Executive Summary\n- Address missing security headers (CSP, HSTS) and fix Critical/Serious WCAG.\n\n"
                "Accessibility\n- [Major] Resolve axe violations with provided helpUrl.\n\n"
                "Security\n- [Critical] Add CSP; [Major] enable HSTS and X-Content-Type-Options.\n"
            )
            return baseline, "none", "none"
        except Exception:
            logger.exception("Agentic pipeline failed; falling back to single-shot mode")

    if mode == "accessibility":
        # Enhanced prompt for accessibility-only mode with site-wide data
        violations = wcag.get("violations", [])
        impact_counts = wcag.get("impact_counts", {})
        
        # Build detailed violation summary with pages affected
        violation_details = []
        for v in violations[:15]:  # Top 15 violations
            pages_affected = v.get("pages_affected", 0)
            total_instances = v.get("total_instances", 0)
            violation_details.append({
                "rule": v.get("id"),
                "description": v.get("description"),
                "impact": v.get("impact"),
                "pages_affected": pages_affected,
                "total_instances": total_instances,
                "help": v.get("help", "")
            })
        
        prompt = (
            "You are an accessibility expert analyzing a whole-site WCAG audit.\n\n"
            "## Site-Wide Accessibility Results:\n"
            f"- Total violations: {wcag.get('total_violations', 0)}\n"
            f"- Unique issues: {wcag.get('unique_rules_violated', 0)}\n"
            f"- Pages with issues: {wcag.get('pages_with_issues', 0)}\n"
            f"- Critical: {impact_counts.get('critical', 0)} | Serious: {impact_counts.get('serious', 0)} | "
            f"Moderate: {impact_counts.get('moderate', 0)} | Minor: {impact_counts.get('minor', 0)}\n\n"
            f"## Top Issues:\n{violation_details}\n\n"
            "## Your Task:\n"
            "Generate practical, human-friendly accessibility recommendations organized by severity.\n\n"
            "For EACH violation, provide:\n"
            "1. **Issue Title** - Clear, non-technical description\n"
            "2. **Impact** - Why this matters for users with disabilities\n"
            "3. **How to Fix** - Step-by-step implementation guide in plain language\n"
            "4. **Affected Pages** - Mention how many pages have this issue\n"
            "5. **Priority** - When to fix this\n\n"
            "Format as:\n"
            "### [Severity] Issue Title (X pages affected)\n"
            "**Impact:** ...\n"
            "**How to Fix:**\n"
            "1. Step one...\n"
            "2. Step two...\n"
            "**Priority:** ...\n\n"
            f"{common_rules}\n"
            "Focus on actionable guidance. Avoid technical jargon. Be specific about implementation."
        )
    elif mode == "security":
        prompt = (
            "You are a security auditor. Only analyze security.\n\n"
            f"Security Summary: {sec_summary}\n\n"
            "Generate clear, actionable, human-friendly security recommendations with severity levels (Critical, Major, Minor).\n"
            "For each issue, include a short 'How to fix' line with concrete steps.\n"
            f"{common_rules} If data is missing, state assumptions."
        )
    else:  # "all" mode
        # Enhanced prompt for combined mode
        violations = wcag.get("violations", [])
        impact_counts = wcag.get("impact_counts", {})
        
        # Build detailed violation summary
        violation_details = []
        for v in violations[:12]:  # Top 12 violations
            pages_affected = v.get("pages_affected", 0)
            total_instances = v.get("total_instances", 0)
            violation_details.append({
                "rule": v.get("id"),
                "description": v.get("description"),
                "impact": v.get("impact"),
                "pages_affected": pages_affected,
                "total_instances": total_instances,
                "help": v.get("help", "")
            })
        
        prompt = (
            "You are a comprehensive web compliance expert analyzing accessibility and security.\n\n"
            "## ACCESSIBILITY Results:\n"
            f"- Total violations: {wcag.get('total_violations', 0)}\n"
            f"- Unique issues: {wcag.get('unique_rules_violated', 0)}\n"
            f"- Pages with issues: {wcag.get('pages_with_issues', 0)}\n"
            f"- Critical: {impact_counts.get('critical', 0)} | Serious: {impact_counts.get('serious', 0)} | "
            f"Moderate: {impact_counts.get('moderate', 0)} | Minor: {impact_counts.get('minor', 0)}\n"
            f"Top Issues: {violation_details}\n\n"
            "## SECURITY Results:\n"
            f"{sec_summary}\n\n"
            "## Your Task:\n"
            "Generate practical recommendations organized into TWO sections:\n\n"
            "**SECTION 1: ACCESSIBILITY RECOMMENDATIONS**\n"
            "For each violation, provide:\n"
            "- Clear issue title and why it matters\n"
            "- Step-by-step fix in plain language\n"
            "- How many pages are affected\n"
            "- Priority level\n\n"
            "**SECTION 2: SECURITY RECOMMENDATIONS**\n"
            "For each security issue, provide:\n"
            "- What's missing or misconfigured\n"
            "- Why it's important\n"
            "- How to implement the fix\n"
            "- Priority level\n\n"
            f"{common_rules}\n"
            "Be specific and actionable. Focus on helping developers understand and implement fixes."
        )

    try:
        # Use Gemini only
        # Space out calls a bit, and retry on quota
        global _LAST_CALL_TS
        now = time.time()
        since = now - _LAST_CALL_TS
        if since < _MIN_CALL_INTERVAL_SEC:
            time.sleep(_MIN_CALL_INTERVAL_SEC - since)

        max_retries = 3
        base_delay = 2.0
        response = None
        final_text = ""
        # Cache by compact bundle fingerprint in non-agentic mode too
        bundle_fingerprint = _hash_text(_safe_json_dumps({
            "mode": mode,
            "wcag": wcag_summary,
            "sec": sec_summary
        }))
        if bundle_fingerprint in _UI_REC_CACHE:
            cached = _UI_REC_CACHE[bundle_fingerprint]
            return cached, "cache", "single-shot"

        for attempt in range(max_retries):
            try:
                response = _MODEL.generate_content(prompt, generation_config={"max_output_tokens": _UI_MAX_TOKENS})
                # single shot only (no continuation) to reduce usage
                text_try = getattr(response, "text", "") or ""
                final_text = text_try
                break
            except Exception as e:
                msg = str(e)
                # On rate limit or token errors, rebuild a compact prompt including ALL violations with summarized targets
                if any(k in msg for k in ["429", "ResourceExhausted", "quota", "too many tokens", "exceeds maximum"]):
                    # Build compact-but-complete summaries
                    wcag_full = _summarize_wcag_full(wcag)
                    sec_summary = _summarize_security(sec)
                    impact_counts = wcag.get("impact_counts", {})
                    
                    if mode == "accessibility":
                        prompt = (
                            "You are an accessibility auditor analyzing a whole-site WCAG audit.\n\n"
                            f"Site Stats: {wcag.get('total_violations', 0)} violations across {wcag.get('pages_with_issues', 0)} pages\n"
                            f"Impact: Critical={impact_counts.get('critical', 0)}, Serious={impact_counts.get('serious', 0)}\n"
                            f"Violations: {wcag_full}\n\n"
                            "Provide concise recommendations organized by severity.\n"
                            "For each: Title, why it matters, how to fix (step-by-step), pages affected, priority."
                        )
                    elif mode == "security":
                        prompt = (
                            "You are a security auditor.\n\n"
                            f"Security Summary: {sec_summary}\n\n"
                            "Provide concise recommendations with severity, what's wrong, how to fix, and priority."
                        )
                    else:
                        prompt = (
                            "You are a web compliance expert.\n\n"
                            f"Accessibility: {wcag.get('total_violations', 0)} violations, {wcag_full}\n"
                            f"Security: {sec_summary}\n\n"
                            "Provide concise recommendations in TWO sections:\n"
                            "1. ACCESSIBILITY: organized by severity\n"
                            "2. SECURITY: what's missing and how to fix\n"
                            "Be specific and actionable."
                        )
                    time.sleep(base_delay * (attempt + 1))
                    continue
                if attempt == max_retries - 1:
                    raise
                time.sleep(base_delay * (attempt + 1))
                continue
        _LAST_CALL_TS = time.time()
        if response is None:
            logger.warning("Gemini did not return a response after retries; attempting Groq fallback")
            # Groq fallback
            _ensure_groq()
            if _GROQ:
                try:
                    prompt_groq = prompt  # reuse compact prompt
                    if _GROQ.get("sdk"):
                        comp = _GROQ["sdk"].chat.completions.create(
                            model="openai/gpt-oss-120b",
                            messages=[{"role": "user", "content": prompt_groq}],
                            temperature=1,
                            max_tokens=2048,
                            top_p=1,
                        )
                        text_g = (comp.choices[0].message.content or "").strip()
                    else:
                        headers = {"Authorization": f"Bearer {_GROQ['api_key']}", "Content-Type": "application/json"}
                        payload = {
                            "model": "openai/gpt-oss-120b",
                            "messages": [{"role": "user", "content": prompt_groq}],
                            "temperature": 1,
                            "max_tokens": 2048,
                            "top_p": 1,
                        }
                        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=60)
                        r.raise_for_status()
                        data = r.json()
                        text_g = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
                        text_g = text_g.strip()
                    if text_g:
                        text_g = _cleanup_recommendations(text_g)
                        logger.info("Recommendations provider: Groq model=openai/gpt-oss-120b")
                        return text_g, "groq", "openai/gpt-oss-120b"
                except Exception as ge:
                    logger.info("Groq fallback failed: %s", ge)
            # Final fallback
            fallback = (
                "AI recommendations are temporarily unavailable due to rate limits or token constraints. "
                "Please try again, or reduce input size."
            )
            return fallback, "none", "none"
        text = (final_text or getattr(response, "text", "") or "No recommendations generated.")
        text = _cleanup_recommendations(text)
        logger.info("Recommendations provider: Gemini model=gemini-2.0-flash (length=%d)", len(text))
        return text, "gemini", "gemini-2.0-flash"
    except Exception:
        logger.exception("Gemini generation failed")
        # Try Groq as secondary fallback
        try:
            _ensure_groq()
            if _GROQ:
                prompt_groq = prompt
                if _GROQ.get("sdk"):
                    comp = _GROQ["sdk"].chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=[{"role": "user", "content": prompt_groq}],
                        temperature=1,
                        max_tokens=2048,
                        top_p=1,
                    )
                    text_g = (comp.choices[0].message.content or "").strip()
                else:
                    headers = {"Authorization": f"Bearer {_GROQ['api_key']}", "Content-Type": "application/json"}
                    payload = {
                        "model": "openai/gpt-oss-120b",
                        "messages": [{"role": "user", "content": prompt_groq}],
                        "temperature": 1,
                        "max_tokens": 2048,
                        "top_p": 1,
                    }
                    r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=60)
                    r.raise_for_status()
                    data = r.json()
                    text_g = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
                    text_g = text_g.strip()
                if text_g:
                    text_g = _cleanup_recommendations(text_g)
                    logger.info("Recommendations provider: Groq model=openai/gpt-oss-120b")
                    return text_g, "groq", "openai/gpt-oss-120b"
        except Exception as ge:
            logger.info("Groq fallback failed: %s", ge)
        fallback = (
            "AI recommendations are temporarily unavailable due to quota limits. "
            "Meanwhile, prioritize: 1) Fix Critical/Serious WCAG issues; 2) Add CSP, HSTS, X-Content-Type-Options, Referrer-Policy, and Permissions-Policy; 3) Resolve SSL Labs graded issues."
        )
        return fallback, "none", "none"


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
    rec_text, rec_provider, rec_model = generate_recommendations(annotated_bundle)
    return {
        "findings": findings,
        "recommendations": rec_text,
        "recommendations_provider": rec_provider,
        "recommendations_model": rec_model,
    }


