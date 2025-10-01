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
_OLLAMA: Optional[Dict[str, str]] = None
_GROQ: Optional[Dict[str, Any]] = None
_LAST_CALL_TS: float = 0.0
_MIN_CALL_INTERVAL_SEC: float = 1.5
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
        "max_output_tokens": 2048,
    }

    _MODEL = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config=generation_config,
    )
    logger.info("Gemini configured successfully")


def configure_ollama(base_url: Optional[str], model: Optional[str]) -> None:
    """Configure Ollama (OpenAI-compatible) endpoint.
    Defaults: base_url=http://localhost:11434/v1, model=llama3.1
    """
    global _OLLAMA
    base = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434/v1").rstrip("/")
    mdl = model or os.getenv("OLLAMA_MODEL") or "llama3.1"
    _OLLAMA = {"base_url": base, "model": mdl}
    logger.info("Ollama configured: base=%s model=%s", base, mdl)


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
    if _MODEL is None:
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

    if mode == "accessibility":
        prompt = (
            "You are an accessibility auditor. Only analyze accessibility.\n\n"
            f"WCAG Summary (top {len(wcag_summary)}): {wcag_summary}\n\n"
            "Generate clear, actionable, human-friendly accessibility recommendations with severity levels (Critical, Major, Minor).\n"
            "For each issue, include a short 'How to fix' line with concrete steps.\n"
            f"{common_rules} If data is missing, state assumptions."
        )
    elif mode == "security":
        prompt = (
            "You are a security auditor. Only analyze security.\n\n"
            f"Security Summary: {sec_summary}\n\n"
            "Generate clear, actionable, human-friendly security recommendations with severity levels (Critical, Major, Minor).\n"
            "For each issue, include a short 'How to fix' line with concrete steps.\n"
            f"{common_rules} If data is missing, state assumptions."
        )
    else:
        prompt = (
            "You are an accessibility and security auditor.\n\n"
            f"WCAG Summary (top {len(wcag_summary)}): {wcag_summary}\n"
            f"Security Summary: {sec_summary}\n\n"
            "Generate clear, actionable, human-friendly recommendations with severity levels (Critical, Major, Minor).\n"
            "Group items by Accessibility vs Security. For each issue, include a short 'How to fix' line.\n"
            f"{common_rules} If data is missing, state assumptions."
        )

    try:
        # Try Ollama first
        if _OLLAMA is not None:
            try:
                payload = {
                    "model": _OLLAMA["model"],
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 800,
                }
                r = requests.post(f"{_OLLAMA['base_url']}/chat/completions", json=payload, timeout=60)
                r.raise_for_status()
                data = r.json()
                text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
                text = _cleanup_recommendations((text or "").strip())
                if text:
                    logger.info("Recommendations provider: Ollama model=%s", _OLLAMA["model"])
                    return text, "ollama", _OLLAMA["model"]
            except requests.HTTPError as he:
                # If request too large, retry compact prompt
                if he.response is not None and he.response.status_code in (400, 413):
                    compact = "Provide concise, bullet-point recommendations only."
                    payload2 = {
                        "model": _OLLAMA["model"],
                        "messages": [{"role": "user", "content": compact}],
                        "temperature": 0.3,
                        "max_tokens": 600,
                    }
                    r2 = requests.post(f"{_OLLAMA['base_url']}/chat/completions", json=payload2, timeout=45)
                    r2.raise_for_status()
                    data2 = r2.json()
                    text2 = ((data2.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
                    text2 = _cleanup_recommendations((text2 or "").strip())
                    if text2:
                        logger.info("Recommendations provider: Ollama(compact) model=%s", _OLLAMA["model"])
                        return text2, "ollama", _OLLAMA["model"]
            except Exception as e:
                logger.info("Ollama generation failed, falling back to Gemini: %s", e)

        # Space out calls a bit, and retry on quota for Gemini
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
        for attempt in range(max_retries):
            try:
                response = _MODEL.generate_content(prompt)
                # If response is short and we still have room, ask for continuation once
                text_try = getattr(response, "text", "") or ""
                if attempt == 0 and len(text_try) < 1200:
                    cont_prompt = (
                        "Continue the previous answer. Complete any truncated sections, and include the remaining 'Security Recommendations' with 'How to fix' steps."
                    )
                    response2 = _MODEL.generate_content(cont_prompt)
                    text_try2 = getattr(response2, "text", "") or ""
                    final_text = (text_try + "\n" + text_try2).strip() if text_try2 else text_try
                else:
                    final_text = text_try
                break
            except Exception as e:
                msg = str(e)
                # On rate limit or token errors, rebuild a compact prompt including ALL violations with summarized targets
                if any(k in msg for k in ["429", "ResourceExhausted", "quota", "too many tokens", "exceeds maximum"]):
                    # Build compact-but-complete summaries
                    wcag_full = _summarize_wcag_full(wcag)
                    sec_summary = _summarize_security(sec)
                    if mode == "accessibility":
                        prompt = (
                            "You are an accessibility auditor. Only analyze accessibility.\n\n"
                            f"WCAG (all summarized): {wcag_full}\n\n"
                            "Provide concise bullet-point recommendations with severity and a 'How to fix' line per item."
                        )
                    elif mode == "security":
                        prompt = (
                            "You are a security auditor. Only analyze security.\n\n"
                            f"Security Summary: {sec_summary}\n\n"
                            "Provide concise bullet-point recommendations with severity and a 'How to fix' line per item."
                        )
                    else:
                        prompt = (
                            "You are an accessibility and security auditor.\n\n"
                            f"WCAG (all summarized): {wcag_full}\n"
                            f"Security Summary: {sec_summary}\n\n"
                            "Provide concise bullet-point recommendations grouped by Accessibility vs Security, each with a 'How to fix' line."
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


