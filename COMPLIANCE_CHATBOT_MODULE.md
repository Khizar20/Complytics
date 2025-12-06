# Compliance Chatbot Module - Complete Documentation (Roman Urdu)

## Module Ka Naam
**Compliance Chatbot Module** - Ye ek AI-powered intelligent chatbot hai jo compliance frameworks (GDPR, ISO 27001, SOC 2, HIPAA, PCI DSS, NIST, CCPA, ISO 13485, DRAP, etc.) ke baare mein sawaal ka intelligent jawab deta hai.

---

## Story Time: Compliance Chatbot Ko Compliance Officer Kaise Use Karta Hai?

Sochiye ke Ayesha ek compliance officer hai jo ek fintech startup mein kaam karti hai. Company ko multiple compliance frameworks follow karne hain - GDPR (European customers ke liye), PCI DSS (payment processing ke liye), ISO 27001 (security ke liye), aur SOC 2 (enterprise customers ko satisfy karne ke liye). CEO ne usay kaha: "Ayesha, humein agle quarter mein SOC 2 Type II certification chahiye. Timeline tight hai, aur humein quickly samajhna hoga ke kya requirements hain aur kaise implement karna hai."

Ayesha ka typical workflow kuch is tarah hota hai:

1. **Initial Research & Understanding**  
   - Wo Compliance Chatbot module open karti hai.  
   - Pehle wo general question puchti hai: "What is SOC 2 Type II certification?"  
   - Chatbot intelligently detect karta hai ke ye SOC 2 related query hai aur Audit Compliance Expert ko route karta hai.  
   - Response mein detailed explanation milta hai: SOC 2 ke types (Type I vs Type II), Trust Service Criteria (Security, Availability, Processing Integrity, Confidentiality, Privacy), aur certification process.  
   - Har control ID green highlight mein hota hai (jaise <span style="color:#008000">SOC 2 CC6.1</span>) taake Ayesha easily reference kar sake.

2. **Framework Comparison & Decision Making**  
   - Ayesha ko samajhna hai ke SOC 2 aur ISO 27001 mein kya difference hai.  
   - Wo puchti hai: "What's the difference between SOC 2 and ISO 27001?"  
   - Chatbot intelligent expert routing se dono frameworks ke experts ko consult karta hai.  
   - Response mein comparison table milta hai: Scope, focus areas, certification process, validity period, etc.  
   - Evidence-based answers milte hain - har point ke saath exact control IDs aur requirements cite hote hain.

3. **Implementation Guidance**  
   - Ab Ayesha ko practical implementation chahiye.  
   - Wo puchti hai: "How should we achieve SOC 2 Type II certification? Guide us step by step."  
   - Chatbot intent classify karta hai: `SCENARIO_GUIDANCE`  
   - Scenario Guidance Expert activate hota hai.  
   - Response mein structured 8-step implementation plan milta hai:
     * Step 1: Gap analysis (with specific controls to check)
     * Step 2: Control implementation (with AWS/Azure specific recommendations)
     * Step 3: Documentation preparation
     * Step 4: Internal audit
     * Step 5: External audit preparation
     * Step 6: Audit execution
     * Step 7: Remediation
     * Step 8: Certification maintenance
   - Har step mein specific controls cite hote hain jo implement karne hain.

4. **Document Review & Compliance Checking**  
   - Ayesha ne apni company ki existing security policy document upload ki hai.  
   - Wo chatbot se puchti hai: "Check if my document covers SOC 2 requirements."  
   - Chatbot document ko analyze karta hai, FAISS se relevant SOC 2 controls retrieve karta hai, aur comparison karta hai.  
   - Response mein milta hai:
     * ✅ Covered requirements (with evidence from document)
     * ❌ Missing requirements (with specific control IDs)
     * 📝 Improvement suggestions (actionable recommendations)
   - Ayesha ko clearly pata chal jata hai ke kya add karna hai.

5. **Follow-up Queries & Context Understanding**  
   - Ayesha follow-up question puchti hai: "What about the monitoring controls for this framework?"  
   - Chatbot intelligently detect karta hai ke "this framework" se SOC 2 ka reference hai (conversation context se).  
   - Framework resolution ho jata hai: "this framework" → "SOC 2"  
   - Response mein SOC 2 ke monitoring controls detail mein milte hain (CC7.1, CC7.2, etc.) with evidence.

6. **Quick Clarifications**  
   - Ayesha ko kisi specific control ke baare mein quick clarification chahiye.  
   - Wo puchti hai: "Tell me briefly about SOC 2 CC6.1"  
   - Chatbot short answer expert activate karta hai.  
   - Concise 2-3 sentence answer milta hai jo exactly CC6.1 ko explain karta hai.

