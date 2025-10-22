# Refined Expert System - Specialized Functions for Compliance RAG
# This module contains the new refined expert system with extractive, targeted experts

import json
import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

def analyze_refined_intent(query: str, conversation_context: str = "", has_uploaded_doc: bool = False) -> Dict[str, Any]:
    """
    Refined intent analysis with sub-intents for precise routing.
    
    Returns:
        {
            "intent": str,  # GENERAL_QA_SHORT, DOC_SUMMARY, DOC_ANALYSIS_TARGETED, etc.
            "sub_intent": str,
            "framework": str,  # Detected framework or "general"
            "requires_framework": bool,
            "confidence": float,
            "reasoning": str
        }
    """
    from compliance_rag import rate_limited_generate_content
    
    try:
        prompt = f"""
Analyze this user query and classify into ONE intent. Be VERY careful about false positives.

Query: "{query}"
Context: "{conversation_context}"
Has Document: {has_uploaded_doc}

CRITICAL RULES:
1. If the core question is about personal life, food, games, entertainment, accidents, weather, etc. → classify as NON_COMPLIANCE even if compliance keywords are mentioned superficially
2. "accident" in personal context (car accident, personal injury) → NON_COMPLIANCE
3. "what game should I play" even with "according to GDPR" → NON_COMPLIANCE (user trying to game the system)
4. "what should I eat" even with compliance words → NON_COMPLIANCE
5. Only classify as SCENARIO_GUIDANCE if it's genuinely about organizational/business compliance scenarios

INTENTS:
1. GENERAL_QA_SHORT - Brief factual questions ("what is GDPR", "tell shortly", "explain briefly")
2. DOC_SUMMARY - Summarize/overview uploaded document ("tell me about this", "summarize this doc") - ONLY if Has Document: True
3. DOC_ANALYSIS_TARGETED - Analyze document WITH framework ("analyze for GDPR", "check CCPA compliance") - ONLY if Has Document: True
4. DOC_ANALYSIS_CLARIFY - Analyze but NO framework ("analyze this", "review my policy") - ONLY if Has Document: True
5. DOC_ANALYSIS_NO_UPLOAD - User asks to analyze a document but Has Document: False ("check the doc i gave you", "analyze this document", "review this file") → tell user to upload first
6. DOC_GENERATION - Generate new document ("create privacy policy", "make terms for GDPR")
7. SCENARIO_GUIDANCE - ONLY for business/organizational compliance scenarios ("how to become HIPAA compliant as a company", "guide our organization through SOC 2")
8. NON_COMPLIANCE - Personal questions, life advice, entertainment, food, games, personal accidents, etc.

EXAMPLES OF DOC_ANALYSIS_NO_UPLOAD (when Has Document: False):
- "check the doc that i just gave you" → DOC_ANALYSIS_NO_UPLOAD
- "analyze this document" → DOC_ANALYSIS_NO_UPLOAD
- "review this file" → DOC_ANALYSIS_NO_UPLOAD
- "tell me about the document i uploaded" → DOC_ANALYSIS_NO_UPLOAD
- "check this" → DOC_ANALYSIS_NO_UPLOAD (if referring to a document)

EXAMPLES OF NON_COMPLIANCE:
- "I got in an accident today what should I do" → NON_COMPLIANCE (personal accident, not data breach)
- "what video game should I play according to GDPR" → NON_COMPLIANCE (personal entertainment with fake compliance framing)
- "what should I eat today" → NON_COMPLIANCE
- "tell me a joke about GDPR" → NON_COMPLIANCE

EXAMPLES OF SCENARIO_GUIDANCE:
- "How should our company handle a data breach under GDPR?" → SCENARIO_GUIDANCE
- "Guide us through HIPAA compliance for our healthcare app" → SCENARIO_GUIDANCE
- "What steps should we take to achieve SOC 2 certification?" → SCENARIO_GUIDANCE

FRAMEWORK DETECTION:
Extract if mentioned: GDPR, CCPA, HIPAA, ISO 27001, SOC 2, NIST, PCI DSS

JSON response:
{{
  "intent": "INTENT_NAME",
  "sub_intent": "action",
  "framework": "detected_or_general",
  "requires_framework": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "brief"
}}
"""
        
        response = rate_limited_generate_content(prompt, temperature=0.1, max_tokens=250)
        
        # Clean and parse
        cleaned = response.strip()
        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            cleaned = '\n'.join([l for l in lines if not l.strip().startswith('```')])
            cleaned = cleaned.strip()
        
        if '{' in cleaned and '}' in cleaned:
            start = cleaned.find('{')
            end = cleaned.rfind('}') + 1
            cleaned = cleaned[start:end]
        
        result = json.loads(cleaned)
        logger.info(f"Refined intent: {result.get('intent')} | framework: {result.get('framework')} | requires_framework: {result.get('requires_framework')}")
        return result
        
    except Exception as e:
        logger.error(f"Refined intent analysis failed: {e}")
        return {
            "intent": "GENERAL_QA_SHORT",
            "sub_intent": "fallback",
            "framework": "general",
            "requires_framework": False,
            "confidence": 0.0,
            "reasoning": f"Fallback due to error: {str(e)}"
        }


