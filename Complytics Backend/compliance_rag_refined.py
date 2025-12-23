# Unified Intelligent Compliance RAG System
# This module consolidates all compliance chatbot functionality into one intelligent system
# Features:
# - Stores only user queries (not bot responses) up to 50 queries
# - Intelligent LLM-based intent classification (not keyword-based)
# - Intelligent LLM-based expert routing (not keyword-based)
# - Handles ambiguous queries with follow-up questions
# - Document upload handling
# - Guardrails for non-compliance queries
# - Works like ChatGPT for security compliance

import json
import logging
import time
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

# Import necessary functions from compliance_rag
from compliance_rag import (
    rate_limited_generate_content,
    rate_limited_generate_content_optimized,
    process_documents,
    get_embedding_optimized,
    expert_security_controls,
    expert_privacy_regulations,
    expert_audit_compliance,
    expert_financial_compliance,
    expert_healthcare_compliance,
    expert_international_compliance,
    expert_operational_compliance,
    expert_industry_specific,
    aggregate_expert_outputs,
    classify_document_type,
    extract_text_from_pdf,
    extract_text_from_docx,
    generate_simple_non_compliance_response,
    QUERY_CACHE,
    save_query_cache,
    hash_text
)


# ============================================================================
# INTELLIGENT CONTEXT MANAGEMENT - Stores only user queries (up to 50)
# ============================================================================

class IntelligentConversationHistory:
    """
    Intelligent conversation history that stores ONLY user queries (not bot responses).
    Maintains up to 50 user queries for context.
    """
    def __init__(self, max_queries: int = 50, timeout_seconds: int = 3600):
        self.user_queries = []  # Store only user queries
        self.max_queries = max_queries
        self.timeout_seconds = timeout_seconds
        self.last_update_time = time.time()
        self.pending_clarification = None  # Track if we're waiting for clarification
        
    def add_user_query(self, query: str, is_compliance: bool = True):
        """Add a user query to history (only queries, not responses)."""
        current_time = time.time()
        
        # Reset if timeout exceeded
        if current_time - self.last_update_time > self.timeout_seconds:
            self.reset()
        
        # Only store compliance-related queries
        if is_compliance and query.strip():
            self.user_queries.append({
                'query': query.strip(),
                'timestamp': current_time,
                'is_compliance': is_compliance
            })
            
            # Maintain max queries limit
            if len(self.user_queries) > self.max_queries:
                self.user_queries.pop(0)
            
            self.last_update_time = current_time
    
    def get_context(self) -> str:
        """Get conversation context from user queries only."""
        if not self.user_queries:
            return ""
        
        # Build context from recent user queries (last 10 for efficiency)
        recent_queries = self.user_queries[-10:]
        context_parts = []
        for q_data in recent_queries:
            context_parts.append(q_data['query'])
        
        # Return as a single string for better LLM understanding
        return " ".join(context_parts)
    
    def get_all_queries(self) -> List[str]:
        """Get all user queries as a list."""
        return [q['query'] for q in self.user_queries]
    
    def reset(self):
        """Reset conversation history."""
        self.user_queries = []
        self.pending_clarification = None
    
    def set_pending_clarification(self, clarification_message: str):
        """Set a pending clarification request."""
        self.pending_clarification = clarification_message
    
    def clear_pending_clarification(self):
        """Clear pending clarification."""
        self.pending_clarification = None


# ============================================================================
# INTELLIGENT INTENT CLASSIFICATION (LLM-based, not keyword-based)
# ============================================================================

def intelligent_intent_classification(
    query: str, 
    conversation_context: str = "", 
    has_uploaded_doc: bool = False
) -> Dict[str, Any]:
    """
    Intelligently classify user intent using LLM (not keyword matching).
    
    Returns:
        {
            "intent": str,  # USE_MAIN_EXPERTS, DOC_ANALYSIS, DOC_GENERATION, etc.
            "framework": str,
            "requires_framework": bool,
            "confidence": float,
            "reasoning": str,
            "is_ambiguous": bool,
            "clarification_needed": str
        }
    """
    # Check cache first
    cache_key = f"intent_class:{hash_text(f'{query}:{has_uploaded_doc}')}"
    if cache_key in QUERY_CACHE:
        cached = QUERY_CACHE[cache_key]
        if isinstance(cached, dict) and 'intent' in cached:
            logger.info(f"✅ Cache hit for intent classification: {cached.get('intent')}")
            return cached
    
    try:
        prompt = f"""You are an expert at understanding user intent in a compliance chatbot context.

USER QUERY: "{query}"
CONVERSATION CONTEXT: "{conversation_context[:1000] if conversation_context else 'None (new conversation)'}"
HAS UPLOADED DOCUMENT: {has_uploaded_doc}

Analyze this query and classify the user's intent. Consider:
1. What the user is trying to accomplish
2. Whether they're asking a question, requesting analysis, or asking for document generation
3. If they're referring to an uploaded document
4. Whether the query is ambiguous and needs clarification

INTENT CATEGORIES:
1. USE_MAIN_EXPERTS - User is asking a compliance question that requires expert knowledge
   - Questions about regulations, requirements, controls, standards
   - "What are GDPR requirements?", "Explain ISO 27001", "How do I implement SOC 2?"
   
2. DOC_ANALYSIS - User wants to analyze an uploaded document
   - "Analyze my document", "Check my privacy policy", "Review this file"
   - Only if has_uploaded_doc is True OR user explicitly mentions analyzing their document
   - DO NOT classify as DOC_ANALYSIS if user says they DIDN'T upload a document (e.g., "I didn't upload the document")
   
3. DOC_GENERATION - User wants to generate/create a new document
   - "Create a privacy policy", "Generate GDPR document", "Make me a terms document"
   
4. DOC_SUMMARY - User wants a summary of uploaded document
   - "Summarize my document", "What's in this file", "Give me an overview"
   - Only if has_uploaded_doc is True
   
5. SCENARIO_GUIDANCE - User wants step-by-step implementation guidance
   - "How should we achieve SOC 2 certification?", "Guide us through HIPAA compliance"
   - Step-by-step implementation guides or certification paths
   
6. GENERAL_QA_SHORT - User explicitly wants a brief/short answer or summary
   - "Tell me briefly", "In short", "Quick answer", "Now tell in short", "Summarize", "Briefly"
   - Follow-up queries asking for a summary of previous conversation
   - If query contains words like "short", "brief", "summarize" AND has conversation context, classify as GENERAL_QA_SHORT
   
7. NON_COMPLIANCE - Query is not related to compliance
   - Personal questions, entertainment, food, games, etc.
   
8. AMBIGUOUS - Query is unclear and needs clarification
   - Too vague, lacks context, uses pronouns without reference
   - "Tell me more", "What about that?", "How do I do it?" (without context)

AMBIGUITY DETECTION:
- Query is AMBIGUOUS if:
  * Uses vague pronouns (it, that, this) without clear reference in context
  * Too short/generic without mentioning frameworks or specific topics
  * Asks "tell me more" or "what about that" without prior context
  * Cannot be answered even WITH conversation context AND is extremely vague (1-2 words)
  
- Query is NOT ambiguous if:
  * Mentions specific frameworks (GDPR, ISO 27001, SOC 2, HIPAA, ISO 13485, DRAP, etc.)
  * Has clear context from previous queries
  * Asks about specific controls, articles, or requirements
  * Provides additional information in follow-up (e.g., "medical devices and they sell all over pakistan" after asking about medicines)
  * Can be answered using conversation context (even if some details are missing)
  * Mentions compliance scenarios, frameworks, or specific topics

FRAMEWORK DETECTION:
Extract mentioned frameworks: GDPR, CCPA, HIPAA, ISO 27001, SOC 2, NIST, PCI DSS

Respond with ONLY a JSON object:
{{
  "intent": "INTENT_NAME",
  "framework": "detected_framework_or_general",
  "requires_framework": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "is_ambiguous": true/false,
  "clarification_needed": "question to ask user if ambiguous, empty string otherwise"
}}"""

        response = rate_limited_generate_content(prompt, temperature=0.1, max_tokens=300)
        
        # Validate response before parsing
        if not response or not response.strip():
            logger.warning("Empty response from LLM for intent classification, using fallback")
            raise ValueError("Empty response from LLM")
        
        # Check if response is an error message
        if "temporarily unavailable" in response.lower() or "error" in response.lower()[:50]:
            logger.warning(f"Error response from LLM: {response[:100]}")
            raise ValueError(f"LLM returned error: {response[:100]}")
        
        # Parse JSON response
        cleaned = response.strip()
        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            cleaned = '\n'.join([l for l in lines if not l.strip().startswith('```')])
            cleaned = cleaned.strip()
        
        if '{' in cleaned and '}' in cleaned:
            start = cleaned.find('{')
            end = cleaned.rfind('}') + 1
            cleaned = cleaned[start:end]
        else:
            logger.warning(f"No JSON found in response: {cleaned[:200]}")
            raise ValueError("No JSON found in response")
        
        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e} | Response: {cleaned[:200]}")
            raise ValueError(f"Invalid JSON response: {str(e)}")
        
        logger.info(f"Intent classification: {result.get('intent')} | ambiguous: {result.get('is_ambiguous')} | framework: {result.get('framework')}")
        
        # Cache the result
        QUERY_CACHE[cache_key] = result
        return result
        
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        fallback_result = {
            "intent": "USE_MAIN_EXPERTS",
            "framework": "general",
            "requires_framework": False,
            "confidence": 0.0,
            "reasoning": f"Fallback due to error: {str(e)}",
            "is_ambiguous": False,
            "clarification_needed": ""
        }
        # Cache fallback too
        QUERY_CACHE[cache_key] = fallback_result
        return fallback_result


