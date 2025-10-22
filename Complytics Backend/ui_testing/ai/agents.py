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
    """
    Build mode-specific agentic prompt with multi-agent collaboration.
    Only includes relevant agents based on scan mode.
    """
    mode = (scan_bundle.get("_mode") or "all").lower()
    
    # Get site-wide data if available
    wcag_results = scan_bundle.get("wcag_results") or {}
    total_violations = wcag_results.get("total_violations", 0)
    unique_issues = wcag_results.get("unique_rules_violated", 0)
    pages_with_issues = wcag_results.get("pages_with_issues", 0)
    total_pages = wcag_results.get("total_pages_scanned", 0)
    impact_counts = wcag_results.get("impact_counts", {})
    
    # Enhanced summaries with site-wide context
    wcag_violations = wcag_results.get("violations", [])
    wcag_summary = []
    for v in wcag_violations[:15]:
        wcag_summary.append({
            "rule": v.get("id"),
            "description": _truncate(v.get("description") or "", 200),
            "impact": v.get("impact"),
            "pages_affected": v.get("pages_affected", 0),
            "total_instances": v.get("total_instances", 0),
            "help": _truncate(v.get("help") or "", 150)
        })
    
    sec_s = _summarize_security_for_agent(scan_bundle)
    
    # Mode-specific prompt configuration
    if mode == "accessibility":
        # Accessibility-only mode: Direct recommendations
        site_context = (
            f"Site-Wide Audit Results:\n"
            f"- Total violations: {total_violations}\n"
            f"- Unique issues: {unique_issues}\n"
            f"- Pages with issues: {pages_with_issues} out of {total_pages} pages scanned\n"
            f"- Impact breakdown: Critical={impact_counts.get('critical', 0)}, Serious={impact_counts.get('serious', 0)}, "
            f"Moderate={impact_counts.get('moderate', 0)}, Minor={impact_counts.get('minor', 0)}\n\n"
        )
        
        prompt = (
            "You are an accessibility expert providing actionable WCAG recommendations.\n\n"
            f"{site_context}"
            f"Detected Issues:\n{wcag_summary}\n\n"
            "For EACH issue, provide:\n\n"
            "### [Severity] Issue Title (X pages affected)\n\n"
            "**Impact:** One sentence explaining why this matters for users with disabilities.\n\n"
            "**How to Fix:**\n\n"
            "1. First step with clear explanation. Include code example if relevant:\n"
            "```html\n"
            "<label for=\"email\">Email</label>\n"
            "<input id=\"email\" type=\"email\">\n"
            "```\n\n"
            "2. Second step with explanation and code example if needed.\n\n"
            "3. Verification: How to test the fix.\n\n"
            "---\n\n"
            "Rules:\n"
            "- Severity: [Critical], [Serious], [Moderate], or [Minor]\n"
            "- Include code snippets in ```html blocks\n"
            "- Separate each recommendation with ---\n"
            "- Focus on practical, implementable solutions\n"
            "- Be concise and clear\n"
        )
        
        return prompt
    
    elif mode == "security":
        # Security-only mode: Direct recommendations
        prompt = (
            "You are a security expert providing actionable web security recommendations.\n\n"
            f"Security Assessment Results:\n{sec_s}\n\n"
            "For EACH issue, provide:\n\n"
            "### [Severity] Issue Title\n\n"
            "**Impact:** One sentence explaining the security risk.\n\n"
            "**How to Fix:**\n\n"
            "1. First step with explanation. Include server configuration example:\n"
            "```apache\n"
            "Header set Content-Security-Policy \"default-src 'self';\"\n"
            "```\n\n"
            "2. Alternative for Nginx (if applicable):\n"
            "```nginx\n"
            "add_header Content-Security-Policy \"default-src 'self';\";\n"
            "```\n\n"
            "3. Verification: How to test the fix.\n\n"
            "---\n\n"
            "Rules:\n"
            "- Severity: [Critical], [Major], or [Minor]\n"
            "- Include configuration examples in appropriate code blocks\n"
            "- Separate each recommendation with ---\n"
            "- Reference OWASP when relevant\n"
            "- Be concise and practical\n"
        )
        
        return prompt
    
    else:  # "all" mode
        # Combined mode: Both accessibility and security recommendations
        site_context = (
            f"Audit Scope:\n"
            f"- Accessibility: {total_violations} violations across {pages_with_issues} of {total_pages} pages\n"
            f"- Impact breakdown: Critical={impact_counts.get('critical', 0)}, Serious={impact_counts.get('serious', 0)}, "
            f"Moderate={impact_counts.get('moderate', 0)}, Minor={impact_counts.get('minor', 0)}\n\n"
        )
        
        prompt = (
            "You are a compliance expert providing actionable recommendations for accessibility and security.\n\n"
            f"{site_context}"
            f"Detected WCAG Issues:\n{wcag_summary[:10]}\n\n"
            f"Security Assessment:\n{sec_s}\n\n"
            "Organize your response into two sections:\n\n"
            "## Accessibility Recommendations\n\n"
            "For each issue:\n\n"
            "### [Severity] Issue Title (X pages affected)\n\n"
            "**Impact:** One sentence about impact on users.\n\n"
            "**How to Fix:**\n\n"
            "1. Step with code example:\n"
            "```html\n"
            "<label for=\"field\">Label</label>\n"
            "```\n\n"
            "2. Another step.\n\n"
            "3. Verification: How to test.\n\n"
            "---\n\n"
            "## Security Recommendations\n\n"
            "For each issue:\n\n"
            "### [Severity] Issue Title\n\n"
            "**Impact:** One sentence about security risk.\n\n"
            "**How to Fix:**\n\n"
            "1. Step with configuration:\n"
            "```apache\n"
            "Header set X-Frame-Options \"DENY\"\n"
            "```\n\n"
            "2. Another step.\n\n"
            "3. Verification: How to test.\n\n"
            "---\n\n"
            "Rules:\n"
            "- Accessibility severity: [Critical], [Serious], [Moderate], [Minor]\n"
            "- Security severity: [Critical], [Major], [Minor]\n"
            "- Use code blocks appropriately\n"
            "- Separate recommendations with ---\n"
            "- Be practical and concise\n"
        )
        
        return prompt


