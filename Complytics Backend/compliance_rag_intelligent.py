"""
Intelligent Expert Routing System
Implements ChatGPT-like intelligent routing based on query complexity and intent
"""

import logging
import re
from typing import Dict, List, Tuple, Any
from compliance_rag import rate_limited_generate_content_optimized

logger = logging.getLogger(__name__)


def detect_query_type(query: str) -> str:
    """
    Detect the type of query: factual, comparison, explanation, implementation, analysis
    """
    query_lower = query.lower().strip()
    
    # Comparison queries
    comparison_keywords = ['differ', 'difference', 'compare', 'comparison', 'vs', 'versus', 
                          'between', 'contrast', 'similar', 'different']
    if any(keyword in query_lower for keyword in comparison_keywords):
        return 'comparison'
    
    # Implementation queries
    implementation_keywords = ['how to', 'how do i', 'how should i', 'how can i', 
                             'implement', 'configure', 'set up', 'guide me', 
                             'steps to', 'process to', 'achieve', 'certify']
    if any(keyword in query_lower for keyword in implementation_keywords):
        return 'implementation'
    
    # Analysis queries
    analysis_keywords = ['analyze', 'analysis', 'review', 'assess', 'evaluate', 
                        'check', 'audit', 'examine']
    if any(keyword in query_lower for keyword in analysis_keywords):
        return 'analysis'
    
    # Explanation queries
    explanation_keywords = ['explain', 'describe', 'what is', 'what are', 
                          'tell me about', 'overview', 'understand']
    if any(keyword in query_lower for keyword in explanation_keywords):
        return 'explanation'
    
    # Factual queries (default)
    return 'factual'


def analyze_complexity(query: str, conversation_context: str = "") -> str:
    """
    Analyze query complexity: simple, medium, complex
    """
    query_lower = query.lower()
    
    # Count frameworks mentioned
    frameworks = ['gdpr', 'ccpa', 'hipaa', 'iso 27001', 'iso27001', 'soc 2', 'soc2', 
                  'nist', 'pci dss', 'pci-dss', 'sox']
    framework_count = sum(1 for fw in frameworks if fw in query_lower)
    
    # Count technical concepts
    technical_keywords = ['implement', 'configure', 'encryption', 'authentication', 
                         'access control', 'firewall', 'network', 'infrastructure',
                         'architecture', 'deployment', 'integration']
    technical_count = sum(1 for kw in technical_keywords if kw in query_lower)
    
    # Check for implementation/scenario keywords
    implementation_keywords = ['how to', 'steps', 'process', 'guide', 'achieve', 
                              'certify', 'comply', 'setup', 'configure']
    has_implementation = any(kw in query_lower for kw in implementation_keywords)
    
    # Check query length and structure
    word_count = len(query.split())
    
    # Complexity scoring
    complexity_score = 0
    
    # Framework count adds complexity
    complexity_score += framework_count * 2
    
    # Technical keywords add complexity
    complexity_score += technical_count
    
    # Implementation queries are complex
    if has_implementation:
        complexity_score += 5
    
    # Longer queries tend to be more complex
    if word_count > 15:
        complexity_score += 2
    elif word_count > 25:
        complexity_score += 4
    
    # Determine complexity level
    if complexity_score <= 2:
        return 'simple'
    elif complexity_score <= 6:
        return 'medium'
    else:
        return 'complex'


def has_implementation_keywords(query: str) -> bool:
    """Check if query contains implementation keywords"""
    query_lower = query.lower()
    implementation_keywords = [
        'how to', 'how do i', 'how should i', 'how can i',
        'implement', 'configure', 'set up', 'setup', 'guide me',
        'steps to', 'process to', 'achieve', 'certify', 'comply',
        'deploy', 'install', 'integrate', 'build', 'create'
    ]
    return any(kw in query_lower for kw in implementation_keywords)