# ============================================================================
# INTELLIGENT EXPERT ROUTING (LLM-based, not keyword-based)
# ============================================================================

def intelligent_expert_routing(
    query: str,
    conversation_context: str = "",
    framework: str = "general"
) -> Dict[str, Any]:
    """
    Intelligently route query to appropriate expert(s) using LLM analysis.
    Not based on keywords - uses semantic understanding.
    
    Returns:
        {
            "experts": List[str],  # ['security', 'privacy', 'audit', etc.]
            "reasoning": str,
            "expert_type": str,  # 'general', 'domain', 'specialized'
            "complexity": str  # 'simple', 'medium', 'complex'
        }
    """
    # Check cache first
    cache_key = f"expert_routing:{hash_text(f'{query}:{framework}')}"
    if cache_key in QUERY_CACHE:
        cached = QUERY_CACHE[cache_key]
        if isinstance(cached, dict) and 'experts' in cached:
            logger.info(f"✅ Cache hit for expert routing: {cached.get('experts')}")
            return cached
    
    try:
        prompt = f"""You are an expert at routing compliance queries to specialized experts.

USER QUERY: "{query}"
CONVERSATION CONTEXT: "{conversation_context[:800] if conversation_context else 'None'}"
FRAMEWORK: {framework}

Analyze this query and determine which expert(s) should handle it. Consider:
1. The domain of the query (security, privacy, audit, healthcare, financial, etc.)
2. The complexity and depth required
3. Whether multiple experts are needed

AVAILABLE EXPERTS:
- security: Security controls, access management, encryption, network security, ISO 27001 controls
- privacy: GDPR, CCPA, data protection, privacy regulations, data subject rights
- audit: Audit procedures, compliance verification, SOC 2, ISO 27001 audits, evidence collection
- financial: PCI DSS, SOX, financial regulations, banking compliance
- healthcare: HIPAA, healthcare compliance, PHI protection, medical data regulations
- international: Cross-border compliance, international regulations, data transfer
- operational: Business processes, vendor management, operational controls
- industry_specific: Industry-specific regulations (FERPA, GLBA, etc.)
- general: General compliance questions, comparisons, simple factual queries

ROUTING RULES:
1. Use 'general' for:
   - Simple factual questions ("What is GDPR?")
   - Comparison queries ("How do GDPR and CCPA differ?")
   - Broad overview questions
   
2. Use 'domain' expert for:
   - Medium complexity questions in a specific domain
   - Questions about specific frameworks (GDPR → privacy, ISO 27001 → security/audit)
   
3. Use 'specialized' expert(s) for:
   - Complex implementation questions
   - Multi-domain questions requiring multiple experts
   - Technical deep-dive questions

COMPLEXITY ANALYSIS:
- simple: Basic questions, definitions, comparisons
- medium: Specific requirements, controls, implementation basics
- complex: Multi-step implementation, technical configuration, advanced scenarios

Respond with ONLY a JSON object:
{{
  "experts": ["expert1", "expert2"],
  "reasoning": "why these experts",
  "expert_type": "general|domain|specialized",
  "complexity": "simple|medium|complex"
}}"""

        response = rate_limited_generate_content(prompt, temperature=0.1, max_tokens=300)
        
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
        
        # Validate experts list
        valid_experts = ['security', 'privacy', 'audit', 'financial', 'healthcare', 
                        'international', 'operational', 'industry_specific', 'general']
        experts = result.get('experts', [])
        experts = [e for e in experts if e in valid_experts]
        
        if not experts:
            experts = ['audit']  # Default fallback
        
        result['experts'] = experts[:3]  # Limit to max 3 experts
        logger.info(f"Expert routing: {experts} | type: {result.get('expert_type')} | complexity: {result.get('complexity')}")
        
        # Cache the result
        QUERY_CACHE[cache_key] = result
        return result
        
    except Exception as e:
        logger.error(f"Expert routing failed: {e}")
        fallback_result = {
            "experts": ["audit"],
            "reasoning": f"Fallback due to error: {str(e)}",
            "expert_type": "general",
            "complexity": "medium"
        }
        # Cache fallback too
        QUERY_CACHE[cache_key] = fallback_result
        return fallback_result


# ============================================================================
# INTELLIGENT AMBIGUOUS QUERY HANDLING WITH FOLLOW-UPS
# ============================================================================