7. **Multi-Framework Questions**  
   - Ayesha ko GDPR aur PCI DSS dono ke baare mein puchna hai.  
   - Wo puchti hai: "What are the data encryption requirements for GDPR and PCI DSS?"  
   - Chatbot multiple experts ko route karta hai: Privacy Expert (GDPR) + Financial Expert (PCI DSS).  
   - Responses aggregate hote hain - dono frameworks ke requirements clearly separate sections mein milte hain.  
   - Har requirement ke saath evidence cite hota hai.

8. **Document Generation**  
   - Ayesha ko privacy policy generate karni hai GDPR compliance ke liye.  
   - Wo puchti hai: "Create a GDPR-compliant privacy policy for our fintech company."  
   - Chatbot Privacy Expert + Audit Expert dono ko activate karta hai.  
   - Response mein complete privacy policy template milta hai with:
     * Required sections (Article 13 GDPR requirements)
     * Data controller information
     * Legal basis for processing
     * Data subject rights
     * Contact information
   - Template ready-to-use format mein hota hai.

**Outcome:** Ayesha ko manual research karne ki zarurat nahi padti. Ye chatbot usay ek intelligent, context-aware assistant de deta hai jo:
- ✅ Semantic understanding se queries ko samajhta hai (keyword matching nahi)
- ✅ Evidence-based answers deta hai (documents se exact quotes)
- ✅ Multiple frameworks ko simultaneously handle karta hai
- ✅ Context maintain karta hai (follow-up queries ko intelligently handle karta hai)
- ✅ Practical implementation guidance deta hai (step-by-step plans)
- ✅ Document analysis karke compliance gaps identify karta hai

Jab auditor poochta hai, "Aapne SOC 2 requirements kaise identify kiye?", Ayesha confidently bol sakti hai: "Humne Compliance Chatbot use kiya jo RAG system se documents se evidence retrieve karke comprehensive answers diye. Ye responses documented hain aur har control ID ke saath evidence cite hai."

**Key Differentiator:** Ye chatbot sirf keyword matching nahi karta - ye pure semantic understanding use karta hai. Agar Ayesha puchti hai "data protection rules for european customers", chatbot intelligently detect karta hai ke ye GDPR related query hai, even if "GDPR" word explicitly mention nahi hua.

---

## Complete Flow Kaise Kaam Karta Hai?

### Step 1: User Query Receive Karna
- User frontend se query bhejta hai (`/api/compliance/chat` endpoint par)
- System query ko receive karta hai aur session ID ke saath track karta hai
- File: `routes/compliance.py` → `compliance_chat()` function

### Step 2: Non-Compliance Guardrails Check
- **Function**: `check_compliance_guardrails()` (compliance_rag_refined.py)
- **Kaise Kaam Karta Hai**: 
  - LLM use karke semantically check karta hai ke query compliance-related hai ya nahi
  - Keyword-based matching NAHI hota, pure semantic understanding hota hai
  - Agar query non-compliance related hai (jaise cooking, movies, games), to politely decline karta hai
  - Response JSON format mein aata hai: `{"is_compliance": true/false, "reason": "...", "confidence": 0.0-1.0}`
- **Prompting Technique**: Classification prompt jo LLM ko clearly define karta hai ke compliance-related kya hai aur kya nahi

### Step 3: Ambiguous Query Detection
- **Function**: `handle_ambiguous_query()` (compliance_rag_refined.py)
- **Kaise Kaam Karta Hai**:
  - LLM use karke check karta hai ke query clear hai ya unclear
  - Agar query ambiguous hai (jaise sirf "costs" ya "help" without context), to clarification mangta hai
  - Conversation context ko use karta hai - agar context mein framework mention hai, to query ko NOT ambiguous mark karta hai
  - Follow-up queries ko intelligently handle karta hai (jaise "medical devices and they sell all over pakistan" after "medicines in pakistan")
- **Prompting Technique**: 
  - Strict rules define kiye gaye hain ke kya ambiguous hai aur kya nahi
  - Examples diye gaye hain LLM ko samajhne ke liye
  - Context-aware detection - agar conversation context hai, to query ko clear consider karta hai

### Step 4: Cache Check (Intelligent Caching)
- **Function**: `process_compliance_query_unified()` mein cache check
- **Kaise Kaam Karta Hai**:
  - Query ko normalize karta hai (lowercase, strip whitespace)
  - MD5 hash create karta hai: `hash_text(query_normalized)`
  - Cache key format: `exact_query:{hash}`
  - Agar exact match milta hai `query_cache.json` mein, to cached response return karta hai
  - **Important**: Sirf "proper compliance questions" cache hote hain:
    - ✅ Cache hota hai: "what is gdpr", "what is iso 27001", "explain soc 2"
    - ❌ Cache NAHI hota: Document-specific queries, follow-up summary requests ("tell in short"), ambiguous queries
  - Cache file location: `compliance_cache/query_cache.json`
  - Cache save hota hai har response ke baad immediately