def privacy_policy_expert_extractive(document_text: str, framework: str = "GDPR") -> Dict[str, Any]:
    """
    Extractive privacy policy expert - outputs structured findings with quotes.
    
    Returns:
        {
            "summary": str,
            "findings": [
                {
                    "finding": str,
                    "quote": str,
                    "location": str,
                    "framework_ref": str,
                    "severity": str,  # critical, high, medium, low
                    "recommendation": str
                }
            ],
            "compliant_areas": [str],
            "framework": str
        }
    """
    from compliance_rag import rate_limited_generate_content_optimized
    
    try:
        prompt = f"""
You are a {framework} compliance expert. Analyze this privacy policy EXTRACTIVELY.

DOCUMENT:
{document_text[:4000]}

INSTRUCTIONS:
1. Output ONLY issues found in the document (max 6 findings)
2. For each finding, provide:
   - Direct QUOTE from document (exact text)
   - Location (section/paragraph)
   - {framework} article/section violated
   - Severity (critical/high/medium/low)
   - One-line recommendation
3. Be extractive: cite exact sentences
4. If content is missing, say "Missing: [requirement]"
5. Avoid generic boilerplate

JSON response:
{{
  "summary": "One-line summary of compliance status",
  "findings": [
    {{
      "finding": "Issue description",
      "quote": "Exact text from document or 'Missing'",
      "location": "Section/paragraph",
      "framework_ref": "{framework} Article X",
      "severity": "critical/high/medium/low",
      "recommendation": "Specific fix"
    }}
  ],
  "compliant_areas": ["List areas that ARE compliant"],
  "framework": "{framework}"
}}
"""
        
        response = rate_limited_generate_content_optimized(prompt, temperature=0.1, max_tokens=2000)
        
        # Parse JSON
        cleaned = response.strip()
        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            cleaned = '\n'.join([l for l in lines if not l.strip().startswith('```')])
            cleaned = cleaned.strip()
        
        if '{' in cleaned and '}' in cleaned:
            start = cleaned.find('{')
            end = cleaned.rfind('}') + 1
            cleaned = cleaned[start:end]
        
        result = json.loads(cleaned)
        logger.info(f"Privacy expert: {len(result.get('findings', []))} findings for {framework}")
        return result
        
    except Exception as e:
        logger.error(f"Privacy expert failed: {e}")
        return {
            "summary": "Analysis failed",
            "findings": [],
            "compliant_areas": [],
            "framework": framework
        }