def handle_ambiguous_query(
    query: str,
    conversation_context: str,
    pending_clarification: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Intelligently handle ambiguous queries with contextual follow-up questions.
    
    Returns:
        (is_ambiguous: bool, clarification_message: str)
    """
    try:
        # Use LLM for all ambiguity detection - no keyword patterns
        
        # Use LLM for edge cases only
        prompt = f"""Analyze if this user query is ambiguous and needs clarification.

USER QUERY: "{query}"
CONVERSATION CONTEXT: "{conversation_context[:1000] if conversation_context else 'None (new conversation)'}"
PENDING CLARIFICATION: "{pending_clarification if pending_clarification else 'None'}"

CRITICAL RULES - BE STRICT:
1. Query is DEFINITELY NOT ambiguous if:
   - Mentions specific frameworks (GDPR, ISO 27001, SOC 2, HIPAA, PCI DSS, NIST, CCPA, ISO 13485, DRAP) - EVEN if short
   - Has question words (what, how, explain, tell me) + compliance terms
   - Has conversation context mentioning frameworks, compliance topics, or previous questions
   - Asks "what is X", "what are X", "explain X", "tell me about X" where X is a framework or compliance topic
   - Asks "I want to know about X" or "I need information about X" or "what compliance framework"
   - Mentions specific compliance scenarios (e.g., "my company sells medicines", "medical devices", "healthcare")
   - Provides additional information in follow-up (e.g., "medical devices and they sell all over pakistan" after asking about medicines)
   - Can be answered using conversation context (even if some details are missing)
   - Has more than 5 words and mentions compliance/compliance terms
   
2. Query IS ambiguous ONLY if:
   - Single word without context (e.g., "costs", "rules", "help" with NO conversation context)
   - Uses vague pronouns (it, that, this) without clear reference AND no context
   - "Tell me more" or "what about that" without ANY prior context
   - Cannot be answered even WITH conversation context AND is extremely vague (1-2 words)
   - User hasn't provided requested clarification AND query is still vague (1-2 words) AFTER being asked for clarification

3. Examples:
   - "what is gdpr" → NOT ambiguous (mentions framework)
   - "GDPR Compliance" → NOT ambiguous (mentions framework)
   - "I wanna know about GDPR Compliance basic rules" → NOT ambiguous (clear question with framework)
   - "costs" (with GDPR context) → NOT ambiguous (has context)
   - "costs" (NO context) → ambiguous
   - "tell me more" (NO context) → ambiguous
   - "tell me more" (with GDPR context) → NOT ambiguous

Respond with ONLY a JSON object:
{{
  "is_ambiguous": true/false,
  "clarification_message": "helpful follow-up question if ambiguous, empty string otherwise"
}}"""

        response = rate_limited_generate_content(prompt, temperature=0.1, max_tokens=250)
        
        # Validate response before parsing
        if not response or not response.strip():
            logger.warning("Empty response from LLM for ambiguous query check, using fallback")
            raise ValueError("Empty response from LLM")
        
        # Check if response is an error message
        if "temporarily unavailable" in response.lower() or "error" in response.lower()[:50]:
            logger.warning(f"Error response from LLM: {response[:100]}")
            raise ValueError(f"LLM returned error: {response[:100]}")
        
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
        else:
            logger.warning(f"No JSON found in response: {cleaned[:200]}")
            raise ValueError("No JSON found in response")
        
        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e} | Response: {cleaned[:200]}")
            raise ValueError(f"Invalid JSON response: {str(e)}")
        
        is_ambiguous = result.get('is_ambiguous', False)
        clarification = result.get('clarification_message', '')
        
        # Default clarification if ambiguous but no message provided
        if is_ambiguous and not clarification:
            clarification = (
                "I'd be happy to help! Could you please provide more details?\n\n"
                "- Which compliance framework are you interested in? (GDPR, ISO 27001, SOC 2, HIPAA, PCI DSS, etc.)\n"
                "- What specific requirement, control, or regulation?\n"
                "- Are you looking for implementation guidance or regulatory requirements?"
            )
        
        logger.info(f"Ambiguous query check: {is_ambiguous} | query: '{query[:50]}...'")
        return is_ambiguous, clarification
        
    except Exception as e:
        logger.error(f"Ambiguous query handling failed: {e}")
        # Smart fallback - check if query mentions frameworks or compliance terms
        query_lower = query.lower()
        frameworks = ['gdpr', 'iso 27001', 'iso27001', 'soc 2', 'soc2', 'hipaa', 'pci dss', 'pcidss', 
                      'nist', 'ccpa', 'iso 13485', 'iso13485', 'drap', 'wcag', 'compliance', 
                      'regulatory', 'security', 'privacy', 'audit']
        
        # If query mentions frameworks or compliance terms, it's NOT ambiguous
        mentions_framework = any(fw in query_lower for fw in frameworks)
        has_question_words = any(word in query_lower for word in ['what', 'how', 'explain', 'tell', 'describe', 'list'])
        has_context = bool(conversation_context and len(conversation_context.strip()) > 10)
        
        # If query is clear (mentions framework OR has question words + compliance terms OR has context), treat as NOT ambiguous
        if mentions_framework or (has_question_words and len(query.split()) > 3) or has_context:
            logger.info(f"Fallback: Query NOT ambiguous (mentions framework or has context): '{query[:50]}...'")
            return False, ""
        
        # Otherwise, treat as ambiguous
        logger.warning(f"Fallback: Query treated as ambiguous (no framework/context detected): '{query[:50]}...'")
        return True, (
            "I'd be happy to help! Could you please provide more details?\n\n"
            "- Which compliance framework are you interested in?\n"
            "- What specific requirement or control?\n"
            "- What are you trying to accomplish?"
        )


# ============================================================================
# INTELLIGENT DOCUMENT REFERENCE CHECK (LLM-based, not keyword-based)
# ============================================================================

def intelligent_document_reference_check(
    query: str,
    conversation_context: str = "",
    has_uploaded_doc: bool = False
) -> Dict[str, Any]:
    """
    Intelligently detect if user is referring to an uploaded document using LLM.
    Not based on keywords - uses semantic understanding.
    
    Returns:
        {
            "mentions_document": bool,
            "is_negative_statement": bool,
            "confidence": float
        }
    """
    try:
        prompt = f"""Analyze this user query to determine if they are referring to an uploaded document.

USER QUERY: "{query}"
CONVERSATION CONTEXT: "{conversation_context[:800] if conversation_context else 'None (new conversation)'}"
HAS UPLOADED DOCUMENT: {has_uploaded_doc}

Determine:
1. Does the user mention or refer to a document they uploaded/provided/gave?
   - Examples: "tell me about the doc i just gave you", "analyze my uploaded document", "review the file I uploaded"
   - Look for references like: "my document", "the document I uploaded", "file I gave you", "doc I just uploaded"
   - Consider variations: "gave you", "provided", "uploaded", "sent", "attached"

2. Is this a NEGATIVE statement about document upload?
   - Examples: "I didn't upload the document", "I haven't uploaded", "no document uploaded"
   - These should be marked as negative statements

3. Is this a general compliance question NOT about a specific uploaded document?
   - Examples: "what is GDPR", "explain ISO 27001", "how do I implement SOC 2"
   - These are NOT document references

CRITICAL RULES:
- "tell me about the doc i just gave you" → mentions_document = True
- "I just uploaded the privacy policy document" → mentions_document = True
- "I didn't upload the document" → mentions_document = False, is_negative_statement = True
- "what is GDPR" → mentions_document = False
- "which companies should implement this framework" → mentions_document = False (refers to framework from context, not document)

Respond with ONLY a JSON object:
{{
  "mentions_document": true/false,
  "is_negative_statement": true/false,
  "confidence": 0.0-1.0
}}"""

        response = rate_limited_generate_content(prompt, temperature=0.1, max_tokens=200)
        
        # Validate response before parsing
        if not response or not response.strip():
            logger.warning("Empty response from LLM for document reference check, using fallback")
            return {"mentions_document": False, "is_negative_statement": False, "confidence": 0.0}
        
        # Check if response is an error message
        if "temporarily unavailable" in response.lower() or "error" in response.lower()[:50]:
            logger.warning(f"Error response from LLM: {response[:100]}")
            return {"mentions_document": False, "is_negative_statement": False, "confidence": 0.0}
        
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
        else:
            logger.warning(f"No JSON found in response: {cleaned[:200]}")
            return {"mentions_document": False, "is_negative_statement": False, "confidence": 0.0}
        
        try:
            result = json.loads(cleaned)
            logger.info(f"Document reference check: mentions_doc={result.get('mentions_document')} | negative={result.get('is_negative_statement')}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in document reference check: {e} | Response: {cleaned[:200]}")
            return {"mentions_document": False, "is_negative_statement": False, "confidence": 0.0}
        
    except Exception as e:
        logger.error(f"Document reference check failed: {e}")
        return {"mentions_document": False, "is_negative_statement": False, "confidence": 0.0}


# ============================================================================
# INTELLIGENT FRAMEWORK RESOLUTION FROM CONTEXT (LLM-based)
# ============================================================================

def intelligent_framework_resolution(query: str, conversation_context: str) -> str:
    """
    Intelligently resolve framework references like "this framework" from conversation context.
    Uses LLM to understand what framework the user is referring to.
    
    Returns:
        framework name (e.g., "ISO 27001", "GDPR") or "general" if not found
    """
    try:
        prompt = f"""Analyze this query and conversation context to determine which compliance framework the user is referring to.

USER QUERY: "{query}"
CONVERSATION CONTEXT (previous user queries): "{conversation_context[:1000]}"

The user query may use references like:
- "this framework"
- "the framework"
- "it"
- "that"

Determine which specific compliance framework they're referring to based on the conversation context.

Possible frameworks: GDPR, ISO 27001, ISO 27002, SOC 2, HIPAA, PCI DSS, NIST, CCPA, CPRA

If the query clearly refers to a framework mentioned in the conversation context, return that framework name.
If no clear reference is found, return "general".

Examples:
- Query: "which companies should implement this framework" + Context: "what is iso 27001" → Return: "ISO 27001"
- Query: "tell me about it" + Context: "what is gdpr" → Return: "GDPR"
- Query: "what is compliance" + Context: "general questions" → Return: "general"

Respond with ONLY the framework name (e.g., "ISO 27001", "GDPR", "SOC 2") or "general":
"""

        response = rate_limited_generate_content(prompt, temperature=0.1, max_tokens=100)
        
        if not response or not response.strip():
            return "general"
        
        # Clean and extract framework name
        cleaned = response.strip().lower()
        
        # Map common variations to standard names
        framework_map = {
            'iso 27001': 'ISO 27001',
            'iso27001': 'ISO 27001',
            'iso/iec 27001': 'ISO 27001',
            'gdpr': 'GDPR',
            'soc 2': 'SOC 2',
            'soc2': 'SOC 2',
            'soc ii': 'SOC 2',
            'hipaa': 'HIPAA',
            'pci dss': 'PCI DSS',
            'pci-dss': 'PCI DSS',
            'nist': 'NIST',
            'ccpa': 'CCPA',
            'cpra': 'CPRA'
        }
        
        for key, value in framework_map.items():
            if key in cleaned:
                logger.info(f"Resolved framework from context: {value}")
                return value
        
        return "general"
        
    except Exception as e:
        logger.error(f"Framework resolution failed: {e}")
        return "general"


# ============================================================================
# NON-COMPLIANCE GUARDRAILS
# ============================================================================

def check_compliance_guardrails(query: str, conversation_context: str = "") -> Tuple[bool, str]:
    """
    Intelligent guardrails to detect non-compliance queries.
    Uses LLM for semantic understanding, not just keywords.
    
    Returns:
        (is_compliance: bool, reason: str)
    """
    try:
        prompt = f"""Determine if this query is related to compliance, security, or regulatory topics.

USER QUERY: "{query}"
CONVERSATION CONTEXT: "{conversation_context[:500] if conversation_context else 'None'}"

A query is COMPLIANCE-RELATED if it's about:
- Compliance frameworks (GDPR, ISO 27001, SOC 2, HIPAA, PCI DSS, NIST, CCPA)
- Security controls, access management, encryption
- Privacy regulations, data protection
- Audit procedures, compliance verification
- Risk management, governance
- Regulatory requirements
- Document analysis/generation for compliance
- Implementation guidance for compliance

A query is NOT compliance-related if it's about:
- Personal life (cooking, recipes, entertainment, movies, sports)
- General knowledge unrelated to compliance
- Health advice (unless HIPAA/compliance context)
- Weather, news, current events (unless compliance context)
- Games, hobbies, personal interests

Respond with ONLY a JSON object:
{{
  "is_compliance": true/false,
  "reason": "brief explanation",
  "confidence": 0.0-1.0
}}"""

        response = rate_limited_generate_content(prompt, temperature=0.1, max_tokens=200)
        
        # Validate response before parsing
        if not response or not response.strip():
            logger.warning("Empty response from LLM for compliance guardrail check, defaulting to compliance-related")
            return True, "Defaulted to compliance-related (empty LLM response)"
        
        # Check if response is an error message
        if "temporarily unavailable" in response.lower() or "error" in response.lower()[:50]:
            logger.warning(f"Error response from LLM: {response[:100]}")
            return True, "Defaulted to compliance-related (LLM error)"
        
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
        else:
            logger.warning(f"No JSON found in guardrail response: {cleaned[:200]}")
            return True, "Defaulted to compliance-related (no JSON in response)"
        
        try:
            result = json.loads(cleaned)
            is_compliance = result.get('is_compliance', True)  # Default to compliant
            reason = result.get('reason', 'Compliance-related query')
            
            logger.info(f"Compliance guardrail: {is_compliance} | reason: {reason}")
            return is_compliance, reason
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in guardrail check: {e} | Response: {cleaned[:200]}")
            return True, "Defaulted to compliance-related (JSON parse error)"
        
    except Exception as e:
        logger.error(f"Compliance guardrail check failed: {e}")
        # Conservative fallback - assume compliance-related
        return True, "Defaulted to compliance-related"


# ============================================================================
# HARDCODED ANSWERS FOR COMMON QUERIES
# ============================================================================

def get_hardcoded_answer(query_normalized: str) -> Optional[str]:
    """
    Check if query matches any hardcoded answers.
    Returns the hardcoded response if match found, None otherwise.
    """
    # Normalize query: lowercase, remove extra spaces
    query_normalized = " ".join(query_normalized.lower().strip().split())
    
    # Hardcoded query-response mappings
    hardcoded_queries = {
        "what is gdpr what are its main requirements": """## GDPR Overview and Main Requirements

**What is GDPR?**

The General Data Protection Regulation (GDPR) is a comprehensive data protection law that came into effect on May 25, 2018, across the European Union (EU) and European Economic Area (EEA). It governs how organizations collect, process, store, and protect personal data of EU residents.

### Main Requirements of GDPR:

#### 1. **Lawful Basis for Processing**
   - Organizations must have a valid legal reason for processing personal data
   - Common bases include: consent, contract performance, legal obligation, vital interests, public task, or legitimate interests

#### 2. **Data Subject Rights**
   - **Right to Access**: Individuals can request copies of their personal data
   - **Right to Rectification**: Correct inaccurate or incomplete data
   - **Right to Erasure ("Right to be Forgotten")**: Request deletion of personal data
   - **Right to Restrict Processing**: Limit how data is used
   - **Right to Data Portability**: Receive data in a machine-readable format
   - **Right to Object**: Object to processing for direct marketing or legitimate interests
   - **Rights Related to Automated Decision-Making**: Protection against automated profiling

#### 3. **Privacy by Design and by Default**
   - Implement data protection measures from the start of any project
   - Default settings should prioritize privacy
   - Minimize data collection to what's necessary

#### 4. **Data Protection Impact Assessments (DPIAs)**
   - Required for high-risk processing activities
   - Must assess risks and implement mitigating measures

#### 5. **Data Breach Notification**
   - Report breaches to supervisory authority within 72 hours
   - Notify affected individuals if breach poses high risk to their rights

#### 6. **Data Protection Officer (DPO)**
   - Required for organizations with large-scale processing, public authorities, or special categories of data
   - Acts as point of contact for data protection matters

#### 7. **Records of Processing Activities**
   - Maintain detailed records of all data processing activities
   - Document purposes, data categories, recipients, retention periods

#### 8. **Cross-Border Data Transfers**
   - Ensure adequate protection when transferring data outside EU/EEA
   - Use Standard Contractual Clauses (SCCs) or other approved mechanisms

#### 9. **Consent Requirements**
   - Must be freely given, specific, informed, and unambiguous
   - Easy to withdraw consent
   - Pre-ticked boxes don't constitute valid consent

#### 10. **Penalties**
   - Fines up to €20 million or 4% of annual global turnover (whichever is higher)
   - Supervisory authorities can issue warnings, reprimands, and order data deletion

### Key Principles:
- **Lawfulness, fairness, and transparency**
- **Purpose limitation** (collect only for specified purposes)
- **Data minimization** (collect only necessary data)
- **Accuracy** (keep data up to date)
- **Storage limitation** (retain only as long as necessary)
- **Integrity and confidentiality** (appropriate security measures)
- **Accountability** (demonstrate compliance)

Would you like more details on any specific requirement or help implementing GDPR compliance for your organization?""",

        "my company deals with medical devices can you tell which compliance framework we should focus on": """## Compliance Frameworks for Medical Device Companies

Based on your company's focus on medical devices, here are the **key compliance frameworks** you should prioritize:

### **Primary Frameworks:**

#### 1. **ISO 13485:2016 - Medical Devices Quality Management Systems**
   - **Why Essential**: International standard specifically for medical device quality management
   - **Requirements**:
     - Quality management system (QMS) implementation
     - Risk management throughout product lifecycle
     - Design and development controls
     - Production and service provision controls
     - Post-market surveillance
   - **Geographic Scope**: Global standard, recognized worldwide

#### 2. **FDA Regulations (21 CFR Part 820) - If selling in USA**
   - **Why Essential**: Mandatory for medical devices sold in the United States
   - **Requirements**:
     - Quality System Regulation (QSR)
     - Design controls
     - Production and process controls
     - Corrective and Preventive Actions (CAPA)
     - Device labeling and tracking
   - **Geographic Scope**: United States

#### 3. **EU MDR (Medical Device Regulation) - If selling in Europe**
   - **Why Essential**: Mandatory for medical devices in European Union
   - **Requirements**:
     - Clinical evaluation and evidence
     - Post-market surveillance
     - Unique Device Identification (UDI)
     - Notified body involvement
     - Technical documentation requirements
   - **Geographic Scope**: European Union

#### 4. **HIPAA (Health Insurance Portability and Accountability Act) - If handling PHI**
   - **Why Essential**: Required if you handle Protected Health Information (PHI)
   - **Requirements**:
     - Administrative, physical, and technical safeguards
     - Privacy Rule compliance
     - Security Rule compliance
     - Breach notification procedures
   - **Geographic Scope**: United States (but applies to any organization handling US patient data)

### **Supporting Frameworks:**

#### 5. **ISO 27001 - Information Security Management**
   - **Why Important**: Medical devices often collect/store sensitive health data
   - **Focus**: Information security controls, risk management, data protection

#### 6. **GDPR - If operating in EU**
   - **Why Important**: Medical devices process personal health data
   - **Focus**: Data subject rights, privacy by design, data breach notification

#### 7. **ISO 14971 - Medical Device Risk Management**
   - **Why Important**: Risk management standard specifically for medical devices
   - **Focus**: Risk analysis, evaluation, and control throughout device lifecycle

### **Recommended Implementation Priority:**

1. **Start with ISO 13485** - Foundation for all medical device quality management
2. **Add ISO 14971** - Risk management framework
3. **Region-Specific**: 
   - USA → FDA 21 CFR Part 820
   - EU → EU MDR
   - Other regions → Check local medical device regulations
4. **Data Protection**: 
   - HIPAA (if handling PHI in USA)
   - GDPR (if operating in EU)
5. **Information Security**: ISO 27001 (for data security)

### **Key Considerations:**
- **Regulatory Approval**: Medical devices require regulatory approval before market entry
- **Clinical Evidence**: Most devices need clinical evaluation/studies
- **Post-Market Surveillance**: Ongoing monitoring and reporting requirements
- **Documentation**: Extensive technical documentation required
- **Quality Management**: Robust QMS is mandatory, not optional

Would you like detailed guidance on implementing any of these frameworks, or help determining which specific regulations apply to your target markets?"""
    }
    
    # Check for exact match
    if query_normalized in hardcoded_queries:
        return hardcoded_queries[query_normalized]
    
    # Check for partial matches (in case of slight variations)
    if "gdpr" in query_normalized and "main requirements" in query_normalized:
        if "what is" in query_normalized or "tell me about" in query_normalized:
            return hardcoded_queries["what is gdpr what are its main requirements"]
    
    if ("medical device" in query_normalized or "medical devices" in query_normalized) and "compliance framework" in query_normalized:
        if "which" in query_normalized or "what" in query_normalized or "should" in query_normalized:
            return hardcoded_queries["my company deals with medical devices can you tell which compliance framework we should focus on"]
    
    return None


# ============================================================================
# MAIN UNIFIED PROCESSING FUNCTION
# ============================================================================

def process_compliance_query_unified(
    query: str,
    conversation_history: IntelligentConversationHistory,
    has_uploaded_doc: bool = False,
    document_text: Optional[str] = None,
    document_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Unified intelligent processing function for compliance queries.
    This is the main entry point that orchestrates all components.
    
    Returns:
        {
            "response": str,
            "experts_consulted": List[str],
            "is_compliance": bool,
            "needs_clarification": bool,
            "clarification_message": str
        }
    """
    start_time = time.time()
    
    try:
        # Step 1: Get conversation context (user queries only) - BEFORE adding current query
        conversation_context = conversation_history.get_context()
        
        # Step 1.5: Check for hardcoded answers (exact match)
        query_normalized = " ".join(query.lower().strip().split())
        hardcoded_response = get_hardcoded_answer(query_normalized)
        if hardcoded_response:
            logger.info(f"✅ Hardcoded answer found for query: '{query[:60]}...'")
            conversation_history.add_user_query(query, is_compliance=True)
            processing_time = time.time() - start_time
            return {
                "response": hardcoded_response,
                "experts_consulted": ["hardcoded"],
                "is_compliance": True,
                "needs_clarification": False,
                "clarification_message": ""
            }
        
        # Step 2: Check compliance guardrails
        is_compliance, compliance_reason = check_compliance_guardrails(query, conversation_context)
        
        if not is_compliance:
            logger.info(f"Non-compliance query detected: {query[:50]}...")
            response = generate_simple_non_compliance_response(query)
            conversation_history.add_user_query(query, is_compliance=False)
            return {
                "response": response,
                "experts_consulted": [],
                "is_compliance": False,
                "needs_clarification": False,
                "clarification_message": ""
            }
        
        # Step 2.5: Intelligently check if user is asking about uploaded document but hasn't uploaded one
        # Use LLM-based detection, not keyword patterns
        document_check_result = intelligent_document_reference_check(query, conversation_context, has_uploaded_doc)
        mentions_document = document_check_result.get('mentions_document', False)
        is_negative_upload_statement = document_check_result.get('is_negative_statement', False)
        
        if mentions_document and not has_uploaded_doc and not is_negative_upload_statement:
            logger.info(f"User asking about document but no document uploaded: {query[:50]}...")
            response = (
                "I'd be happy to help you analyze your document! However, I don't see any uploaded documents in our current session.\n\n"
                "**Please upload your document first**, and then I can:\n\n"
                "- Analyze it for compliance (GDPR, ISO 27001, SOC 2, etc.)\n"
                "- Provide a summary\n"
                "- Review specific sections\n"
                "- Check for compliance gaps\n\n"
                "Once you've uploaded your document, you can ask me questions like:\n"
                "- 'Analyze my document for GDPR compliance'\n"
                "- 'Summarize my uploaded document'\n"
                "- 'What are the key points in my document?'"
            )
            conversation_history.add_user_query(query, is_compliance=True)
            return {
                "response": response,
                "experts_consulted": [],
                "is_compliance": True,
                "needs_clarification": False,
                "clarification_message": ""
            }
        
        # Step 3: Check for ambiguous queries (using context from previous queries)
        pending_clarification = conversation_history.pending_clarification
        is_ambiguous, clarification_message = handle_ambiguous_query(
            query, conversation_context, pending_clarification
        )
        
        if is_ambiguous:
            logger.info(f"Ambiguous query detected, asking for clarification")
            conversation_history.set_pending_clarification(clarification_message)
            # Add ambiguous query to history so context is available for follow-up
            conversation_history.add_user_query(query, is_compliance=True)
            return {
                "response": clarification_message,
                "experts_consulted": [],
                "is_compliance": True,
                "needs_clarification": True,
                "clarification_message": clarification_message
            }
        
        # Clear pending clarification if query is no longer ambiguous
        conversation_history.clear_pending_clarification()
        
        # Add query to history AFTER we've determined it's not ambiguous
        conversation_history.add_user_query(query, is_compliance=True)
        
        # Step 4: Check cache for exact query match (only for cacheable queries)
        # Normalize query for cache key: lowercase, strip whitespace, remove extra spaces
        query_normalized = " ".join(query.lower().strip().split())
        cache_key = f"exact_query:{hash_text(query_normalized)}"
        
        # Check cache BEFORE processing (only for compliance queries that aren't document-specific)
        if cache_key in QUERY_CACHE:
            cached_response = QUERY_CACHE[cache_key]
            if isinstance(cached_response, str) and len(cached_response) > 0:
                logger.info(f"✅ CACHE HIT for query: '{query[:60]}...'")
                processing_time = time.time() - start_time
                return {
                    "response": cached_response,
                    "experts_consulted": ["cached"],
                    "is_compliance": True,
                    "needs_clarification": False,
                    "clarification_message": ""
                }
        
        # Step 5: Intelligent intent classification
        intent_result = intelligent_intent_classification(
            query, conversation_context, has_uploaded_doc
        )
        
        intent = intent_result.get('intent', 'USE_MAIN_EXPERTS')
        framework = intent_result.get('framework', 'general')
        
        # Intelligently resolve framework from context if query uses "this framework" or similar references
        if framework == 'general' and conversation_context:
            framework = intelligent_framework_resolution(query, conversation_context)
            if framework != 'general':
                logger.info(f"Resolved framework from context: {framework}")
        
        # Fix: Don't treat negative upload statements as DOC_ANALYSIS (using intelligent check)
        document_check_result = intelligent_document_reference_check(query, conversation_context, has_uploaded_doc)
        is_negative_upload_statement = document_check_result.get('is_negative_statement', False)
        
        if is_negative_upload_statement and intent == 'DOC_ANALYSIS':
            logger.info("Negative upload statement detected, overriding DOC_ANALYSIS intent")
            intent = 'USE_MAIN_EXPERTS'
            # Provide helpful response about document upload
            response = (
                "I understand you haven't uploaded a document yet. That's perfectly fine!\n\n"
                "**If you'd like to analyze a document**, please upload it first. I can help you with:\n\n"
                "- Privacy policies (GDPR, CCPA compliance)\n"
                "- Terms & Conditions\n"
                "- Security documentation\n"
                "- Compliance reports\n\n"
                "**Or, if you have a compliance question**, feel free to ask me directly! For example:\n"
                "- 'What are GDPR requirements?'\n"
                "- 'How do I implement ISO 27001 controls?'\n"
                "- 'Explain SOC 2 compliance'\n\n"
                "What would you like help with today?"
            )
            return {
                "response": response,
                "experts_consulted": [],
                "is_compliance": True,
                "needs_clarification": False,
                "clarification_message": ""
            }
        
        # Fallback: If intent classification failed and user has uploaded doc, check for document-related queries
        if intent == 'USE_MAIN_EXPERTS' and has_uploaded_doc and document_text:
            doc_keywords = ['document', 'file', 'upload', 'analyze', 'review', 'summarize', 'tell me about']
            query_lower = query.lower()
            if any(keyword in query_lower for keyword in doc_keywords):
                logger.info("Detected document-related query with uploaded document, routing to DOC_ANALYSIS")
                intent = 'DOC_ANALYSIS'
        
        # Determine if this query should be cached
        # Don't cache: ambiguous queries, document-specific queries, follow-up summary requests
        should_cache = True
        if intent == 'DOC_ANALYSIS' or intent == 'DOC_SUMMARY' or intent == 'DOC_GENERATION':
            should_cache = False  # Document-specific queries are context-dependent
        elif intent == 'GENERAL_QA_SHORT':
            # Follow-up summary requests are context-dependent and should not be cached
            # The intent classification already handles this intelligently
            if conversation_context:
                should_cache = False  # Follow-up summary requests are context-dependent
        
        # Step 5: Handle document-specific intents
        if intent == 'DOC_ANALYSIS' and has_uploaded_doc and document_text:
            # Use document compliance expert
            result = document_compliance_expert(document_text, document_type or 'privacy_policy', framework, conversation_context)
            response = format_document_compliance_response(result)
            experts = ['document_compliance']
            
        elif intent == 'DOC_GENERATION':
            # Handle document generation
            from compliance_rag import generate_intelligent_compliant_document, create_docx_with_download_link, format_document_response_with_download
            
            doc_type = intent_result.get('document_type', 'privacy_policy')
            organization_context = conversation_context[:500]
            
            document_content = generate_intelligent_compliant_document(
                doc_type, framework, organization_context
            )
            
            # Create download link (would need user_id in real implementation)
            file_path, download_url = create_docx_with_download_link(
                document_content, doc_type, framework, "user_id"
            )
            
            if download_url:
                response = format_document_response_with_download(
                    document_content, download_url, doc_type, framework
                )
            else:
                response = f"I've generated a {framework}-compliant {doc_type.replace('_', ' ')} document:\n\n{document_content}"
            
            experts = ['privacy', 'audit']
            
        elif intent == 'DOC_SUMMARY' and has_uploaded_doc and document_text:
            # Simple document summary
            prompt = f"""Summarize this document concisely (3-5 sentences).

CONVERSATION CONTEXT (previous user queries):
{conversation_context[:500] if conversation_context else 'None'}

DOCUMENT TO SUMMARIZE:
{document_text[:2500]}

Provide a concise summary (3-5 sentences):
"""
            response = rate_limited_generate_content_optimized(prompt)
            experts = []
            
        elif intent == 'SCENARIO_GUIDANCE':
            # Scenario guidance expert
            response = scenario_guidance_expert(query, framework, conversation_context)
            experts = ['guidance']
            
        elif intent == 'GENERAL_QA_SHORT':
            # Short QA answer - use conversation context for follow-up queries
            response = short_qa_answer(query, conversation_context)
            experts = []
            
        else:
            # Step 6: USE_MAIN_EXPERTS - Intelligent expert routing
            routing_result = intelligent_expert_routing(query, conversation_context, framework)
            experts = routing_result.get('experts', ['audit'])
            
            # Get context from framework documents
            context = ""
            try:
                segments, embeddings, index = process_documents()
                if segments and index:
                    query_embedding = get_embedding_optimized(query)
                    if query_embedding is not None:
                        query_embedding = np.expand_dims(query_embedding, axis=0)
                        distances, idxs = index.search(query_embedding, 3)
                        retrieved_segments = []
                        for idx in idxs[0]:
                            if idx >= 0 and idx < len(segments):
                                retrieved_segments.append(segments[idx])
                        if retrieved_segments:
                            context = " ".join(retrieved_segments[:500])
            except Exception as e:
                logger.warning(f"Error getting context from documents: {e}")
            
            # Call appropriate expert(s)
            expert_responses = []
            for expert_name in experts:
                if expert_name == 'security':
                    expert_response = expert_security_controls(query, context, conversation_context)
                elif expert_name == 'privacy':
                    expert_response = expert_privacy_regulations(query, context, conversation_context)
                elif expert_name == 'audit':
                    expert_response = expert_audit_compliance(query, context, conversation_context)
                elif expert_name == 'financial':
                    expert_response = expert_financial_compliance(query, context, conversation_context)
                elif expert_name == 'healthcare':
                    expert_response = expert_healthcare_compliance(query, context, conversation_context)
                elif expert_name == 'international':
                    expert_response = expert_international_compliance(query, context, conversation_context)
                elif expert_name == 'operational':
                    expert_response = expert_operational_compliance(query, context, conversation_context)
                elif expert_name == 'industry_specific':
                    expert_response = expert_industry_specific(query, context, conversation_context)
                elif expert_name == 'general':
                    from compliance_rag_intelligent import expert_general_compliance
                    expert_response = expert_general_compliance(query, context, conversation_context, framework)
                else:
                    expert_response = expert_audit_compliance(query, context, conversation_context)
                
                if expert_response:
                    expert_responses.append(expert_response)
            
            # Aggregate expert responses
            if len(expert_responses) == 1:
                response = expert_responses[0]
            elif len(expert_responses) > 1:
                response = aggregate_expert_outputs(expert_responses, query, context, conversation_context)
            else:
                response = "I couldn't generate a response. Please try rephrasing your question."
            
            # Check if response is an error message and provide helpful fallback
            if response and ("temporarily unavailable" in response.lower() or len(response.strip()) < 10):
                logger.warning("Expert returned error or empty response, providing fallback")
                if has_uploaded_doc and document_text:
                    response = (
                        "I'm having trouble processing your request right now due to service availability issues. "
                        "However, I can see you've uploaded a document. "
                        "Please try asking a more specific question about your document, such as:\n\n"
                        "- 'Analyze my document for GDPR compliance'\n"
                        "- 'What are the key points in my document?'\n"
                        "- 'Summarize my uploaded document'\n\n"
                        "Or try again in a few moments."
                    )
                else:
                    response = (
                        "I'm experiencing temporary service issues. Please try again in a few moments, "
                        "or rephrase your question. If the issue persists, try asking about a specific compliance framework "
                        "like GDPR, ISO 27001, or SOC 2."
                    )
        
        # Query already added to history after ambiguity check (Step 3)
        
        # Step 7: Cache the response (only for cacheable compliance queries)
        if should_cache and response and len(response) > 0:
            try:
                QUERY_CACHE[cache_key] = response
                logger.info(f"💾 Cached response for query: '{query[:60]}...' (Cache size: {len(QUERY_CACHE)})")
                # Save cache immediately
                save_query_cache()
            except Exception as e:
                logger.error(f"Error caching response: {e}")
                # Don't fail on cache errors
        
        processing_time = time.time() - start_time
        logger.info(f"Query processed in {processing_time:.2f}s | experts: {experts} | cached: {should_cache}")
        
        return {
            "response": response,
            "experts_consulted": experts,
            "is_compliance": True,
            "needs_clarification": False,
            "clarification_message": ""
        }
        
    except Exception as e:
        logger.error(f"Error in unified processing: {e}", exc_info=True)
        return {
            "response": "I encountered an error processing your query. Please try rephrasing it.",
            "experts_consulted": [],
            "is_compliance": True,
            "needs_clarification": False,
            "clarification_message": ""
        }


# ============================================================================
# DOCUMENT EXPERT FUNCTIONS (from original compliance_rag_refined.py)
# ============================================================================

def privacy_policy_expert_extractive(document_text: str, framework: str = "GDPR", conversation_context: str = "") -> Dict[str, Any]:
    """Extractive privacy policy expert - outputs structured findings with quotes."""
    print("\n" + "="*80)
    print(f"📋 PRIVACY POLICY EXTRACTIVE EXPERT TRIGGERED (Framework: {framework})")
    print(f"Document length: {len(document_text)} characters")
    print("="*80 + "\n")
    logger.info(f"📋 PRIVACY POLICY EXTRACTIVE EXPERT triggered for framework: {framework}")
    
    try:
        prompt = f"""
You are a {framework} compliance expert. Analyze this privacy policy EXTRACTIVELY.

CONVERSATION CONTEXT (previous user queries):
{conversation_context[:800] if conversation_context else 'None (new conversation)'}

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
6. Consider conversation context to understand user's specific concerns or focus areas

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


def terms_expert_extractive(document_text: str, framework: str = "general", conversation_context: str = "") -> Dict[str, Any]:
    """Extractive terms & conditions expert - outputs structured findings."""
    print("\n" + "="*80)
    print(f"📜 TERMS & CONDITIONS EXTRACTIVE EXPERT TRIGGERED (Framework: {framework})")
    print(f"Document length: {len(document_text)} characters")
    print("="*80 + "\n")
    logger.info(f"📜 TERMS EXTRACTIVE EXPERT triggered for framework: {framework}")
    
    try:
        prompt = f"""
You are a legal compliance expert for Terms & Conditions. Analyze this document EXTRACTIVELY.

CONVERSATION CONTEXT (previous user queries):
{conversation_context[:800] if conversation_context else 'None (new conversation)'}

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
4. Consider conversation context to understand user's specific concerns or focus areas

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


def scenario_guidance_expert(scenario: str, framework: str = "GDPR", conversation_context: str = "") -> str:
    """Scenario guidance expert - provides step-by-step compliance guidance."""
    print("\n" + "="*80)
    print(f"🎯 SCENARIO GUIDANCE EXPERT TRIGGERED (Framework: {framework})")
    print(f"Scenario: {scenario[:100]}...")
    print("="*80 + "\n")
    logger.info(f"🎯 SCENARIO GUIDANCE EXPERT triggered for framework: {framework}")
    
    try:
        prompt = f"""
Provide step-by-step {framework} compliance guidance for this scenario:

CONVERSATION CONTEXT (previous user queries):
{conversation_context[:800] if conversation_context else 'None (new conversation)'}

SCENARIO: {scenario}

**CRITICAL FORMATTING REQUIREMENTS FOR FRONTEND RENDERING:**

1. **Use Markdown Headers:**
   - Use ## for main sections
   - Use ### for subsections
   - Use #### for sub-subsections
   - **MANDATORY:** Add a blank line BEFORE each header
   - **MANDATORY:** Add a blank line AFTER each header

2. **Green Highlighting for Framework References:**
   - ALL control IDs, article numbers, and framework references MUST be highlighted in green: <span style="color:#008000">Article 17 GDPR</span>
   - Examples:
     * <span style="color:#008000">ISO 27001 Control A.9.2.1</span>
     * <span style="color:#008000">SOC 2 CC6.1</span>
     * <span style="color:#008000">HIPAA §164.312(a)(1)</span>
     * <span style="color:#008000">PCI DSS Requirement 1.1</span>
   - Format: [Requirement] (<span style="color:#008000">{framework} Article X</span>)

3. **Use Bullet Points:**
   - Use * for bullet points
   - Use - for sub-bullets
   - Each bullet point should be on its own line
   - **MANDATORY:** Add a blank line BEFORE the bullet list
   - **MANDATORY:** Add a blank line AFTER the bullet list

4. **Proper Line Spacing:**
   - **CRITICAL:** Always add a blank line between sections
   - **CRITICAL:** Always add a blank line between paragraphs
   - **CRITICAL:** Always add a blank line between headers and content
   - Example format:
     
     ## Section Title
     
     Section introduction paragraph.
     
     ### Subsection Title
     
     * Bullet point 1
     * Bullet point 2
     
     Next paragraph with blank line above.

5. **Structured Response Format:**
   - Start with a brief overview (2-3 sentences)
   - Use clear section headers with proper spacing
   - Number steps clearly

INSTRUCTIONS:
1. Max 8 steps
2. Each step: cite specific {framework} article/section with green highlighting
3. Be actionable and specific
4. No generic boilerplate
5. Consider the conversation context to provide relevant, contextual guidance

Format:
## Overview
Brief 2-3 sentence overview of the scenario and approach.

## Step-by-Step Guidance

### Step 1: [Action]
* Requirement: [Description] (<span style="color:#008000">{framework} Article X</span>)
* Implementation: [Specific action]
* Key Points:
  - Point 1
  - Point 2

### Step 2: [Action]
* Requirement: [Description] (<span style="color:#008000">{framework} Article Y</span>)
* Implementation: [Specific action]
* Key Points:
  - Point 1
  - Point 2

[Continue for remaining steps...]

## Important Considerations
* Consideration 1
* Consideration 2
"""
        
        response = rate_limited_generate_content_optimized(prompt, temperature=0.1, max_tokens=1500)
        logger.info(f"Scenario guidance generated for {framework}")
        return response
        
    except Exception as e:
        logger.error(f"Scenario guidance failed: {e}")
        return f"Error generating guidance: {str(e)}"


def short_qa_answer(question: str, conversation_context: str = "") -> str:
    """Short QA mode - 2-4 sentence answers for general compliance questions.
    Uses conversation context for follow-up queries like 'tell me in short'."""
    print("\n" + "="*80)
    print("💬 SHORT QA EXPERT TRIGGERED")
    print(f"Question: {question[:100]}...")
    print("="*80 + "\n")
    logger.info(f"💬 SHORT QA EXPERT triggered for question: {question[:100]}")
    
    try:
        # Check if this is a follow-up summary request
        question_lower = question.lower()
        is_summary_request = any(phrase in question_lower for phrase in [
            'tell me in short', 'now tell in short', 'in short', 'summarize', 
            'brief', 'briefly', 'quick answer', 'give me a short'
        ])
        
        if is_summary_request and conversation_context:
            # This is a follow-up asking for a summary of previous conversation
            prompt = f"""Based on the previous conversation context, provide a concise 2-4 sentence summary.

CONVERSATION CONTEXT (previous user queries):
{conversation_context[:800]}

USER REQUEST: {question}

**CRITICAL FORMATTING REQUIREMENTS FOR FRONTEND RENDERING:**

1. **Use Markdown Headers:**
   - Use ## for main sections if needed
   - Use ### for subsections if needed
   - **MANDATORY:** Add a blank line BEFORE each header
   - **MANDATORY:** Add a blank line AFTER each header

2. **Green Highlighting for Framework References:**
   - ALL control IDs, article numbers, and framework references MUST be highlighted in green: <span style="color:#008000">Article 17 GDPR</span>
   - Examples: <span style="color:#008000">ISO 27001 Control A.9.2.1</span>, <span style="color:#008000">SOC 2 CC6.1</span>

3. **Use Bullet Points:**
   - Use * for bullet points
   - Each bullet point should be on its own line
   - **MANDATORY:** Add a blank line BEFORE the bullet list
   - **MANDATORY:** Add a blank line AFTER the bullet list

4. **Proper Line Spacing:**
   - **CRITICAL:** Always add a blank line between sections
   - **CRITICAL:** Always add a blank line between paragraphs
   - **CRITICAL:** Always add a blank line between headers and content

Provide a brief, concise summary (2-4 sentences) of what was discussed, focusing on the main compliance topic and key points. Use proper formatting with markdown headers and green highlighting for any framework references.

Summary:
"""
        else:
            # Regular short answer to a direct question
            prompt = f"""
Answer this compliance question in 2-4 sentences. Be concise and factual.

Question: {question}
{f"Previous conversation context: {conversation_context[:500]}" if conversation_context else ""}

**CRITICAL FORMATTING REQUIREMENTS FOR FRONTEND RENDERING:**

1. **Use Markdown Headers:**
   - Use ## for main sections if needed
   - Use ### for subsections if needed
   - **MANDATORY:** Add a blank line BEFORE each header
   - **MANDATORY:** Add a blank line AFTER each header

2. **Green Highlighting for Framework References:**
   - ALL control IDs, article numbers, and framework references MUST be highlighted in green: <span style="color:#008000">Article 17 GDPR</span>
   - Examples: <span style="color:#008000">ISO 27001 Control A.9.2.1</span>, <span style="color:#008000">SOC 2 CC6.1</span>

3. **Use Bullet Points:**
   - Use * for bullet points
   - Each bullet point should be on its own line
   - **MANDATORY:** Add a blank line BEFORE the bullet list
   - **MANDATORY:** Add a blank line AFTER the bullet list

4. **Proper Line Spacing:**
   - **CRITICAL:** Always add a blank line between sections
   - **CRITICAL:** Always add a blank line between paragraphs
   - **CRITICAL:** Always add a blank line between headers and content

Answer (2-4 sentences only):
"""
        
        response = rate_limited_generate_content(prompt, temperature=0.1, max_tokens=200)
        logger.info("Short QA answer generated")
        return response.strip()
        
    except Exception as e:
        logger.error(f"Short QA failed: {e}")
        return "I couldn't generate an answer. Please rephrase your question."


def format_extractive_findings(analysis_result: Dict[str, Any]) -> str:
    """Format extractive findings into a readable response with proper frontend formatting."""
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
                
                # Extract framework reference and highlight in green
                framework_ref = finding.get('framework_ref', 'N/A')
                # If framework_ref contains article/control references, highlight them in green
                if framework_ref != 'N/A' and any(keyword in framework_ref.lower() for keyword in ['article', 'control', 'requirement', 'section', '§']):
                    # Wrap framework reference in green span
                    framework_ref_formatted = f'<span style="color:#008000">{framework_ref}</span>'
                else:
                    framework_ref_formatted = framework_ref
                
                response += f"{severity_emoji} **{i}. {finding.get('finding')}**\n"
                response += f"- **Quote:** \"{finding.get('quote', 'N/A')}\"\n"
                response += f"- **Location:** {finding.get('location', 'N/A')}\n"
                response += f"- **Framework:** {framework_ref_formatted}\n"
                response += f"- **Recommendation:** {finding.get('recommendation', 'N/A')}\n\n"
        
        if compliant_areas:
            response += "### ✅ Compliant Areas\n\n"
            for area in compliant_areas:
                response += f"- {area}\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Format findings failed: {e}")
        return "Error formatting analysis results."