### Step 5: Intent Classification (Intelligent, LLM-based)
- **Function**: `intelligent_intent_classification()` (compliance_rag_refined.py)
- **Kaise Kaam Karta Hai**:
  - LLM use karke query ka intent classify karta hai
  - Keyword-based matching NAHI hota, pure semantic understanding
  - Intent categories:
    1. **USE_MAIN_EXPERTS**: General compliance questions (GDPR, ISO 27001, etc.)
    2. **DOC_ANALYSIS**: Document analysis request (only if document uploaded)
    3. **DOC_GENERATION**: Document generation request (privacy policy, terms)
    4. **DOC_SUMMARY**: Document summary request
    5. **SCENARIO_GUIDANCE**: Step-by-step implementation guidance
    6. **GENERAL_QA_SHORT**: Brief/short answer request ("tell in short")
    7. **NON_COMPLIANCE**: Non-compliance queries (handled by guardrails)
    8. **AMBIGUOUS**: Unclear queries (handled by ambiguous query detection)
- **Prompting Technique**:
  - Detailed prompt jo har intent category ko clearly define karta hai
  - Examples diye gaye hain har category ke liye
  - Conversation context ko consider karta hai
  - Framework detection bhi hota hai (GDPR, ISO 27001, etc.)

### Step 6: Document Reference Check (Intelligent)
- **Function**: `intelligent_document_reference_check()` (compliance_rag_refined.py)
- **Kaise Kaam Karta Hai**:
  - LLM use karke check karta hai ke user document ki baat kar raha hai ya nahi
  - Negative statements detect karta hai (jaise "I didn't upload the document")
  - Agar document upload nahi hai aur user document ki baat kare, to upload karne ko kehta hai
- **Prompting Technique**: Semantic understanding prompt jo document references ko detect karta hai

### Step 7: Framework Resolution (Intelligent)
- **Function**: `intelligent_framework_resolution()` (compliance_rag_refined.py)
- **Kaise Kaam Karta Hai**:
  - Conversation context se framework resolve karta hai
  - Agar query mein "this framework" ya "it" hai, to context se framework identify karta hai
  - Example: Query "which companies should implement this framework" + Context "what is iso 27001" → Returns "ISO 27001"
- **Prompting Technique**: Context-aware resolution prompt

### Step 8: Expert Routing (Intelligent)
- **Function**: `intelligent_expert_routing()` (compliance_rag_refined.py)
- **Kaise Kaam Karta Hai**:
  - LLM use karke relevant experts ko select karta hai
  - Keyword-based routing NAHI hota, semantic understanding hota hai
  - Multiple experts select ho sakte hain agar query multi-domain hai
- **Expert Types**:
  1. **general**: General compliance guidance (compliance_rag_intelligent.py)
  2. **security**: Security controls expert (compliance_rag.py)
  3. **privacy**: Privacy regulations expert (GDPR, CCPA) (compliance_rag.py)
  4. **audit**: Audit compliance expert (ISO 27001, SOC 2) (compliance_rag.py)
  5. **financial**: Financial compliance expert (PCI DSS, SOX) (compliance_rag.py)
  6. **healthcare**: Healthcare compliance expert (HIPAA) (compliance_rag.py)
  7. **international**: International compliance expert (compliance_rag.py)
  8. **operational**: Operational compliance expert (compliance_rag.py)
  9. **industry_specific**: Industry-specific compliance expert (compliance_rag.py)

### Step 9: Query to Embeddings Conversion
- **Function**: `get_embedding_optimized()` (compliance_rag.py)
- **Kaise Kaam Karta Hai**:
  1. **Model**: SentenceTransformer model use hota hai: `'all-MiniLM-L6-v2'`
  2. **Process**:
     - Query text ko model mein pass kiya jata hai
     - Model query ko 384-dimensional vector mein convert karta hai
     - Ye vector semantic meaning capture karta hai
  3. **Caching**: Embeddings cache hote hain performance ke liye
  4. **Usage**: 
     - Query embedding create hota hai
     - FAISS index mein similarity search hota hai
     - Top 3 most similar document segments retrieve hote hain