def intelligent_expert_routing(query: str, conversation_context: str = "", 
                               framework: str = "general") -> Dict[str, Any]:
    """
    Intelligent expert routing based on query type, complexity, and intent.
    Returns routing decision with expert type and reasoning.
    """
    # Step 1: Detect query type
    query_type = detect_query_type(query)
    
    # Step 2: Analyze complexity
    complexity = analyze_complexity(query, conversation_context)
    
    # Step 3: Check for implementation keywords
    is_implementation = has_implementation_keywords(query)
    
    # Step 4: Intelligent routing decision
    routing_decision = {
        'expert_type': 'general',
        'reasoning': '',
        'query_type': query_type,
        'complexity': complexity,
        'is_implementation': is_implementation
    }
    
    # Routing logic
    if query_type == 'comparison':
        # Comparisons always go to general expert for balanced view
        routing_decision['expert_type'] = 'general'
        routing_decision['reasoning'] = 'Comparison query - general expert provides balanced comparison'
        
    elif query_type == 'factual' and complexity == 'simple':
        # Simple factual questions go to general expert
        routing_decision['expert_type'] = 'general'
        routing_decision['reasoning'] = 'Simple factual query - general expert sufficient'
        
    elif query_type == 'explanation' and complexity == 'simple' and not is_implementation:
        # Simple explanations go to general expert
        routing_decision['expert_type'] = 'general'
        routing_decision['reasoning'] = 'Simple explanation query - general expert sufficient'
        
    elif query_type == 'analysis':
        # Analysis queries need specialized experts
        routing_decision['expert_type'] = 'specialized'
        routing_decision['reasoning'] = 'Analysis query requires specialized expert knowledge'
        
    elif is_implementation or complexity == 'complex':
        # Implementation and complex queries need specialized experts
        routing_decision['expert_type'] = 'specialized'
        routing_decision['reasoning'] = 'Implementation/complex query requires specialized expert'
        
    elif complexity == 'medium' and not is_implementation:
        # Medium complexity without implementation can use domain expert
        routing_decision['expert_type'] = 'domain'
        routing_decision['reasoning'] = 'Medium complexity query - domain expert appropriate'
        
    else:
        # Default to general expert
        routing_decision['expert_type'] = 'general'
        routing_decision['reasoning'] = 'Default routing to general expert'
    
    logger.info(f"Intelligent routing: {routing_decision['expert_type']} - {routing_decision['reasoning']}")
    return routing_decision


def expert_general_compliance(query: str, context: str = "", conversation_context: str = "", 
                             framework: str = "general") -> str:
    """
    General compliance expert for simple, factual, and comparison queries.
    Provides balanced, concise answers without deep technical implementation details.
    Uses FAISS context when available, falls back to general knowledge.
    """
    print("\n" + "="*80)
    print("💡 GENERAL COMPLIANCE EXPERT TRIGGERED")
    print(f"Query: {query[:100]}...")
    print("="*80 + "\n")
    logger.info(f"💡 GENERAL EXPERT triggered for query: {query[:100]}")
    
    query_type = detect_query_type(query)
    has_framework_docs = context and len(context.strip()) > 200
    
    if query_type == 'comparison':
        if has_framework_docs:
            prompt = f"""You are a compliance expert providing a balanced comparison of compliance frameworks and regulations.

Previous conversation context:
{conversation_context}

Query: {query}

COMPLIANCE FRAMEWORK DOCUMENTS:
{context}

CRITICAL INSTRUCTIONS:
1. If relevant information exists in the documents, cite it using format: [Information] (Evidence: <span style="color:#008000">"exact quote"</span> - <span style="color:#008000">Framework/Section</span>)
2. ALWAYS highlight document-derived evidence AND framework references in green using <span style="color:#008000">text</span>
3. If no relevant information exists in the documents, use your expert knowledge to provide a complete answer
4. NEVER say "not in documents", "not available", "there is no direct mention", or explain what's missing. Simply provide the information from your knowledge.
5. Provide a balanced, objective comparison using both document evidence (when available) and your expert knowledge

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

INSTRUCTIONS:
1. Provide a balanced, objective comparison
2. Highlight key differences clearly
3. Use structured format with clear sections
4. Be concise but comprehensive
5. Focus on practical differences, not just theoretical
6. If comparing frameworks (e.g., HIPAA vs GDPR), cover:
   - Scope and applicability
   - Key requirements differences
   - Enforcement and penalties
   - Practical implementation differences

Format your response with clear headings and bullet points. Be professional and accurate.

Provide a direct, balanced comparison:"""
        else:
            # No framework docs - use general knowledge
            prompt = f"""You are a compliance expert providing a balanced comparison of compliance frameworks and regulations.

Previous conversation context:
{conversation_context}

Query: {query}

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

INSTRUCTIONS:
1. Provide a balanced, objective comparison
2. Highlight key differences clearly
3. Use structured format with clear sections
4. Be concise but comprehensive
5. Focus on practical differences, not just theoretical
6. If comparing frameworks (e.g., HIPAA vs GDPR), cover:
   - Scope and applicability
   - Key requirements differences
   - Enforcement and penalties
   - Practical implementation differences

Format your response with clear headings and bullet points. Be professional and accurate.

Provide a direct, balanced comparison:"""
    
    elif query_type == 'factual' or query_type == 'explanation':
        if has_framework_docs:
            prompt = f"""You are a compliance expert providing clear, factual answers about compliance frameworks and regulations.

Previous conversation context:
{conversation_context}

Query: {query}

COMPLIANCE FRAMEWORK DOCUMENTS:
{context}

CRITICAL INSTRUCTIONS:
1. If relevant information exists in the documents, cite it using format: [Information] (Evidence: <span style="color:#008000">"exact quote"</span> - <span style="color:#008000">Framework/Section</span>)
2. ALWAYS highlight document-derived evidence AND framework references in green using <span style="color:#008000">text</span>
3. If no relevant information exists in the documents, use your expert knowledge to provide a complete answer
4. NEVER say "not in documents", "not available", "there is no direct mention", "not in my knowledge", or explain what's missing. Simply provide the information from your knowledge.
5. Always provide a COMPLETE answer using both document evidence (when available) and your expert knowledge

**CRITICAL FORMATTING REQUIREMENTS FOR FRONTEND RENDERING:**

1. **Use Markdown Headers:**
   - Use ## for main sections
   - Use ### for subsections
   - Use #### for sub-subsections

2. **Green Highlighting for Framework References:**
   - ALL control IDs, article numbers, and framework references MUST be highlighted in green: <span style="color:#008000">Article 17 GDPR</span>
   - Examples:
     * <span style="color:#008000">ISO 27001 Control A.9.2.1</span>
     * <span style="color:#008000">SOC 2 CC6.1</span>
     * <span style="color:#008000">HIPAA §164.312(a)(1)</span>
     * <span style="color:#008000">PCI DSS Requirement 1.1</span>

3. **Use Bullet Points:**
   - Use * for bullet points
   - Use - for sub-bullets
   - Each bullet point should be on its own line

INSTRUCTIONS:
1. Provide clear, accurate information
2. Be concise but comprehensive
3. Use structured format with headings
4. Focus on key concepts and requirements
5. Include relevant framework references when appropriate (with green highlighting)
6. Highlight important points clearly

Format your response with clear headings and bullet points. Be professional and educational.

Provide a direct, informative answer:"""
        else:
            # No framework docs - use general knowledge
            prompt = f"""You are a compliance expert providing clear, factual answers about compliance frameworks and regulations.

Previous conversation context:
{conversation_context}

Query: {query}

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

INSTRUCTIONS:
1. Provide clear, accurate information
2. Be concise but comprehensive
3. Use structured format with headings
4. Focus on key concepts and requirements
5. Include relevant framework references when appropriate (with green highlighting)
6. Highlight important points clearly

Format your response with clear headings and bullet points. Be professional and educational.

Provide a direct, informative answer:"""
    
    else:
        if has_framework_docs:
            prompt = f"""You are a compliance expert providing general compliance guidance.

Previous conversation context:
{conversation_context}

Query: {query}

COMPLIANCE FRAMEWORK DOCUMENTS:
{context}

CRITICAL INSTRUCTIONS:
1. If relevant information exists in the documents, cite it using format: [Information] (Evidence: <span style="color:#008000">"exact quote"</span> - <span style="color:#008000">Framework/Section</span>)
2. ALWAYS highlight document-derived evidence AND framework references in green using <span style="color:#008000">text</span>
3. If no relevant information exists in the documents, use your expert knowledge to provide a complete answer
4. NEVER say "not in documents", "not available", "there is no direct mention", "not in my knowledge", or explain what's missing. Simply provide the information from your knowledge.
5. Always provide a COMPLETE answer using both document evidence (when available) and your expert knowledge

**CRITICAL FORMATTING REQUIREMENTS FOR FRONTEND RENDERING:**

1. **Use Markdown Headers:**
   - Use ## for main sections
   - Use ### for subsections
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

Provide a clear, concise, and informative answer about compliance topics. Use structured format with headings and bullet points. Be professional and accurate.

Answer:"""
        else:
            # No framework docs - use general knowledge
            prompt = f"""You are a compliance expert providing general compliance guidance.

Previous conversation context:
{conversation_context}

Query: {query}

**CRITICAL FORMATTING REQUIREMENTS FOR FRONTEND RENDERING:**

1. **Use Markdown Headers:**
   - Use ## for main sections
   - Use ### for subsections
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

Provide a clear, concise, and informative answer about compliance topics. Use structured format with headings and bullet points. Be professional and accurate.

Answer:"""
    
    return rate_limited_generate_content_optimized(prompt, temperature=0.1, max_tokens=1000)