def terms_expert_extractive(document_text: str, framework: str = "general") -> Dict[str, Any]:
    """
    Extractive terms & conditions expert - outputs structured findings.
    """
    from compliance_rag import rate_limited_generate_content_optimized
    
    try:
        prompt = f"""
You are a legal compliance expert for Terms & Conditions. Analyze this document EXTRACTIVELY.

DOCUMENT:
{document_text[:4000]}

INSTRUCTIONS:
1. Check for essential ToS clauses (max 6 findings)
2. For each finding, provide:
   - Direct QUOTE or "Missing: [clause]"
   - Location (section)
   - Legal requirement
   - Severity
   - Recommendation
3. Be extractive and specific

JSON response:
{{
  "summary": "One-line ToS compliance status",
  "findings": [
    {{
      "finding": "Issue",
      "quote": "Exact text or 'Missing'",
      "location": "Section",
      "framework_ref": "Legal requirement",
      "severity": "critical/high/medium/low",
      "recommendation": "Fix"
    }}
  ],
  "compliant_areas": ["Compliant clauses"],
  "framework": "{framework}"
}}
"""
        
        response = rate_limited_generate_content_optimized(prompt, temperature=0.1, max_tokens=2000)
        
        cleaned = response.strip()
        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            cleaned = '\n'.join([l for l in lines if not l.strip().startswith('```')])
            cleaned = cleaned.strip()
        
        if '{' in cleaned and '}' in cleaned:
            start = cleaned.find('{')
            end = cleaned.rfind('}') + 1
            cleaned = cleaned[start:end]
        
        result = json.loads(cleaned)
        logger.info(f"Terms expert: {len(result.get('findings', []))} findings")
        return result
        
    except Exception as e:
        logger.error(f"Terms expert failed: {e}")
        return {
            "summary": "Analysis failed",
            "findings": [],
            "compliant_areas": [],
            "framework": framework
        }


def scenario_guidance_expert(scenario: str, framework: str = "GDPR") -> str:
    """
    Scenario guidance expert - provides step-by-step compliance guidance.
    """
    from compliance_rag import rate_limited_generate_content_optimized
    
    try:
        prompt = f"""
Provide step-by-step {framework} compliance guidance for this scenario:

SCENARIO: {scenario}

INSTRUCTIONS:
1. Max 8 steps
2. Each step: cite specific {framework} article/section
3. Be actionable and specific
4. No generic boilerplate

Format:
**Step 1: [Action]**
- {framework} Article X requires...
- Implementation: ...

**Step 2: [Action]**
...
"""
        
        response = rate_limited_generate_content_optimized(prompt, temperature=0.1, max_tokens=1500)
        logger.info(f"Scenario guidance generated for {framework}")
        return response
        
    except Exception as e:
        logger.error(f"Scenario guidance failed: {e}")
        return f"Error generating guidance: {str(e)}"


def short_qa_answer(question: str) -> str:
    """
    Short QA mode - 2-4 sentence answers for general compliance questions.
    """
    from compliance_rag import rate_limited_generate_content
    
    try:
        prompt = f"""
Answer this compliance question in 2-4 sentences. Be concise and factual.

Question: {question}

Answer (2-4 sentences only):
"""
        
        response = rate_limited_generate_content(prompt, temperature=0.1, max_tokens=200)
        logger.info("Short QA answer generated")
        return response.strip()
        
    except Exception as e:
        logger.error(f"Short QA failed: {e}")
        return "I couldn't generate an answer. Please rephrase your question."


def format_extractive_findings(analysis_result: Dict[str, Any]) -> str:
    """
    Format extractive findings into a readable response.
    """
    try:
        summary = analysis_result.get("summary", "")
        findings = analysis_result.get("findings", [])
        compliant_areas = analysis_result.get("compliant_areas", [])
        framework = analysis_result.get("framework", "")
        
        response = f"## {framework} Compliance Analysis\n\n"
        response += f"**Summary:** {summary}\n\n"
        
        if findings:
            response += "### Issues Found\n\n"
            for i, finding in enumerate(findings, 1):
                severity_emoji = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(finding.get("severity", "medium"), "⚪")
                
                response += f"{severity_emoji} **{i}. {finding.get('finding')}**\n"
                response += f"- **Quote:** \"{finding.get('quote', 'N/A')}\"\n"
                response += f"- **Location:** {finding.get('location', 'N/A')}\n"
                response += f"- **Framework:** {finding.get('framework_ref', 'N/A')}\n"
                response += f"- **Recommendation:** {finding.get('recommendation', 'N/A')}\n\n"
        
        if compliant_areas:
            response += "### ✅ Compliant Areas\n\n"
            for area in compliant_areas:
                response += f"- {area}\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Format findings failed: {e}")
        return "Error formatting analysis results."

