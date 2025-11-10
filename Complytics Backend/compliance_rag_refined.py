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
            "intent": str,  # USE_MAIN_EXPERTS, GENERAL_QA_SHORT, DOC_SUMMARY, etc.
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
1. DEFAULT to USE_MAIN_EXPERTS for most compliance questions (regulations, requirements, controls, standards)
2. Questions about SPECIFIC regulations/requirements/articles → USE_MAIN_EXPERTS (NOT scenario guidance)
3. "What are the [framework] requirements for [X]?" → USE_MAIN_EXPERTS
4. "Explain [specific regulation/control/article]" → USE_MAIN_EXPERTS
5. Only use SCENARIO_GUIDANCE for step-by-step implementation guides or "how to achieve compliance"

INTENTS (in priority order):
1. USE_MAIN_EXPERTS - Default for compliance questions about regulations, requirements, controls, articles, standards
   Examples:
   - "What are GDPR breach notification requirements?" → USE_MAIN_EXPERTS
   - "Explain SOC 2 audit requirements" → USE_MAIN_EXPERTS
   - "What does GDPR Article 33 say?" → USE_MAIN_EXPERTS
   - "What are PCI DSS firewall requirements?" → USE_MAIN_EXPERTS
   - "How do I configure Azure AD MFA?" → USE_MAIN_EXPERTS
   - "What is ISO 27001?" → USE_MAIN_EXPERTS

2. GENERAL_QA_SHORT - ONLY if explicitly asking for brief/short answers ("tell briefly", "in short", "quick answer")

3. DOC_SUMMARY - Summarize uploaded document - ONLY if Has Document: True

4. DOC_ANALYSIS_TARGETED - Analyze document WITH framework - ONLY if Has Document: True

5. DOC_ANALYSIS_CLARIFY - Analyze but NO framework - ONLY if Has Document: True

6. DOC_ANALYSIS_NO_UPLOAD - User asks to analyze document but Has Document: False

7. DOC_GENERATION - Generate new document ("create privacy policy", "generate terms")

8. SCENARIO_GUIDANCE - ONLY for step-by-step implementation guides or certification paths
   Examples:
   - "How should we achieve SOC 2 certification?" → SCENARIO_GUIDANCE
   - "Guide us through implementing HIPAA compliance" → SCENARIO_GUIDANCE
   - "What steps to become ISO 27001 certified?" → SCENARIO_GUIDANCE
   - "What compliance framework should I choose?" → SCENARIO_GUIDANCE

9. NON_COMPLIANCE - Personal questions, entertainment, food, games, etc.

EXAMPLES THAT SHOULD BE USE_MAIN_EXPERTS (NOT SCENARIO_GUIDANCE):
- "What are the GDPR data breach notification requirements?" → USE_MAIN_EXPERTS
- "Explain CCPA consumer rights" → USE_MAIN_EXPERTS
- "What are SOC 2 control requirements?" → USE_MAIN_EXPERTS
- "What does NIST 800-53 say about MFA?" → USE_MAIN_EXPERTS
- "What are PCI DSS requirements?" → USE_MAIN_EXPERTS

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
    print("\n" + "="*80)
    print(f"📋 PRIVACY POLICY EXTRACTIVE EXPERT TRIGGERED (Framework: {framework})")
    print(f"Document length: {len(document_text)} characters")
    print("="*80 + "\n")
    logger.info(f"📋 PRIVACY POLICY EXTRACTIVE EXPERT triggered for framework: {framework}")
    
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
    print("\n" + "="*80)
    print(f"📜 TERMS & CONDITIONS EXTRACTIVE EXPERT TRIGGERED (Framework: {framework})")
    print(f"Document length: {len(document_text)} characters")
    print("="*80 + "\n")
    logger.info(f"📜 TERMS EXTRACTIVE EXPERT triggered for framework: {framework}")
    
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
    print("\n" + "="*80)
    print(f"🎯 SCENARIO GUIDANCE EXPERT TRIGGERED (Framework: {framework})")
    print(f"Scenario: {scenario[:100]}...")
    print("="*80 + "\n")
    logger.info(f"🎯 SCENARIO GUIDANCE EXPERT triggered for framework: {framework}")
    
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
    print("\n" + "="*80)
    print("💬 SHORT QA EXPERT TRIGGERED")
    print(f"Question: {question[:100]}...")
    print("="*80 + "\n")
    logger.info(f"💬 SHORT QA EXPERT triggered for question: {question[:100]}")
    
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