### Step 10: FAISS Index Search
- **Function**: `search_documents()` (compliance_rag.py)
- **Kaise Kaam Karta Hai**:
  1. Query embedding ko FAISS index mein search kiya jata hai
  2. **FAISS Index Structure**:
     - Index file: `faiss_indexes/compliance_index.faiss`
     - Document segments ki embeddings store hote hain
     - Fast similarity search ke liye optimized
  3. **Search Process**:
     - Query embedding ko FAISS mein search kiya jata hai
     - Top K (usually 3) most similar segments retrieve hote hain
     - Cosine similarity use hoti hai
  4. **Retrieved Context**: Top segments ko join karke context banaya jata hai

### Step 11: Expert Response Generation
- Har expert apne specialized prompt ke saath response generate karta hai
- **Prompting Techniques** (detailed below):
  - Evidence-based prompting
  - Chain-of-thought reasoning
  - Context-aware generation
  - Formatting instructions

### Step 12: Response Aggregation (if multiple experts)
- **Function**: `aggregate_expert_outputs()` (compliance_rag.py)
- **Kaise Kaam Karta Hai**:
  - Agar multiple experts select hue hain, to unke responses ko aggregate karta hai
  - Duplicate information remove karta hai
  - Structured format mein organize karta hai (Executive Summary, Key Compliance Mapping, Implementation Plan, etc.)

### Step 13: Response Caching
- **Function**: `process_compliance_query_unified()` mein caching logic
- **Kaise Kaam Karta Hai**:
  - Agar query cacheable hai (not document-specific, not follow-up summary), to cache mein save hota hai
  - Cache key: `exact_query:{hash}`
  - Response immediately `query_cache.json` mein save hota hai

### Step 14: Response Return
- Final response user ko return hota hai
- Response format:
  ```json
  {
    "response": "...",
    "experts_consulted": ["privacy", "audit"],
    "is_compliance": true,
    "needs_clarification": false,
    "clarification_message": ""
  }
  ```

---

## Context Management Kaise Kaam Karta Hai?

### IntelligentConversationHistory Class
- **File**: `compliance_rag_refined.py`
- **Class**: `IntelligentConversationHistory`
- **Kaise Kaam Karta Hai**:
  1. **Storage**: Sirf user queries store hote hain (bot responses NAHI)
  2. **Limit**: Maximum 50 queries store hote hain
  3. **Timeout**: 3600 seconds (1 hour) - agar timeout ho jaye, to history reset ho jati hai
  4. **Context Building**:
     - Recent 10 queries ko context mein use kiya jata hai
     - Context string banaya jata hai: `" ".join(recent_queries)`
  5. **Pending Clarification**: Track karta hai ke clarification pending hai ya nahi
  6. **Methods**:
     - `add_user_query()`: Query add karta hai
     - `get_context()`: Context string return karta hai
     - `get_all_queries()`: All queries return karta hai
     - `reset()`: History reset karta hai
     - `set_pending_clarification()`: Clarification message set karta hai
     - `clear_pending_clarification()`: Clarification clear karta hai

### Context Usage
- Context har expert prompt mein include hota hai
- Format: `Previous conversation context: {conversation_context}`
- Context se:
  - Framework resolution hota hai ("this framework" → actual framework name)
  - Follow-up queries ko understand kiya jata hai
  - Ambiguous queries ko clarify kiya jata hai

---

## Cache System Kaise Kaam Karta Hai?

### Cache Structure
- **File**: `compliance_cache/query_cache.json`
- **Format**: JSON dictionary
- **Keys**: 
  - `exact_query:{hash}`: Exact query match ke liye
  - `context_query:{query_hash}:{context_hash}:{conv_hash}`: Context-dependent queries ke liye

### Cache Logic
1. **Cache Check**:
   - Query ko normalize kiya jata hai (lowercase, strip)
   - MD5 hash create hota hai
   - Cache key: `exact_query:{hash}`
   - Agar match milta hai, to cached response return hota hai

2. **Cache Storage**:
   - Sirf cacheable queries cache hote hain:
     - ✅ Cache hota hai: "what is gdpr", "explain iso 27001"
     - ❌ Cache NAHI hota: Document-specific queries, follow-up summaries, ambiguous queries
   - Response immediately cache mein save hota hai

3. **Cache Saving**:
   - Function: `save_query_cache()` (compliance_rag.py)
   - Har response ke baad immediately save hota hai
   - JSON format mein properly formatted

4. **Cache Loading**:
   - Server start par cache file load hota hai
   - Agar file nahi hai, to empty cache start hota hai

### Cache Benefits
- Fast response for repeated queries
- Reduced LLM API calls
- Cost savings
- Better user experience

---

## Query to Embeddings Conversion (Detailed)

### Process
1. **Model Initialization**:
   - Model: `SentenceTransformer('all-MiniLM-L6-v2')`
   - Model size: 384 dimensions
   - Model type: Pre-trained transformer model