def select_domain_expert(query: str, framework: str = "general") -> str:
    """
    Select appropriate domain expert based on framework and query content.
    Returns expert type: 'privacy', 'healthcare', 'audit', 'financial', 'security'
    """
    query_lower = query.lower()
    
    # Framework-based routing
    if 'hipaa' in query_lower or 'phi' in query_lower or 'protected health' in query_lower:
        return 'healthcare'
    
    if 'gdpr' in query_lower or 'ccpa' in query_lower or 'privacy' in query_lower or 'data protection' in query_lower:
        return 'privacy'
    
    if 'pci' in query_lower or 'sox' in query_lower or 'financial' in query_lower:
        return 'financial'
    
    if 'azure' in query_lower or 'identity' in query_lower or 'authentication' in query_lower:
        return 'security'
    
    if 'iso' in query_lower or 'soc' in query_lower or 'nist' in query_lower or 'audit' in query_lower:
        return 'audit'
    
    # Default based on framework
    framework_lower = framework.lower()
    if 'hipaa' in framework_lower:
        return 'healthcare'
    elif 'gdpr' in framework_lower or 'ccpa' in framework_lower:
        return 'privacy'
    elif 'pci' in framework_lower or 'sox' in framework_lower:
        return 'financial'
    elif 'iso' in framework_lower or 'soc' in framework_lower:
        return 'audit'
    
    # Default to audit for general compliance
    return 'audit'