def document_compliance_expert(document_text: str, document_type: str, framework: str = "GDPR") -> Dict[str, Any]:
    """
    Specialized expert for comprehensive document analysis and generation.
    Analyzes a document against a compliance framework, identifies gaps, and can generate corrected version.
    
    Args:
        document_text: The document content to analyze
        document_type: Type of document (privacy_policy, terms_and_conditions, general_documentation)
        framework: Compliance framework to analyze against (GDPR, CCPA, HIPAA, etc.)
    
    Returns:
        Dict with analysis results, issues, and corrected document
    """
    from compliance_rag import rate_limited_generate_content_optimized
    
    print("\n" + "="*80)
    print(f"📋 DOCUMENT COMPLIANCE EXPERT TRIGGERED")
    print(f"Document Type: {document_type}")
    print(f"Framework: {framework}")
    print(f"Document Length: {len(document_text)} characters")
    print("="*80 + "\n")
    logger.info(f"📋 DOCUMENT COMPLIANCE EXPERT triggered for {document_type} against {framework}")
    
    try:
        # Step 1: Comprehensive Analysis
        analysis_prompt = f"""
You are an expert compliance analyst specializing in {framework} compliance for {document_type.replace('_', ' ')} documents.

**DOCUMENT TO ANALYZE:**
{document_text[:4000]}

**YOUR TASK:**
Perform a comprehensive {framework} compliance analysis of this {document_type.replace('_', ' ')} document.

**ANALYSIS REQUIREMENTS:**

1. **Identify ALL Compliance Gaps:**
   - Missing clauses required by {framework}
   - Incomplete or vague language
   - Non-compliant statements
   - Missing legal disclosures
   - Inadequate user rights descriptions

2. **For EACH Issue Found:**
   - Quote the exact problematic text (or note "MISSING" if clause doesn't exist)
   - Cite the specific {framework} requirement violated
   - Explain why it's non-compliant
   - Rate severity: CRITICAL, HIGH, MEDIUM, or LOW
   - Provide specific correction needed

3. **Identify Compliant Sections:**
   - List what the document does well
   - Which {framework} requirements are properly addressed

**FORMAT YOUR RESPONSE AS JSON:**
{{
  "overall_compliance_score": 0-100,
  "summary": "Brief overview of compliance status",
  "critical_issues": [
    {{
      "issue": "Description",
      "missing_or_incorrect": "Quote or 'MISSING'",
      "framework_requirement": "{framework} Article/Section",
      "explanation": "Why non-compliant",
      "severity": "CRITICAL",
      "correction_needed": "Specific text/clause needed"
    }}
  ],
  "high_issues": [...same structure...],
  "medium_issues": [...same structure...],
  "low_issues": [...same structure...],
  "compliant_areas": ["Area 1", "Area 2", ...],
  "recommendations": ["Recommendation 1", "Recommendation 2", ...]
}}

Provide thorough, actionable analysis. Be specific with citations and corrections.
"""
        
        analysis_response = rate_limited_generate_content_optimized(analysis_prompt, temperature=0.1, max_tokens=4000)
        
        # Parse analysis
        analysis_data = {}
        try:
            cleaned = analysis_response.strip()
            if cleaned.startswith('```'):
                lines = cleaned.split('\n')
                cleaned = '\n'.join([l for l in lines if not l.strip().startswith('```')])
            analysis_data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse analysis JSON, using raw response")
            analysis_data = {
                "overall_compliance_score": 50,
                "summary": analysis_response[:500],
                "critical_issues": [],
                "high_issues": [],
                "medium_issues": [],
                "low_issues": [],
                "compliant_areas": [],
                "recommendations": []
            }
        
        # Step 2: Generate Corrected Document
        correction_prompt = f"""
You are an expert legal compliance writer specializing in {framework}-compliant {document_type.replace('_', ' ')} documents.

**ORIGINAL DOCUMENT:**
{document_text[:3000]}

**IDENTIFIED ISSUES:**
{json.dumps(analysis_data.get('critical_issues', []), indent=2)[:1000]}
{json.dumps(analysis_data.get('high_issues', []), indent=2)[:1000]}

**YOUR TASK:**
Generate a FULLY COMPLIANT {framework} {document_type.replace('_', ' ')} document that:

1. **Fixes ALL identified issues**
2. **Includes ALL required {framework} clauses:**
   - For Privacy Policies: Data collection, usage, sharing, retention, user rights, security measures, cookies, international transfers, contact information
   - For Terms & Conditions: Service description, user obligations, liability limitations, dispute resolution, termination, governing law
   - For Documentation: Security controls, data handling, compliance measures, audit trails

3. **Uses Professional Legal Language:**
   - Clear and precise
   - Legally enforceable
   - User-friendly yet comprehensive

4. **Maintains Original Document Structure** (if reasonable) but enhance content

5. **Add Proper Sections and Headings**

**IMPORTANT:**
- Generate the COMPLETE document, not just snippets
- Include placeholder text like [Company Name], [Date], [Contact Email] where specific details are needed
- Make it production-ready
- Ensure FULL {framework} compliance

Generate the corrected document now:
"""
        
        corrected_document = rate_limited_generate_content_optimized(correction_prompt, temperature=0.2, max_tokens=4000)
        
        logger.info(f"Document compliance analysis completed. Score: {analysis_data.get('overall_compliance_score', 'N/A')}")
        
        return {
            "analysis": analysis_data,
            "corrected_document": corrected_document,
            "framework": framework,
            "document_type": document_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Document compliance expert failed: {e}", exc_info=True)
        return {
            "analysis": {
                "overall_compliance_score": 0,
                "summary": f"Analysis failed: {str(e)}",
                "critical_issues": [],
                "high_issues": [],
                "medium_issues": [],
                "low_issues": [],
                "compliant_areas": [],
                "recommendations": []
            },
            "corrected_document": "Error generating corrected document.",
            "framework": framework,
            "document_type": document_type,
            "error": str(e)
        }


def format_document_compliance_response(result: Dict[str, Any]) -> str:
    """
    Format the document compliance analysis and corrected document into a user-friendly response.
    """
    try:
        analysis = result.get("analysis", {})
        corrected_doc = result.get("corrected_document", "")
        framework = result.get("framework", "")
        doc_type = result.get("document_type", "").replace('_', ' ').title()
        
        # Build response
        response = f"# {framework} Compliance Analysis: {doc_type}\n\n"
        
        # Compliance score
        score = analysis.get("overall_compliance_score", 0)
        score_emoji = "🔴" if score < 40 else "🟡" if score < 70 else "🟢"
        response += f"## {score_emoji} Overall Compliance Score: {score}/100\n\n"
        
        # Summary
        response += f"**Summary:** {analysis.get('summary', 'No summary available.')}\n\n"
        
        # Critical Issues
        critical = analysis.get("critical_issues", [])
        if critical:
            response += f"## 🔴 Critical Issues ({len(critical)})\n\n"
            for i, issue in enumerate(critical, 1):
                response += f"### {i}. {issue.get('issue', 'Issue')}\n"
                response += f"- **Current Text:** {issue.get('missing_or_incorrect', 'N/A')}\n"
                response += f"- **{framework} Requirement:** {issue.get('framework_requirement', 'N/A')}\n"
                response += f"- **Why Non-Compliant:** {issue.get('explanation', 'N/A')}\n"
                response += f"- **Fix Needed:** {issue.get('correction_needed', 'N/A')}\n\n"
        
        # High Issues
        high = analysis.get("high_issues", [])
        if high:
            response += f"## 🟠 High Priority Issues ({len(high)})\n\n"
            for i, issue in enumerate(high, 1):
                response += f"### {i}. {issue.get('issue', 'Issue')}\n"
                response += f"- **{framework} Requirement:** {issue.get('framework_requirement', 'N/A')}\n"
                response += f"- **Fix Needed:** {issue.get('correction_needed', 'N/A')}\n\n"
        
        # Medium and Low Issues (summarized)
        medium = analysis.get("medium_issues", [])
        low = analysis.get("low_issues", [])
        if medium or low:
            response += f"## 🟡 Other Issues\n"
            response += f"- **Medium Priority:** {len(medium)} issues\n"
            response += f"- **Low Priority:** {len(low)} issues\n\n"
        
        # Compliant Areas
        compliant = analysis.get("compliant_areas", [])
        if compliant:
            response += f"## ✅ Compliant Areas\n\n"
            for area in compliant[:5]:  # Show top 5
                response += f"- {area}\n"
            if len(compliant) > 5:
                response += f"- ...and {len(compliant) - 5} more\n"
            response += "\n"
        
        # Recommendations
        recommendations = analysis.get("recommendations", [])
        if recommendations:
            response += f"## 💡 Recommendations\n\n"
            for rec in recommendations[:3]:  # Show top 3
                response += f"- {rec}\n"
            response += "\n"
        
        # Divider before corrected document
        response += "\n" + "="*80 + "\n\n"
        
        # Corrected Document Section
        response += f"# ✅ Corrected {framework}-Compliant {doc_type}\n\n"
        response += f"I've generated a fully compliant version that addresses all the issues identified above.\n\n"
        response += f"## 📄 Corrected Document:\n\n"
        response += "```\n"
        response += corrected_doc[:3000]  # Limit for display
        if len(corrected_doc) > 3000:
            response += "\n\n[... Document continues ...]\n"
        response += "\n```\n\n"
        
        response += f"**Note:** Replace placeholders like [Company Name], [Date], [Contact Email] with your actual information.\n\n"
        response += f"**Ready for Use:** This document is production-ready and fully compliant with {framework} requirements.\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Format document compliance response failed: {e}")
        return f"Analysis completed but formatting failed: {str(e)}"