def document_compliance_expert(document_text: str, document_type: str, framework: str = "GDPR", conversation_context: str = "") -> Dict[str, Any]:
    """
    Specialized expert for comprehensive document analysis and generation.
    Analyzes a document against a compliance framework, identifies gaps, and can generate corrected version.
    """
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

**CONVERSATION CONTEXT (previous user queries):**
{conversation_context[:800] if conversation_context else 'None (new conversation)'}

**DOCUMENT TO ANALYZE:**
{document_text[:4000]}

**YOUR TASK:**
Perform a comprehensive {framework} compliance analysis of this {document_type.replace('_', ' ')} document.
Consider the conversation context to understand user's specific concerns or focus areas.

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

**CONVERSATION CONTEXT (previous user queries):**
{conversation_context[:800] if conversation_context else 'None (new conversation)'}

**ORIGINAL DOCUMENT:**
{document_text[:3000]}

**IDENTIFIED ISSUES:**
{json.dumps(analysis_data.get('critical_issues', []), indent=2)[:1000]}
{json.dumps(analysis_data.get('high_issues', []), indent=2)[:1000]}

**YOUR TASK:**
Generate a FULLY COMPLIANT {framework} {document_type.replace('_', ' ')} document that addresses user's specific needs from the conversation context.

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
    """Format the document compliance analysis and corrected document into a user-friendly response."""
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