2. **Embedding Generation**:
   ```python
   query_embedding = embedding_model.encode(query)
   ```
   - Query text ko model mein pass kiya jata hai
   - Model query ko 384-dimensional vector mein convert karta hai
   - Ye vector semantic meaning capture karta hai

3. **Embedding Properties**:
   - **Dimension**: 384 dimensions
   - **Type**: Float32 numpy array
   - **Normalization**: Usually L2 normalized for cosine similarity

4. **Usage in FAISS**:
   - Query embedding ko FAISS index mein search kiya jata hai
   - Similar document segments retrieve hote hain
   - Cosine similarity use hoti hai

### Document Embeddings
- **File**: `embeddings/document_embeddings.npy`
- **Process**:
  1. Documents ko segments mein divide kiya jata hai (max 1000 characters per segment)
  2. Har segment ka embedding create hota hai
  3. Embeddings numpy array mein store hote hain
  4. FAISS index create hota hai embeddings se

---

## Expert Types aur Unke Prompting Techniques

### 1. General Compliance Expert
- **File**: `compliance_rag_intelligent.py`
- **Function**: `expert_general_compliance()`
- **Prompting Techniques**:
  1. **Context-Aware Prompting**: Conversation context include hota hai
  2. **Evidence-Based Prompting**: Agar FAISS context hai, to evidence cite karta hai
  3. **Knowledge Fallback**: Agar context mein answer nahi hai, to apne knowledge se answer deta hai
  4. **Formatting Instructions**: Markdown headers, green highlighting, bullet points
  5. **Query Type Detection**: Comparison, factual, explanation queries ko differently handle karta hai
- **Key Instructions**:
  - "NEVER say 'not in documents', 'not available', 'not in my knowledge'"
  - "If no relevant information exists in documents, use expert knowledge"
  - "Always provide COMPLETE answer"

### 2. Privacy Regulations Expert
- **File**: `compliance_rag.py`
- **Function**: `expert_privacy_regulations()`
- **Prompting Techniques**:
  1. **Evidence-Based Prompting**: Legal text ko cite karta hai with green highlighting
  2. **Technical Implementation Mapping**: Legal requirements ko technical actions mein translate karta hai
  3. **Lifecycle Alignment**: Agar user data lifecycle puchta hai, to exactly usi order mein answer deta hai
  4. **Tech Stack Specific**: User ke tech stack (AWS, Azure) ke according recommendations deta hai
  5. **Section Skipping**: Agar documents mein relevant info nahi hai, to section skip karta hai (explanation NAHI deta)
- **Key Instructions**:
  - "DO NOT say 'not in documents', 'not available'"
  - "If no relevant information exists, skip the section entirely"
  - "Always highlight article numbers in green: <span style=\"color:#008000\">Article 17 GDPR</span>"

### 3. Audit Compliance Expert
- **File**: `compliance_rag.py`
- **Function**: `expert_audit_compliance()`
- **Prompting Techniques**:
  1. **Paraphrased Evidence**: Natural explanation phle, phir exact quote as evidence
  2. **Control ID Citation**: Control IDs ko green highlight karta hai
  3. **Tech Stack Validation**: User ke tech stack ko validate karta hai
  4. **Evidence Formatting**: Evidence items ko numbered list format mein deta hai
  5. **Implementation Mapping**: Controls ko user ke tech stack se map karta hai
- **Key Instructions**:
  - "Provide NATURAL, PARAPHRASED statement, then cite exact quote"
  - "DO NOT copy exact quote as statement"
  - "Always highlight control IDs in green: <span style=\"color:#008000\">ISO 27001 A.9.2.1</span>"

### 4. Security Controls Expert
- **File**: `compliance_rag.py`
- **Function**: `expert_security_controls()`
- **Prompting Techniques**:
  1. **Technical Focus**: Technical implementation details par focus
  2. **Control Mapping**: Security controls ko specific tools se map karta hai
  3. **Risk-Based Approach**: Risk assessment aur mitigation strategies
  4. **Evidence Collection**: Security logs aur artifacts ke baare mein batata hai
- **Key Instructions**:
  - "Map controls to user's specific tools"
  - "Provide technical implementation details"
  - "Highlight control IDs in green"

### 5. Healthcare Compliance Expert
- **File**: `compliance_rag.py`
- **Function**: `expert_healthcare_compliance()`
- **Prompting Techniques**:
  1. **HIPAA Focus**: HIPAA Privacy and Security Rules par focus
  2. **PHI Protection**: Protected Health Information ke protection methods
  3. **Safeguard Citation**: Administrative, physical, technical safeguards ko cite karta hai
  4. **Implementation Guidance**: Practical implementation steps
- **Key Instructions**:
  - "Cite HIPAA sections with green highlighting"
  - "Provide complete implementation guidance"
  - "DO NOT say 'not in documents'"

