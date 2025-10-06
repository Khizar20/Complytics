from typing import Any, Dict, List


def _truncate(text: str, n: int) -> str:
    return (text[: n - 1] + "…") if isinstance(text, str) and len(text) > n else (text or "")


def _summarize_wcag_for_agent(bundle: Dict[str, Any], limit: int = 20, nodes_per: int = 1) -> List[Dict[str, Any]]:
    results = bundle.get("wcag_results") or {}
    out: List[Dict[str, Any]] = []
    for v in (results.get("violations") or [])[:limit]:
        example_targets: List[str] = []
        for n in (v.get("nodes") or [])[:nodes_per]:
            example_targets.append(_truncate(" ".join(n.get("target") or []), 120))
        out.append({
            "id": v.get("id"),
            "impact": v.get("impact"),
            "description": _truncate(v.get("description") or v.get("help") or "", 200),
            "example_targets": example_targets,
        })
    return out


def _summarize_security_for_agent(bundle: Dict[str, Any]) -> Dict[str, Any]:
    sec = bundle.get("security_results") or {}
    sh = sec.get("securityheaders") or {}
    ssll = sec.get("ssllabs") or {}
    endpoints = ssll.get("endpoints") if isinstance(ssll.get("endpoints"), list) else []
    grade = (endpoints[0].get("grade") if endpoints else ssll.get("grade")) or ""
    missing = (sh.get("missing") or [])[:20]
    return {
        "missing_headers": missing,
        "ssl_grade": grade,
        "note": _truncate(str({k: v for k, v in ssll.items() if k in {"status"}}), 160),
    }


def _summarize_navigation_for_agent(bundle: Dict[str, Any]) -> Dict[str, Any]:
    log = ((bundle.get("_extras") or {}).get("interaction_log") or {})
    steps = log.get("steps") if isinstance(log.get("steps"), list) else []
    sample = []
    for s in steps[:12]:
        action = str(s.get("action"))
        detail = s.get("field") or s.get("focused") or s.get("status") or s.get("error") or ""
        sample.append({"action": action, "detail": _truncate(str(detail), 120)})
    return {"title": _truncate(str(log.get("title") or ""), 100), "url": log.get("url"), "samples": sample}


def build_agentic_prompt(scan_bundle: Dict[str, Any]) -> str:
    wcag_s = _summarize_wcag_for_agent(scan_bundle)
    sec_s = _summarize_security_for_agent(scan_bundle)
    nav_s = _summarize_navigation_for_agent(scan_bundle)
    mode = (scan_bundle.get("_mode") or "all").lower()

    header = (
        "You are a small team of specialized compliance agents working together on a website audit.\n"
        "Your goal is to produce a single, actionable plan grouped by Accessibility and Security, with explicit 'How to fix' steps.\n"
        "Do not echo raw HTML or ARIA attributes. Be concise and precise.\n\n"
    )

    accessibility_agent = (
        "[Accessibility Agent]\n"
        "Input (axe-core summary): " + str(wcag_s) + "\n"
        "Task: Identify WCAG issues, assign severity (Critical/Major/Minor), and give a one-line How-to-fix per item.\n\n"
    )

    security_agent = (
        "[Security Agent]\n"
        "Input (headers + SSL Labs summary): " + str(sec_s) + "\n"
        "Task: Identify missing/weak controls (headers/TLS), assign severity (Critical/Major/Minor),\n"
        "and give a one-line How-to-fix per item mapped to OWASP guidance.\n\n"
    )

    navigation_agent = (
        "[Navigation Agent]\n"
        "Input (light interaction log): " + str(nav_s) + "\n"
        "Task: Note any form/keyboard issues that impact accessibility or security posture, with concise fixes.\n\n"
    )

    reviewer = (
        "[Reviewer]\n"
        "Task: Merge and de-duplicate all items into a final plan grouped by Accessibility vs Security.\n"
        "Include a short executive summary, then bullet points with severity and How-to-fix.\n"
        f"Mode: {mode}\n\n"
        "[Final Output Format]\n"
        "Executive Summary (2-4 bullets)\n"
        "Accessibility\n  - [Severity] Title — How to fix\n"
        "Security\n  - [Severity] Title — How to fix\n"
    )

    return header + accessibility_agent + security_agent + navigation_agent + reviewer


