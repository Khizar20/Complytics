from typing import Any, Dict
import logging
import os

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage


logger = logging.getLogger("ai.agents")


def _api_keys() -> list[str]:
    keys: list[str] = []
    for key in (os.getenv("GOOGLE_API_KEY1"), os.getenv("GOOGLE_API_KEY2"), os.getenv("GOOGLE_API_KEY3"), os.getenv("GOOGLE_API_KEY4")):
        if key:
            value = key.strip()
            if value and value not in keys:
                keys.append(value)
    return keys


def _invoke_llm(messages: list) -> Any:
    keys = _api_keys()
    last_error: Exception | None = None
    if not keys:
        raise RuntimeError("Gemini API key not configured (expected GOOGLE_API_KEY1 / GOOGLE_API_KEY2 / GOOGLE_API_KEY3 / GOOGLE_API_KEY4)")

    for idx, key in enumerate(keys):
        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                api_key=key,
                temperature=0.2,
                max_output_tokens=1200,
            )
            return llm.invoke(messages)
        except Exception as exc:
            last_error = exc
            logger.info("Gemini agentic invocation failed with key #%d: %s", idx + 1, exc)
            continue

    assert last_error is not None  # for type checkers
    raise last_error


def _truncate(text: str, limit: int) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit]


def security_node(state: Dict[str, Any]) -> Dict[str, Any]:
    scan = state.get("scan_results", {})
    dom = _truncate(state.get("dom_snapshot", ""), 30000)
    headers = _truncate(state.get("headers_summary", ""), 15000)

    prompt = f"""
You are a UI security analyst. Use OWASP ASVS and OWASP Top 10 guidance.
Identify UI security risks (e.g., insecure inputs, missing security headers/CSP, mixed content indicators, vulnerable JS libs, weak TLS posture).
Return a concise JSON list of items with fields: title, severity (Critical/Major/Minor), rule, evidence, fix.

Context - DOM snapshot (may be partial):\n{dom}
Context - Headers/Security summaries:\n{headers}
Existing automated findings:\n{scan}
""".strip()

    resp = _invoke_llm(
        [
            SystemMessage(content="Be precise. Map to OWASP rules where possible."),
            HumanMessage(content=prompt),
        ]
    )
    return {"security_ai": resp.content}


def accessibility_node(state: Dict[str, Any]) -> Dict[str, Any]:
    wcag = state.get("scan_results", {}).get("wcag_results", {})
    dom = _truncate(state.get("dom_snapshot", ""), 20000)

    prompt = f"""
You are an accessibility expert following WCAG 2.1+.
Augment axe-core findings with heuristic checks (alt text quality, ARIA usage, keyboard navigation, focus management, color contrast cues, form labeling).
Return a concise JSON list of items with fields: title, severity (Critical/Major/Minor), rule, evidence, fix.

axe-core results:\n{wcag}
DOM snapshot (may be partial):\n{dom}
""".strip()

    resp = _invoke_llm(
        [
            SystemMessage(content="Follow WCAG. Avoid duplicates."),
            HumanMessage(content=prompt),
        ]
    )
    return {"accessibility_ai": resp.content}


def navigation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    interaction = state.get("interaction_log", {})
    dom = _truncate(state.get("dom_snapshot", ""), 15000)
    prompt = f"""
You are a testing navigator. Review the interaction log (focus/type actions, errors) and DOM snapshot.
Identify compliance issues in forms and navigation (keyboard traps, missing labels, required indicators, insecure inputs, broken navigation).
Return JSON items: title, severity (Critical/Major/Minor), rule, evidence, fix.

Interaction log: {interaction}
DOM snapshot (may be partial):\n{dom}
""".strip()
    resp = _invoke_llm([
        SystemMessage(content="Validate against security and accessibility standards."),
        HumanMessage(content=prompt),
    ])
    return {"navigation_ai": resp.content}


def review_node(state: Dict[str, Any]) -> Dict[str, Any]:
    merged = (
        "Security findings (JSON):\n"
        + (state.get("security_ai", "") or "")
        + "\n\nAccessibility findings (JSON):\n"
        + (state.get("accessibility_ai", "") or "")
    )

    prompt = (
        "Merge, deduplicate, and prioritize findings. "
        "Output two parts: 1) Markdown action plan grouped by Security vs Accessibility with severity and fixes; "
        "2) At the end, a JSON summary with fields: items[{category, title, severity, rule, fix}]."
    )

    resp = _invoke_llm(
        [SystemMessage(content=prompt), HumanMessage(content=merged)]
    )
    return {"final_report_md": resp.content}


def build_graph():
    g = StateGraph(dict)
    g.add_node("security", security_node)
    g.add_node("accessibility", accessibility_node)
    g.add_node("navigation", navigation_node)
    g.add_node("review", review_node)

    g.set_entry_point("security")
    g.add_edge("security", "accessibility")
    g.add_edge("accessibility", "navigation")
    g.add_edge("navigation", "review")
    g.add_edge("review", END)
    return g.compile()


def run_agentic(scan_results: Dict[str, Any], dom_snapshot: str, headers_summary: str, interaction_log: Dict[str, Any] | None = None) -> Dict[str, Any]:
    graph = build_graph()
    return graph.invoke(
        {
            "scan_results": scan_results,
            "dom_snapshot": dom_snapshot,
            "headers_summary": headers_summary,
            "interaction_log": interaction_log or {},
        }
    )