### 6. Financial Compliance Expert
- **File**: `compliance_rag.py`
- **Function**: `expert_financial_compliance()`
- **Prompting Techniques**:
  1. **Regulation Focus**: PCI DSS, SOX regulations par focus
  2. **Payment Standards**: Payment card industry standards
  3. **Financial Reporting**: Financial reporting requirements
  4. **Chain-of-Thought**: Step-by-step reasoning
- **Key Instructions**:
  - "Provide regulatory requirements"
  - "Map to payment processing systems"
  - "Highlight requirement IDs in green"

### 7. Scenario Guidance Expert
- **File**: `compliance_rag_refined.py`
- **Function**: `scenario_guidance_expert()`
- **Prompting Techniques**:
  1. **Step-by-Step Structure**: Clear numbered steps
  2. **Implementation Focus**: Practical implementation guidance
  3. **Framework-Specific**: Framework ke according guidance
  4. **Formatting**: Markdown headers, bullet points, proper spacing
- **Key Instructions**:
  - "Max 8 steps"
  - "Each step: cite specific requirements"
  - "Provide actionable guidance"

### 8. Document Compliance Expert
- **File**: `compliance_rag_refined.py`
- **Function**: `document_compliance_expert()`
- **Prompting Techniques**:
  1. **Extractive Analysis**: Document se specific sections extract karta hai
  2. **Compliance Checking**: Framework requirements ke against check karta hai
  3. **Improvement Suggestions**: Missing elements suggest karta hai
  4. **Structured Response**: Analysis, findings, recommendations format
- **Key Instructions**:
  - "Extract specific sections from document"
  - "Check against framework requirements"
  - "Suggest improvements"

### 9. Short QA Answer Expert
- **File**: `compliance_rag_refined.py`
- **Function**: `short_qa_answer()`
- **Prompting Techniques**:
  1. **Concise Format**: Brief, to-the-point answers
  2. **Context Summarization**: Agar follow-up summary request hai, to previous conversation summarize karta hai
  3. **Formatting**: Proper markdown formatting
- **Key Instructions**:
  - "Provide concise answer (2-4 sentences)"
  - "Use conversation context for follow-up queries"
  - "Format with markdown headers"

---

## Common Prompting Techniques Used Across All Experts

### 1. Evidence-Based Prompting
- **Technique**: Documents se evidence cite karna
- **Format**: `[Information] (Evidence: <span style="color:#008000">"exact quote"</span> - <span style="color:#008000">Control ID</span>)`
- **Usage**: Har expert apne context se relevant evidence cite karta hai

### 2. Green Highlighting
- **Technique**: Framework references ko green highlight karna
- **Format**: `<span style="color:#008000">ISO 27001 A.9.2.1</span>`
- **Usage**: Control IDs, Article numbers, Framework names ko highlight karta hai

### 3. Context-Aware Prompting
- **Technique**: Conversation context ko prompt mein include karna
- **Format**: `Previous conversation context: {conversation_context}`
- **Usage**: Follow-up queries ko understand karne ke liye

### 4. Formatting Instructions
- **Technique**: Explicit formatting instructions dena
- **Format**: Markdown headers, bullet points, proper spacing
- **Usage**: Frontend rendering ke liye proper format ensure karna

### 5. Knowledge Fallback
- **Technique**: Agar documents mein answer nahi hai, to expert knowledge use karna
- **Format**: "If no relevant information exists in documents, use expert knowledge"
- **Usage**: Complete answers ensure karne ke liye

### 6. Structured Response Format
- **Technique**: Response ko structured sections mein organize karna
- **Format**: Executive Summary, Key Requirements, Implementation Plan, etc.
- **Usage**: User ko clear, organized information dene ke liye

### 7. Tech Stack Specific Recommendations
- **Technique**: User ke tech stack ke according recommendations dena
- **Format**: "If user is on AWS, recommend AWS KMS"
- **Usage**: Practical, actionable advice dene ke liye

### 8. Negative Instruction Prompting
- **Technique**: Explicitly batana ke kya NAHI karna hai
- **Format**: "DO NOT say 'not in documents'", "DO NOT explain methodology"
- **Usage**: Unwanted behaviors ko prevent karne ke liye

---

## Guardrails System

### Non-Compliance Guardrails
- **Function**: `check_compliance_guardrails()` (compliance_rag_refined.py)
- **Kaise Kaam Karta Hai**:
  1. LLM use karke semantically check karta hai ke query compliance-related hai ya nahi
  2. Compliance-related topics:
     - Compliance frameworks (GDPR, ISO 27001, SOC 2, HIPAA, PCI DSS, NIST, CCPA)
     - Security controls, access management, encryption
     - Privacy regulations, data protection
     - Audit procedures, compliance verification
     - Risk management, governance
     - Regulatory requirements
  3. Non-compliance topics:
     - Personal life (cooking, recipes, entertainment, movies, sports)
     - General knowledge unrelated to compliance
     - Health advice (unless HIPAA/compliance context)
     - Weather, news, current events (unless compliance context)
     - Games, hobbies, personal interests
  4. Response: Politely decline karta hai non-compliance queries ko

### Document Upload Guardrails
- **Function**: `intelligent_document_reference_check()` (compliance_rag_refined.py)
- **Kaise Kaam Karta Hai**:
  1. Check karta hai ke user document ki baat kar raha hai ya nahi
  2. Agar document upload nahi hai aur user document ki baat kare, to upload karne ko kehta hai
  3. Negative statements detect karta hai ("I didn't upload")

---

## Intent Types (Detailed)

### 1. USE_MAIN_EXPERTS
- **Description**: General compliance questions
- **Examples**: "What are GDPR requirements?", "Explain ISO 27001", "How do I implement SOC 2?"
- **Routing**: Intelligent expert routing se relevant experts select hote hain

### 2. DOC_ANALYSIS
- **Description**: Document analysis request
- **Examples**: "Analyze my document", "Check my privacy policy", "Review this file"
- **Requirement**: Document must be uploaded
- **Expert**: Document Compliance Expert

### 3. DOC_GENERATION
- **Description**: Document generation request
- **Examples**: "Create a privacy policy", "Generate GDPR document", "Make me a terms document"
- **Expert**: Privacy + Audit Experts

### 4. DOC_SUMMARY
- **Description**: Document summary request
- **Examples**: "Summarize my document", "What's in this file", "Give me an overview"
- **Requirement**: Document must be uploaded

### 5. SCENARIO_GUIDANCE
- **Description**: Step-by-step implementation guidance
- **Examples**: "How should we achieve SOC 2 certification?", "Guide us through HIPAA compliance"
- **Expert**: Scenario Guidance Expert

### 6. GENERAL_QA_SHORT
- **Description**: Brief/short answer request
- **Examples**: "Tell me briefly", "In short", "Quick answer", "Now tell in short"
- **Expert**: Short QA Answer Expert
- **Special**: Conversation context use hota hai for follow-up summaries

### 7. NON_COMPLIANCE
- **Description**: Non-compliance queries
- **Handling**: Guardrails se handle hota hai

### 8. AMBIGUOUS
- **Description**: Unclear queries
- **Handling**: Ambiguous query detection se handle hota hai

---

## Files Jahan Code Present Hai

### Backend Files (Python)

1. **`Complytics Backend/routes/compliance.py`**
   - Main API routes file
   - `/api/compliance/chat` endpoint
   - `/api/compliance/upload` endpoint
   - `/api/compliance/reset` endpoint
   - Document processing logic
   - Conversation history management

2. **`Complytics Backend/compliance_rag.py`**
   - Core RAG implementation
   - Embedding generation (`get_embedding_optimized()`)
   - FAISS index management
   - Expert functions (privacy, audit, security, financial, healthcare)
   - Query processing functions
   - Document analysis functions
   - Response generation functions
   - Cache management (`QUERY_CACHE`, `save_query_cache()`)

3. **`Complytics Backend/compliance_rag_refined.py`**
   - Unified processing function (`process_compliance_query_unified()`)
   - Intelligent intent classification (`intelligent_intent_classification()`)
   - Ambiguous query handling (`handle_ambiguous_query()`)
   - Document reference check (`intelligent_document_reference_check()`)
   - Framework resolution (`intelligent_framework_resolution()`)
   - Guardrails (`check_compliance_guardrails()`)
   - Expert routing (`intelligent_expert_routing()`)
   - Conversation history (`IntelligentConversationHistory`)
   - Document compliance expert (`document_compliance_expert()`)
   - Scenario guidance expert (`scenario_guidance_expert()`)
   - Short QA answer (`short_qa_answer()`)

4. **`Complytics Backend/compliance_rag_intelligent.py`**
   - General compliance expert (`expert_general_compliance()`)
   - Query type detection (`detect_query_type()`)
   - Domain expert selection (`select_domain_expert()`)

5. **`Complytics Backend/db.py`**
   - Database connection
   - MongoDB operations

6. **`Complytics Backend/schemas/users.py`**
   - User schema definitions

### Frontend Files (React/JSX)

1. **`src/components/team/ComplianceChat.jsx`**
   - Main chat interface component
   - Message display
   - Input handling
   - File upload UI
   - Session management
   - History display

2. **`src/components/ui/ComplianceChatFormattedResponse.jsx`**
   - Response formatting component
   - Markdown rendering
   - HTML table rendering
   - Code highlighting
   - Expert tags display
   - Proper spacing handling

3. **`src/lib/api.js`**
   - API utility functions
   - API URL building

4. **`src/context/AuthContext.jsx`**
   - Authentication context
   - Token management

### Configuration Files

1. **`Complytics Backend/config.py`**
   - Application configuration
   - Environment variables (GOOGLE_API_KEY1-4)

2. **`Complytics Backend/requirements.txt`**
   - Python dependencies

### Data Files

1. **`Complytics Backend/compliance_frameworks/`**
   - PDF files of compliance frameworks
   - Source documents for RAG

2. **`Complytics Backend/embeddings/`**
   - `document_embeddings.npy` - Document embeddings
   - `document_map.json` - Document mapping
   - `uploaded_docs_embeddings.npy` - Uploaded documents embeddings
   - `uploaded_docs_segments.json` - Uploaded documents segments

3. **`Complytics Backend/faiss_indexes/`**
   - `compliance_index.faiss` - FAISS index file
   - `uploaded_docs.index` - Uploaded documents index

4. **`Complytics Backend/compliance_cache/`**
   - `query_cache.json` - Query cache

---

## Key Functions (Detailed)

### Main Functions in `compliance_rag.py`:
- `get_embedding_optimized()` - Query to embedding conversion
- `process_documents()` - Load documents, embeddings, FAISS index
- `search_documents()` - FAISS similarity search
- `expert_privacy_regulations()` - Privacy expert
- `expert_audit_compliance()` - Audit expert
- `expert_security_controls()` - Security expert
- `expert_financial_compliance()` - Financial expert
- `expert_healthcare_compliance()` - Healthcare expert
- `aggregate_expert_outputs()` - Aggregate multiple expert responses
- `save_query_cache()` - Save cache to disk
- `hash_text()` - MD5 hash generation

### Main Functions in `compliance_rag_refined.py`:
- `process_compliance_query_unified()` - Main unified processing function
- `intelligent_intent_classification()` - LLM-based intent classification
- `handle_ambiguous_query()` - Ambiguous query detection
- `intelligent_document_reference_check()` - Document reference detection
- `intelligent_framework_resolution()` - Framework resolution from context
- `check_compliance_guardrails()` - Non-compliance guardrails
- `intelligent_expert_routing()` - Intelligent expert selection
- `scenario_guidance_expert()` - Scenario guidance
- `document_compliance_expert()` - Document compliance
- `short_qa_answer()` - Short answers
- `IntelligentConversationHistory` - Context management class

### Main Functions in `compliance_rag_intelligent.py`:
- `expert_general_compliance()` - General compliance expert
- `detect_query_type()` - Query type detection (comparison, factual, explanation)
- `select_domain_expert()` - Domain expert selection

---

## Database Collections

1. **`compliance_chat_history`** - Chat history storage
2. **`documents`** - Uploaded documents storage

---

## API Endpoints

- `POST /api/compliance/chat` - Chat query endpoint
- `POST /api/compliance/upload` - Document upload endpoint
- `POST /api/compliance/reset` - Reset conversation endpoint

---

## Dependencies

- **FastAPI** - Web framework
- **Google Gemini AI** - LLM for response generation (4 API keys for failover)
- **SentenceTransformer** - Embedding model (`all-MiniLM-L6-v2`)
- **FAISS** - Vector similarity search
- **MongoDB** - Database
- **PyPDF2/pdfplumber** - PDF processing
- **python-docx** - DOCX processing
- **numpy** - Numerical operations
- **hashlib** - Hash generation

---

## Summary

Ye module ek intelligent compliance chatbot hai jo:

1. **Intelligent Query Understanding**: LLM-based intent classification, ambiguous query detection, guardrails
2. **Context Management**: User queries ko store karke context maintain karta hai (50 queries max)
3. **Intelligent Caching**: Proper compliance questions ko cache karta hai for fast responses
4. **RAG System**: Query ko embeddings mein convert karke FAISS se relevant documents retrieve karta hai
5. **Expert System**: Multiple specialized experts jo semantic understanding se select hote hain
6. **Evidence-Based Responses**: Documents se evidence cite karke comprehensive answers deta hai
7. **Knowledge Fallback**: Agar documents mein answer nahi hai, to expert knowledge use karta hai
8. **Proper Formatting**: Markdown formatting, green highlighting, structured responses

Sab kuch RAG technique, LLM-based intelligent routing, aur AI (Gemini) ke combination se kaam karta hai. Keyword-based matching NAHI hota - sab kuch semantic understanding aur LLM-based hai.
