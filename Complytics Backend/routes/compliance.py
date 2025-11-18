from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from typing import Optional, List
import os
from datetime import datetime, timedelta
import shutil
from pathlib import Path
import logging
from schemas.users import UserInDB  # Changed to UserInDB which is the correct model
from db import database
from compliance_rag import (
    process_documents,
    ConversationHistory,
    select_relevant_experts_optimized,
    is_compliance_related_optimized,
    generate_non_compliance_response,
    generate_simple_non_compliance_response,
    process_uploaded_document,
    analyze_privacy_policy,
    generate_privacy_policy,
    extract_text_from_pdf,
    extract_text_from_docx,
    rate_limited_generate_content_optimized,
    generate_terms_and_conditions,
    learn_from_user_interaction,
    analyze_document_intent,
    generate_comprehensive_document_analysis,
    generate_intelligent_compliant_document,
    create_docx_with_download_link,
    format_document_response_with_download,
    generate_document_improvement_suggestions,
    process_query_optimized,
    get_embedding_optimized,
    classify_document_type,
    detect_document_analysis_request,
    detect_document_reference,
    analyze_general_documentation_compliance,
    QUERY_CACHE,
    save_query_cache
)
from compliance_rag_refined import (
    analyze_refined_intent,
    privacy_policy_expert_extractive,
    terms_expert_extractive,
    scenario_guidance_expert,
    short_qa_answer,
    format_extractive_findings,
    document_compliance_expert,
    format_document_compliance_response
)
from routes.auth import get_current_user  # Add this import for authentication
from fastapi.responses import FileResponse
import hashlib
from fastapi import status
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["compliance"])

# Initialize conversation history
conversation_histories = {}

async def _get_or_extract_document_text(doc, db):
    try:
        # Prefer stored content if available
        text = (doc or {}).get("content")
        if isinstance(text, str) and text.strip():
            return text
        # Fallback to reading from disk
        path = (doc or {}).get("file_path") or ""
        if not path or not os.path.exists(path):
            return ""
        if path.endswith('.pdf'):
            text = extract_text_from_pdf(path)
        elif path.endswith('.docx'):
            text = extract_text_from_docx(path)
        else:
            return ""
        if isinstance(text, str) and text.strip():
            try:
                await db.documents.update_one({"_id": doc.get("_id")}, {"$set": {"content": text}})
            except Exception:
                pass
            return text
        return ""
    except Exception:
        return ""

@router.post("/chat")
async def compliance_chat(
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db)
):
    start_time = datetime.utcnow()
    try:
        logger.info(f"Received chat request from user: {current_user.id}")
        data = await request.json()
        query = data.get("query")
        session_id = data.get("session_id", str(current_user.id))
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        logger.info(f"Processing query: {query} for session: {session_id}")

        # Initialize or get conversation history
        if session_id not in conversation_histories:
            logger.info(f"Creating new conversation history for session: {session_id}")
            conversation_histories[session_id] = ConversationHistory()

        # Get conversation context before checking compliance
        conversation_context = conversation_histories[session_id].get_context()
        logger.info(f"Got conversation context: {conversation_context[:100]}...")

        # Check if user has uploaded documents scoped to this session only
        has_uploaded_doc = False
        latest_doc = await db.documents.find_one(
            {"session_id": session_id},
                sort=[("upload_date", -1)]
            )
        if latest_doc:
            has_uploaded_doc = True
            try:
                logger.info(f"Latest uploaded doc for session={session_id} user={current_user.id}: name={latest_doc.get('original_name')} path={latest_doc.get('file_path')} has_content={'content' in latest_doc}")
            except Exception:
                pass

        # Quick pattern-based non-compliance detection (safety net)
        query_lower = query.lower()
        personal_life_patterns = [
            r'\b(what|which).+(should i|do i|can i).+(eat|drink|play|watch|buy|wear)',
            r'\bi got (in )?an? accident\b',
            r'\bcar accident\b',
            r'\bvideo game\b',
            r'\bmovie (to watch|recommendation)\b',
            r'\brestaurant\b',
            r'\bfood (to eat|recommendation)\b',
            r'\bwhat (should|can) i (do|play|eat|watch) (today|tonight)',
        ]
        
        import re
        is_personal_query = any(re.search(pattern, query_lower) for pattern in personal_life_patterns)
        
        if is_personal_query:
            logger.info(f"Pattern-based detection: Personal/non-compliance query detected")
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            response = generate_simple_non_compliance_response(query)
            experts = []
            conversation_histories[session_id].add_exchange(query, response, is_compliance=False)
            await db.compliance_chat_history.update_one(
                {"user_id": current_user.id, "session_id": session_id},
                {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": False}},
                 "$set": {"last_updated": end_time}},
                upsert=True
            )
            logger.info("Blocked personal query with pattern detection")
            return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": False}
        
        # Early document analysis detection - check if user is asking about a document BEFORE intent analysis
        # This prevents queries like "analyze this document" from triggering experts when no doc is uploaded
        doc_analysis_detected = detect_document_analysis_request(query)
        doc_reference_detected = detect_document_reference(query, conversation_context)
        
        logger.info(f"Early document detection: analysis={doc_analysis_detected}, reference={doc_reference_detected}, has_doc={has_uploaded_doc}")
        
        # If user is clearly asking about a document but hasn't uploaded one, stop early
        if (doc_analysis_detected or doc_reference_detected) and not has_uploaded_doc:
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            response = "Please upload your document first. I don't see any file attached in this session."
            experts = []
            conversation_histories[session_id].add_exchange(query, response, is_compliance=True)
            await db.compliance_chat_history.update_one(
                {"user_id": current_user.id, "session_id": session_id},
                {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": True}},
                 "$set": {"last_updated": end_time}},
                upsert=True
            )
            logger.info(f"Blocked document query without upload (early): {query}")
            return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": True}
        
        # Refined intent analysis with sub-intents
        refined_intent = analyze_refined_intent(query, conversation_context, has_uploaded_doc)
        logger.info(f"Refined intent: {refined_intent}")
        
        # Fallback to old intent for compatibility
        intent_analysis = analyze_document_intent(query, conversation_context, has_uploaded_doc)
        logger.info(f"Legacy intent analysis: {intent_analysis}")

        # If user is referring to uploaded document and one exists, validate document type early
        if (doc_analysis_detected or doc_reference_detected) and has_uploaded_doc:
            document_text = (latest_doc or {}).get("content") or ""
            if not document_text:
                path = latest_doc.get("file_path") or ""
                if path and os.path.exists(path):
                    if path.endswith('.pdf'):
                        document_text = extract_text_from_pdf(path)
                    elif path.endswith('.docx'):
                        document_text = extract_text_from_docx(path)
            
            # Check if document has enough text (minimum 50 chars for classification)
            if not document_text or len(document_text.strip()) < 50:
                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds()
                response = "The uploaded document appears to be empty or too short to analyze. Please upload a document with substantial content (at least 50 characters)."
                experts = []
                conversation_histories[session_id].add_exchange(query, response, is_compliance=True)
                await db.compliance_chat_history.update_one(
                    {"user_id": current_user.id, "session_id": session_id},
                    {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": True}},
                     "$set": {"last_updated": end_time}},
                    upsert=True
                )
                logger.info(f"Rejected document - too short: {len(document_text.strip())} chars")
                return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": True}
            
            if document_text:
                # Check with allow_general_docs=True to detect system documentation
                doc_type = classify_document_type(document_text, allow_general_docs=True)
                logger.info(f"Early document type check: {doc_type}")
                
                # Reject documents that are not allowed types
                if doc_type not in ("privacy_policy", "terms_and_conditions", "general_documentation"):
                    response = (
                        "## ❌ Document Type Not Supported\n\n"
                        f"The uploaded document appears to be a **{doc_type.replace('_', ' ').title()}** document, "
                        "which I cannot analyze.\n\n"
                        "### 📋 Supported Document Types:\n\n"
                        "I can only analyze the following document types:\n\n"
                        "🔒 **Privacy Policies**\n"
                        "- GDPR, CCPA, PIPEDA, or other privacy policy documents\n"
                        "- Documents describing how you collect, use, and protect personal data\n\n"
                        "📜 **Terms and Conditions**\n"
                        "- Terms of Service, User Agreements, Acceptable Use Policies\n"
                        "- Documents defining the rules for using your service/platform\n\n"
                        "📋 **System/Software Documentation**\n"
                        "- Technical design documents, API specifications\n"
                        "- Architecture documents, deployment guides\n"
                        "- Software development and infrastructure documentation\n\n"
                        "### ⚠️ Not Supported:\n"
                        "- ISO compliance standards (ISO 27001, ISO 27002, etc.)\n"
                        "- Regulatory framework documents (NIST, SOC 2 controls, PCI DSS standards)\n"
                        "- Academic content (exams, assignments, research papers)\n"
                        "- Personal documents (CVs, resumes)\n\n"
                        "**Please upload one of the supported document types to continue with the analysis.**"
                    )
                    experts = []
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds()
                    conversation_histories[session_id].add_exchange(query, response, is_compliance=False)
                    await db.compliance_chat_history.update_one(
                        {"user_id": current_user.id, "session_id": session_id},
                        {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": False}},
                         "$set": {"last_updated": end_time}},
                        upsert=True
                    )
                    logger.info(f"Rejected document type: {doc_type}")
                    return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": False}
                
                # If it's a privacy policy or terms doc, smart-route before generic flows
                if doc_type in ("privacy_policy", "terms_and_conditions"):
                    ql = (query or "").lower()
                    # Summarization intents: avoid heavy expert flows
                    if any(p in ql for p in ["summarize", "summary", "tell me about", "what is this", "what's this", "overview"]):
                        end_time = datetime.utcnow()
                        response_time = (end_time - start_time).total_seconds()
                        prompt = (
                            "Summarize the following document in a concise, non-generic way.\n\n"
                            f"{document_text[:2500]}\n\n"
                            "Focus on real content from the document (not generic frameworks)."
                        )
                        response = rate_limited_generate_content_optimized(prompt)
                        experts = []
                        conversation_histories[session_id].add_exchange(query, response, is_compliance=True)
                        await db.compliance_chat_history.update_one(
                            {"user_id": current_user.id, "session_id": session_id},
                            {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": True}},
                             "$set": {"last_updated": end_time}},
                            upsert=True
                        )
                        logger.info("Completed concise document summary (no experts)")
                        return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": True}

                    # Analysis intents: require/ask framework; avoid generic expert boilerplate
                    analysis_verbs = ["analyze", "analyse", "review", "check", "assess", "evaluate", "compare", "improve"]
                    if any(v in ql for v in analysis_verbs):
                        # Detect frameworks from query
                        frameworks = []
                        if "gdpr" in ql:
                            frameworks.append("GDPR")
                        if "ccpa" in ql or "cpra" in ql:
                            frameworks.append("CCPA")
                        if "hipaa" in ql:
                            frameworks.append("HIPAA")
                        if "iso" in ql or "27001" in ql:
                            frameworks.append("ISO 27001")
                        if "soc" in ql or "soc2" in ql or "soc 2" in ql:
                            frameworks.append("SOC 2")

                        end_time = datetime.utcnow()
                        response_time = (end_time - start_time).total_seconds()

                        if not frameworks:
                            response = "Which framework should I use to analyze your document? For example: GDPR, CCPA."
                            experts = []
                            conversation_histories[session_id].add_exchange(query, response, is_compliance=True)
                            await db.compliance_chat_history.update_one(
                                {"user_id": current_user.id, "session_id": session_id},
                                {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": True}},
                                 "$set": {"last_updated": end_time}},
                                upsert=True
                            )
                            logger.info("Asked user to select framework for analysis (no experts)")
                            return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": True}

                        # Use the first specified framework for targeted analysis
                        framework_choice = frameworks[0]
                        # Use document_compliance_expert for all document analysis
                        result = document_compliance_expert(document_text, doc_type, framework_choice)
                        response = format_document_compliance_response(result)
                        experts = ['document_compliance']
                        conversation_histories[session_id].add_exchange(query, response, is_compliance=True)
                        await db.compliance_chat_history.update_one(
                            {"user_id": current_user.id, "session_id": session_id},
                            {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": True}},
                             "$set": {"last_updated": end_time}},
                            upsert=True
                        )
                        logger.info(f"Completed targeted {doc_type} analysis for framework {framework_choice}")
                        return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": True}

                # Handle general documentation (system docs, architecture, etc.)
                if doc_type == "general_documentation":
                    # Extract frameworks from query or use defaults
                    frameworks = []
                    query_lower = query.lower()
                    if "gdpr" in query_lower:
                        frameworks.append("GDPR")
                    if "iso" in query_lower or "27001" in query_lower:
                        frameworks.append("ISO 27001")
                    if "soc" in query_lower or "soc2" in query_lower or "soc 2" in query_lower:
                        frameworks.append("SOC 2")
                    if "hipaa" in query_lower:
                        frameworks.append("HIPAA")
                    if "pci" in query_lower or "dss" in query_lower:
                        frameworks.append("PCI DSS")
                    if "nist" in query_lower:
                        frameworks.append("NIST")
                    
                    # Default frameworks if none specified
                    if not frameworks:
                        frameworks = ["GDPR", "ISO 27001", "SOC 2"]
                    
                    logger.info(f"Analyzing general documentation for frameworks: {frameworks}")
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds()
                    
                    # Use document_compliance_expert for general documentation analysis
                    # Use the first framework or default to GDPR
                    framework_choice = frameworks[0] if frameworks else "GDPR"
                    result = document_compliance_expert(document_text, doc_type, framework_choice)
                    response = format_document_compliance_response(result)
                    experts = ['document_compliance']
                    
                    conversation_histories[session_id].add_exchange(query, response, is_compliance=True)
                    await db.compliance_chat_history.update_one(
                        {"user_id": current_user.id, "session_id": session_id},
                        {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": True}},
                         "$set": {"last_updated": end_time}},
                        upsert=True
                    )
                    logger.info(f"Completed general documentation analysis")
                    return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": True}
                
                # Reject if it's truly unrelated (CV, personal docs, academic content, etc.)
                elif doc_type == "other":
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds()
                    response = """I can only analyze the following types of documents:

✅ **Privacy Policies** - For GDPR, CCPA, HIPAA compliance analysis
✅ **Terms & Conditions** - For legal and compliance review
✅ **System Documentation** - Architecture docs, API specs, technical designs, deployment guides, security documentation

❌ I cannot analyze:
- Academic content (quizzes, exams, assignments, lecture notes)
- Personal documents (CVs, resumes)
- General text documents unrelated to compliance or system documentation

Please upload one of the supported document types."""
                    experts = []
                    conversation_histories[session_id].add_exchange(query, response, is_compliance=True)
                    await db.compliance_chat_history.update_one(
                        {"user_id": current_user.id, "session_id": session_id},
                        {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": True}},
                         "$set": {"last_updated": end_time}},
                        upsert=True
                    )
                    logger.info(f"Rejected non-compliance document: {doc_type}")
                    return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": True}

        # === REFINED INTENT ROUTING ===
        # Route based on refined intent for better responses
        intent = refined_intent.get("intent", "")
        framework = refined_intent.get("framework", "general")
        
        # 0. NON_COMPLIANCE - Not compliance-related
        if intent == "NON_COMPLIANCE":
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            response = generate_simple_non_compliance_response(query)
            experts = []
            conversation_histories[session_id].add_exchange(query, response, is_compliance=False)
            await db.compliance_chat_history.update_one(
                {"user_id": current_user.id, "session_id": session_id},
                {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": False}},
                 "$set": {"last_updated": end_time}},
                upsert=True
            )
            logger.info("Handled non-compliance query")
            return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": False}
        
        # 0.5. DOC_ANALYSIS_NO_UPLOAD - User asking about document without uploading
        if intent == "DOC_ANALYSIS_NO_UPLOAD":
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            response = "Please upload your document first. I don't see any file attached in this session."
            experts = []
            conversation_histories[session_id].add_exchange(query, response, is_compliance=True)
            await db.compliance_chat_history.update_one(
                {"user_id": current_user.id, "session_id": session_id},
                {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": True}},
                 "$set": {"last_updated": end_time}},
                upsert=True
            )
            logger.info("Handled doc analysis request without upload (via refined intent)")
            return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": True}
        
        # 1. GENERAL_QA_SHORT - Short factual answers
        if intent == "GENERAL_QA_SHORT":
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            response = short_qa_answer(query)
            experts = []
            conversation_histories[session_id].add_exchange(query, response, is_compliance=True)
            await db.compliance_chat_history.update_one(
                {"user_id": current_user.id, "session_id": session_id},
                {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": True}},
                 "$set": {"last_updated": end_time}},
                upsert=True
            )
            logger.info("Completed short QA response")
            return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": True}
        
        # 2. DOC_SUMMARY - Concise document summary
        elif intent == "DOC_SUMMARY" and has_uploaded_doc:
            document_text = await _get_or_extract_document_text(latest_doc, db)
            if document_text and len(document_text.strip()) >= 100:
                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds()
                prompt = f"Summarize this document concisely (3-5 sentences):\n\n{document_text[:2500]}"
                response = rate_limited_generate_content_optimized(prompt)
                experts = []
                conversation_histories[session_id].add_exchange(query, response, is_compliance=True)
                await db.compliance_chat_history.update_one(
                    {"user_id": current_user.id, "session_id": session_id},
                    {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": True}},
                     "$set": {"last_updated": end_time}},
                    upsert=True
                )
                logger.info("Completed document summary")
                return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": True}
        
        # 3. DOC_ANALYSIS_CLARIFY - Ask for framework
        elif intent == "DOC_ANALYSIS_CLARIFY" and has_uploaded_doc:
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            response = "Which compliance framework should I use to analyze your document?\n\nOptions:\n- GDPR (EU data protection)\n- CCPA/CPRA (California privacy)\n- HIPAA (US healthcare)\n- ISO 27001 (Information security)\n- SOC 2 (Service organization controls)"
            experts = []
            conversation_histories[session_id].add_exchange(query, response, is_compliance=True)
            await db.compliance_chat_history.update_one(
                {"user_id": current_user.id, "session_id": session_id},
                {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": True}},
                 "$set": {"last_updated": end_time}},
                upsert=True
            )
            logger.info("Asked user to clarify framework")
            return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": True}
        
        # 4. DOC_ANALYSIS_TARGETED - Run extractive expert
        elif intent == "DOC_ANALYSIS_TARGETED" and has_uploaded_doc:
            document_text = await _get_or_extract_document_text(latest_doc, db)
            if document_text and len(document_text.strip()) >= 200:
                doc_type = classify_document_type(document_text, allow_general_docs=True)
                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds()
                
                # Only allow privacy policy, terms & conditions, and system documentation
                if doc_type not in ("privacy_policy", "terms_and_conditions", "general_documentation"):
                    response = (
                        "## ❌ Cannot Analyze This Document Type\n\n"
                        f"The uploaded document is classified as: **{doc_type.replace('_', ' ').title()}**\n\n"
                        "### ✅ Documents I Can Analyze:\n\n"
                        "🔒 **Privacy Policies** - GDPR, CCPA, privacy notices\n\n"
                        "📜 **Terms and Conditions** - Terms of Service, User Agreements\n\n"
                        "📋 **System/Software Documentation** - Technical and architecture docs\n\n"
                        "### ❌ Documents I Cannot Analyze:\n\n"
                        "- ISO/Compliance Standards (ISO 27001, SOC 2, NIST frameworks)\n"
                        "- Regulatory Documents (PCI DSS, HIPAA regulations)\n"
                        "- Academic Content (exams, assignments)\n"
                        "- Personal Documents (CVs, resumes)\n\n"
                        "💡 **Tip:** Please upload a Privacy Policy, Terms and Conditions, or System Documentation document for analysis."
                    )
                    experts = []
                else:
                    # Use the specialized document compliance expert for all document types
                    result = document_compliance_expert(document_text, doc_type, framework)
                    response = format_document_compliance_response(result)
                    experts = ['document_compliance']
                
                conversation_histories[session_id].add_exchange(query, response, is_compliance=True)
                await db.compliance_chat_history.update_one(
                    {"user_id": current_user.id, "session_id": session_id},
                    {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": True}},
                     "$set": {"last_updated": end_time}},
                    upsert=True
                )
                logger.info(f"Completed extractive {doc_type} analysis for {framework}")
                return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": True}
        
        # 5. DOC_GENERATION - Generate or improve a compliant document
        elif intent == "DOC_GENERATION":
            logger.info(f"Document generation requested: {refined_intent}")
            
            # Determine if we're generating from scratch or improving an existing document
            if has_uploaded_doc:
                # User uploaded a document and wants it improved/made compliant
                document_text = await _get_or_extract_document_text(latest_doc, db)
                if document_text and len(document_text.strip()) >= 200:
                    doc_type = classify_document_type(document_text, allow_general_docs=True)
                    
                    # Only process allowed document types
                    if doc_type in ("privacy_policy", "terms_and_conditions", "general_documentation"):
                        end_time = datetime.utcnow()
                        response_time = (end_time - start_time).total_seconds()
                        
                        # Use the document compliance expert for comprehensive analysis and correction
                        result = document_compliance_expert(document_text, doc_type, framework)
                        corrected_doc = result.get("corrected_document", "")
                        
                        # Create DOCX file from corrected document
                        file_path, download_url = create_docx_with_download_link(
                            corrected_doc, f"improved_{doc_type}", framework, str(current_user.id)
                        )
                        
                        # Format the response with analysis and download link
                        response = format_document_compliance_response(result)
                        
                        if download_url:
                            response += f"\n\n### 📥 Download Your Corrected Document\n\n"
                            response += f"[Click here to download your compliant {doc_type.replace('_', ' ')}]({download_url})\n"
                            
                            # Store generation record
                            await db.document_generations.insert_one({
                                "user_id": current_user.id,
                                "session_id": session_id,
                                "document_type": doc_type,
                                "framework": framework,
                                "file_path": file_path,
                                "download_url": download_url,
                                "timestamp": datetime.utcnow(),
                                "improvement": True
                            })
                        
                        experts = ['document_compliance']
                        conversation_histories[session_id].add_exchange(query, response, is_compliance=True)
                        await db.compliance_chat_history.update_one(
                            {"user_id": current_user.id, "session_id": session_id},
                            {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": True}},
                             "$set": {"last_updated": end_time}},
                            upsert=True
                        )
                        logger.info("Completed document improvement generation with document_compliance_expert")
                        return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": True}
            else:
                # Generate from scratch (no uploaded document)
                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds()
                
                document_type = refined_intent.get("document_type", "privacy_policy")
                organization_context = f"User session context: {conversation_context[:500]}"
                
                # Generate the document content
                document_content = generate_intelligent_compliant_document(
                    document_type, framework, organization_context
                )
                
                # Create DOCX file with download link
                file_path, download_url = create_docx_with_download_link(
                    document_content, document_type, framework, str(current_user.id)
                )
                
                if download_url:
                    response = format_document_response_with_download(
                        document_content, download_url, document_type, framework
                    )
                    
                    # Store generation record in database
                    await db.document_generations.insert_one({
                        "user_id": current_user.id,
                        "session_id": session_id,
                        "document_type": document_type,
                        "framework": framework,
                        "file_path": file_path,
                        "download_url": download_url,
                        "timestamp": datetime.utcnow()
                    })
                else:
                    response = f"I've generated a {framework}-compliant {document_type.replace('_', ' ')} document for you:\n\n{document_content}\n\nNote: There was an issue creating the download file, but you can copy the content above."
                
                experts = ['privacy', 'audit']
                conversation_histories[session_id].add_exchange(query, response, is_compliance=True)
                await db.compliance_chat_history.update_one(
                    {"user_id": current_user.id, "session_id": session_id},
                    {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": True}},
                     "$set": {"last_updated": end_time}},
                    upsert=True
                )
                logger.info("Completed document generation from scratch")
                return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": True}
        
        # 6. USE_MAIN_EXPERTS - Route to main expert system (Audit, Security, Privacy, Financial)
        elif intent == "USE_MAIN_EXPERTS":
            logger.info(f"Routing to main expert system for query: {query[:100]}")
            # Continue to main expert processing below (don't return early)
            pass  # Fall through to main expert system
        
        # 7. SCENARIO_GUIDANCE - Compliance guidance (only for step-by-step implementation guides)
        elif intent == "SCENARIO_GUIDANCE":
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            response = scenario_guidance_expert(query, framework)
            experts = ['guidance']
            conversation_histories[session_id].add_exchange(query, response, is_compliance=True)
            await db.compliance_chat_history.update_one(
                {"user_id": current_user.id, "session_id": session_id},
                {"$push": {"messages": {"query": query, "response": response, "experts_consulted": experts, "response_time": response_time, "timestamp": end_time, "is_compliance": True}},
                 "$set": {"last_updated": end_time}},
                upsert=True
            )
            logger.info(f"Completed scenario guidance for {framework}")
            return {"response": response, "session_id": session_id, "experts_consulted": experts, "response_time": response_time, "is_compliance": True}
        
        # === FALLBACK TO LEGACY ROUTING ===
        # Removed keyword-based document analysis shortcut; rely on explicit ANALYZE_UPLOADED intent with session-scoped docs

        # Handle different document intents
        if intent_analysis["intent"] == "ANALYZE_UPLOADED":
            if not has_uploaded_doc:
                response = "I'd be happy to analyze your document for compliance! However, I don't see any uploaded documents in our current session. Please upload your privacy policy or terms & conditions document first, and then I can provide a comprehensive compliance analysis."
                experts = []
            else:
                # Extract text from the latest document
                # Validate file exists
                # Prefer stored content; if not present, validate path and extract
                document_text = (latest_doc or {}).get("content") or ""
                if not document_text and not os.path.exists(latest_doc["file_path"]):
                    response = "Uploaded file is no longer available on the server and no stored content was found. Please re-upload your document."
                    experts = []
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds()
                    return {
                        "response": response,
                        "session_id": session_id,
                        "experts_consulted": experts,
                        "response_time": response_time,
                        "is_compliance": True
                    }
                if not document_text:
                    if latest_doc["file_path"].endswith('.pdf'):
                        document_text = extract_text_from_pdf(latest_doc["file_path"])
                    elif latest_doc["file_path"].endswith('.docx'):
                        document_text = extract_text_from_docx(latest_doc["file_path"])
                    else:
                        document_text = "Unsupported file format"
                    if isinstance(document_text, str) and document_text.strip():
                        try:
                            await db.documents.update_one({"_id": latest_doc.get("_id")}, {"$set": {"content": document_text}})
                        except Exception:
                            pass
                # If extraction failed or text too short, stop
                if not document_text or len(document_text.strip()) < 200:
                    response = "I couldn't read enough text from the uploaded document to analyze it. Please ensure the file isn't scanned-only, or upload a text-based PDF/DOCX."
                    experts = []
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds()
                    return {
                        "response": response,
                        "session_id": session_id,
                        "experts_consulted": experts,
                        "response_time": response_time,
                        "is_compliance": True
                    }
                # Gate by document type: only privacy policy, terms & conditions, or system documentation allowed
                doc_type = classify_document_type(document_text, allow_general_docs=True)
                if doc_type not in ("privacy_policy", "terms_and_conditions", "general_documentation"):
                    response = (
                        "## 🚫 Unsupported Document Type\n\n"
                        f"**Detected:** {doc_type.replace('_', ' ').title()}\n\n"
                        "I specialize in analyzing user-facing policies and technical documentation.\n\n"
                        "### ✅ What I Can Analyze:\n\n"
                        "🔒 **Privacy Policies** - Data protection and privacy notices\n\n"
                        "📜 **Terms and Conditions** - Service terms and user agreements\n\n"
                        "📋 **Technical Documentation** - System and software docs\n\n"
                        "Please upload one of these document types for compliance analysis."
                    )
                    experts = []
                    # Short-circuit this intent branch
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds()
                    return {
                        "response": response,
                        "session_id": session_id,
                        "experts_consulted": experts,
                        "response_time": response_time,
                        "is_compliance": True
                    }
                
                # Generate comprehensive analysis using document_compliance_expert
                framework = intent_analysis.get("framework", "GDPR")
                document_type = intent_analysis.get("document_type", "document")
                
                result = document_compliance_expert(document_text, document_type, framework)
                response = format_document_compliance_response(result)
                experts = ['document_compliance']

        elif intent_analysis["intent"] == "GENERATE_NEW":
            # Generate a new compliant document
            framework = intent_analysis.get("framework", "GDPR")
            document_type = intent_analysis.get("document_type", "privacy_policy")
            
            # Get organization context from conversation if available
            organization_context = f"User session context: {conversation_context[:500]}"
            
            # Generate the document content
            document_content = generate_intelligent_compliant_document(
                document_type, framework, organization_context
            )
            
            # Create DOCX file with download link
            file_path, download_url = create_docx_with_download_link(
                document_content, document_type, framework, str(current_user.id)
            )
            
            if download_url:
                # Format response with download link
                response = format_document_response_with_download(
                    document_content, download_url, document_type, framework
                )
                
                # Store generation record in database
                await db.document_generations.insert_one({
                    "user_id": current_user.id,
                    "session_id": session_id,
                    "document_type": document_type,
                    "framework": framework,
                    "file_path": file_path,
                    "download_url": download_url,
                    "timestamp": datetime.utcnow()
                })
            else:
                response = f"I've generated a {framework}-compliant {document_type.replace('_', ' ')} document for you:\n\n{document_content}\n\nNote: There was an issue creating the download file, but you can copy the content above."
            
            experts = ['privacy', 'audit']

        elif intent_analysis["intent"] == "COMPARE_COMPLIANCE":
            if not has_uploaded_doc:
                response = "To compare your document against compliance standards, please first upload your privacy policy or terms & conditions document. Once uploaded, I can provide a detailed comparison against any compliance framework you specify."
                experts = []
            else:
                # Extract and analyze document
                document_text = (latest_doc or {}).get("content") or ""
                if not document_text and not os.path.exists(latest_doc["file_path"]):
                    response = "Uploaded file is no longer available on the server and no stored content was found. Please re-upload your document."
                    experts = []
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds()
                    return {
                        "response": response,
                        "session_id": session_id,
                        "experts_consulted": experts,
                        "response_time": response_time,
                        "is_compliance": True
                    }
                if not document_text:
                    if latest_doc["file_path"].endswith('.pdf'):
                        document_text = extract_text_from_pdf(latest_doc["file_path"])
                    elif latest_doc["file_path"].endswith('.docx'):
                        document_text = extract_text_from_docx(latest_doc["file_path"])
                    else:
                        document_text = "Unsupported file format"
                    if isinstance(document_text, str) and document_text.strip():
                        try:
                            await db.documents.update_one({"_id": latest_doc.get("_id")}, {"$set": {"content": document_text}})
                        except Exception:
                            pass
                if not document_text or len(document_text.strip()) < 200:
                    response = "I couldn't read enough text from the uploaded document to compare it. Please upload a text-based PDF/DOCX."
                    experts = []
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds()
                    return {
                        "response": response,
                        "session_id": session_id,
                        "experts_consulted": experts,
                        "response_time": response_time,
                        "is_compliance": True
                    }
                # Gate by document type
                doc_type = classify_document_type(document_text, allow_general_docs=True)
                if doc_type not in ("privacy_policy", "terms_and_conditions", "general_documentation"):
                    response = (
                        "❌ **Document Type Not Supported**\n\n"
                        "I can only analyze:\n"
                        "✅ Privacy Policies\n"
                        "✅ Terms and Conditions\n"
                        "✅ System/Software Documentation\n"
                    )
                    experts = []
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds()
                    return {
                        "response": response,
                        "session_id": session_id,
                        "experts_consulted": experts,
                        "response_time": response_time,
                        "is_compliance": True
                    }
                
                framework = intent_analysis.get("framework", "GDPR")
                document_type = intent_analysis.get("document_type", "document")
                
                # Use document_compliance_expert for all document analysis
                result = document_compliance_expert(document_text, document_type, framework)
                response = format_document_compliance_response(result)
                experts = ['document_compliance']

        elif intent_analysis["intent"] == "GET_IMPROVEMENT_SUGGESTIONS":
            if not has_uploaded_doc:
                response = "I'd be happy to provide improvement suggestions for your document! Please upload your current privacy policy or terms & conditions document first, and I'll analyze it and give you specific recommendations on how to make it better."
                experts = []
            else:
                # Extract text from uploaded document
                document_text = (latest_doc or {}).get("content") or ""
                if not document_text and not os.path.exists(latest_doc["file_path"]):
                    response = "Uploaded file is no longer available on the server and no stored content was found. Please re-upload your document."
                    experts = []
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds()
                    return {
                        "response": response,
                        "session_id": session_id,
                        "experts_consulted": experts,
                        "response_time": response_time,
                        "is_compliance": True
                    }
                if not document_text:
                    if latest_doc["file_path"].endswith('.pdf'):
                        document_text = extract_text_from_pdf(latest_doc["file_path"])
                    elif latest_doc["file_path"].endswith('.docx'):
                        document_text = extract_text_from_docx(latest_doc["file_path"])
                    else:
                        document_text = "Unsupported file format"
                    if isinstance(document_text, str) and document_text.strip():
                        try:
                            await db.documents.update_one({"_id": latest_doc.get("_id")}, {"$set": {"content": document_text}})
                        except Exception:
                            pass
                if not document_text or len(document_text.strip()) < 200:
                    response = "I couldn't read enough text from the uploaded document to provide suggestions. Please upload a text-based PDF/DOCX."
                    experts = []
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds()
                    return {
                        "response": response,
                        "session_id": session_id,
                        "experts_consulted": experts,
                        "response_time": response_time,
                        "is_compliance": True
                    }
                # Gate by document type
                doc_type = classify_document_type(document_text, allow_general_docs=True)
                if doc_type not in ("privacy_policy", "terms_and_conditions", "general_documentation"):
                    response = (
                        "❌ **Document Type Not Supported**\n\n"
                        "I can only analyze:\n"
                        "✅ Privacy Policies\n"
                        "✅ Terms and Conditions\n"
                        "✅ System/Software Documentation\n"
                    )
                    experts = []
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds()
                    return {
                        "response": response,
                        "session_id": session_id,
                        "experts_consulted": experts,
                        "response_time": response_time,
                        "is_compliance": True
                    }
                
                framework = intent_analysis.get("framework", "GDPR")
                document_type = intent_analysis.get("document_type", "privacy_policy")
                
                # Generate improvement suggestions WITHOUT creating a new document
                response = generate_document_improvement_suggestions(
                    document_text, framework, document_type
                )
                experts = ['privacy', 'audit']

        elif intent_analysis["intent"] == "IMPROVE_DOCUMENT":
            if not has_uploaded_doc:
                response = "I'd be happy to help improve your document! Please upload your current privacy policy or terms & conditions document, and I can analyze it and generate an improved, compliant version for you."
                experts = []
            else:
                # Extract text from uploaded document
                document_text = (latest_doc or {}).get("content") or ""
                if not document_text and not os.path.exists(latest_doc["file_path"]):
                    response = "Uploaded file is no longer available on the server and no stored content was found. Please re-upload your document."
                    experts = []
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds()
                    return {
                        "response": response,
                        "session_id": session_id,
                        "experts_consulted": experts,
                        "response_time": response_time,
                        "is_compliance": True
                    }
                if not document_text:
                    if latest_doc["file_path"].endswith('.pdf'):
                        document_text = extract_text_from_pdf(latest_doc["file_path"])
                    elif latest_doc["file_path"].endswith('.docx'):
                        document_text = extract_text_from_docx(latest_doc["file_path"])
                    else:
                        document_text = "Unsupported file format"
                    if isinstance(document_text, str) and document_text.strip():
                        try:
                            await db.documents.update_one({"_id": latest_doc.get("_id")}, {"$set": {"content": document_text}})
                        except Exception:
                            pass
                if not document_text or len(document_text.strip()) < 200:
                    response = "I couldn't read enough text from the uploaded document to improve it. Please upload a text-based PDF/DOCX."
                    experts = []
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds()
                    return {
                        "response": response,
                        "session_id": session_id,
                        "experts_consulted": experts,
                        "response_time": response_time,
                        "is_compliance": True
                    }
                # Gate by document type
                doc_type = classify_document_type(document_text, allow_general_docs=True)
                if doc_type not in ("privacy_policy", "terms_and_conditions", "general_documentation"):
                    response = (
                        "❌ **Document Type Not Supported**\n\n"
                        "I can only analyze:\n"
                        "✅ Privacy Policies\n"
                        "✅ Terms and Conditions\n"
                        "✅ System/Software Documentation\n"
                    )
                    experts = []
                    end_time = datetime.utcnow()
                    response_time = (end_time - start_time).total_seconds()
                    return {
                        "response": response,
                        "session_id": session_id,
                        "experts_consulted": experts,
                        "response_time": response_time,
                        "is_compliance": True
                    }
                
                framework = intent_analysis.get("framework", "GDPR")
                document_type = intent_analysis.get("document_type", "privacy_policy")
                
                # First analyze the current document using document_compliance_expert
                result = document_compliance_expert(document_text, document_type, framework)
                analysis = format_document_compliance_response(result)
                
                # Then generate an improved version
                improved_content = generate_intelligent_compliant_document(
                    document_type, framework, f"Improving existing document. Original content summary: {document_text[:1000]}"
                )
                
                # Create DOCX file
                file_path, download_url = create_docx_with_download_link(
                    improved_content, f"improved_{document_type}", framework, str(current_user.id)
                )
                
                if download_url:
                    response = f"""## 📊 Document Analysis & Improvement

{analysis}

---

## ✅ Improved Document Generated

I've created an improved, fully compliant version of your {document_type.replace('_', ' ')} document.

### 📥 Download Your Improved Document
**[Click here to download your improved {document_type.replace('_', ' ')} document]({download_url})**

The improved document addresses all the compliance gaps identified in the analysis above."""
                else:
                    response = f"{analysis}\n\n---\n\nImproved Document:\n\n{improved_content}"
                
                experts = ['privacy', 'audit']

        # Check if this is a document-related query (asking about uploaded content specifically)
        elif any(phrase in query.lower() for phrase in [
            "what is in this document", "what's in this document", "what is in the document", 
            "what's in the document", "show me the document", "document content",
            "document says", "in the uploaded document", "from the document",
            "analyze the uploaded document", "analyse the uploaded document", "review the uploaded document"
        ]):
            if has_uploaded_doc:
                # Extract text from the document
                if latest_doc["file_path"].endswith('.pdf'):
                    text = extract_text_from_pdf(latest_doc["file_path"])
                elif latest_doc["file_path"].endswith('.docx'):
                    text = extract_text_from_docx(latest_doc["file_path"])
                else:
                    text = "Unsupported file format"
                
                # Generate a summary of the document
                prompt = (
                    "Summarize the following document content in a clear and concise way:\n\n"
                    f"{text[:2000]}...\n\n"  # Limit text length for the prompt
                    "Focus on key compliance-related points and requirements."
                )
                
                response = rate_limited_generate_content_optimized(prompt)
                experts = ['privacy', 'audit']
            else:
                response = "No document has been uploaded for analysis. Please upload a document first."
                experts = []
        
        else:
            # Handle general compliance queries or non-document intents
            if intent_analysis["intent"] == "NON_DOCUMENT":
                # For non-compliance queries, return a simple, direct response
                response = generate_non_compliance_response(query, str(current_user.id))
                experts = []
            else:
                # This is a general compliance query
                is_compliance, reason = is_compliance_related_optimized(query, conversation_context)
                logger.info(f"Query compliance status: {is_compliance}, reason: {reason}")

                if not is_compliance:
                    # For non-compliance queries, return a simple, direct response
                    response = generate_non_compliance_response(query, str(current_user.id))
                    experts = []
                else:
                    # Process documents if not already done
                    logger.info("Processing compliance documents...")
                    segments, embeddings, index = process_documents()
                    
                    # Check if any of the required components are None or empty
                    if segments is None or len(segments) == 0:
                        logger.error("No segments found in documents")
                        raise HTTPException(status_code=500, detail="No segments found in documents")
                        
                    if embeddings is None or len(embeddings) == 0:
                        logger.error("No embeddings generated")
                        raise HTTPException(status_code=500, detail="No embeddings generated")
                        
                    if index is None:
                        logger.error("FAISS index not created")
                        raise HTTPException(status_code=500, detail="FAISS index not created")

                    # Get query embedding and relevant context
                    query_embedding = get_embedding_optimized(query)
                    if query_embedding is not None:
                        query_embedding = np.expand_dims(query_embedding, axis=0)
                        
                        # Debug: Log before FAISS search
                        logger.info(f"🔍 FAISS Search Debug:")
                        logger.info(f"  - Total segments available: {len(segments)}")
                        logger.info(f"  - FAISS index total vectors: {index.ntotal}")
                        logger.info(f"  - Query embedding shape: {query_embedding.shape}")
                        
                        distances, idxs = index.search(query_embedding, 3)
                        
                        # Debug: Log FAISS results
                        logger.info(f"  - FAISS returned indices: {idxs[0]}")
                        logger.info(f"  - FAISS returned distances: {distances[0]}")
                        
                        # Retrieve segments with detailed debugging
                        retrieved_segments = []
                        for i, idx in enumerate(idxs[0]):
                            logger.info(f"  - Processing index {i}: idx={idx}, len(segments)={len(segments)}, valid={idx >= 0 and idx < len(segments)}")
                            if idx >= 0 and idx < len(segments):
                                retrieved_segments.append(segments[idx])
                            else:
                                logger.warning(f"  ⚠️ Invalid index {idx} (must be 0-{len(segments)-1})")
                        
                        retrieved_context = " ".join(retrieved_segments)
                        
                        # Log retrieved context for verification
                        logger.info("="*80)
                        logger.info("📚 RETRIEVED CONTEXT FROM FRAMEWORK EMBEDDINGS")
                        logger.info("="*80)
                        logger.info(f"Query: {query}")
                        logger.info(f"Number of segments retrieved: {len(retrieved_segments)}")
                        logger.info(f"Total context length: {len(retrieved_context)} characters")
                        logger.info("-"*80)
                        if len(retrieved_segments) > 0:
                            for i, segment in enumerate(retrieved_segments, 1):
                                logger.info(f"\n📄 Segment {i} (Distance: {distances[0][i-1]:.4f}):")
                                logger.info(f"Preview: {segment[:500]}...")
                        else:
                            logger.error("❌ NO SEGMENTS RETRIEVED! Evidence-based approach will NOT work!")
                            logger.error("   This means experts will use general knowledge instead of framework citations.")
                        logger.info("="*80)
                    else:
                        retrieved_context = ""
                        logger.error("❌ Query embedding is None! Cannot search FAISS index.")

                    # Use optimized query processing
                    logger.info("Using optimized query processing...")
                    conversation_obj = conversation_histories.get(session_id)
                    response, processing_time = process_query_optimized(
                        query, retrieved_context, conversation_context, conversation_obj
                    )
                    
                    # Get experts from optimized selection
                    experts = select_relevant_experts_optimized(query)

        # Update conversation history
        conversation_histories[session_id].add_exchange(query, response, is_compliance=True)

        # Calculate response time
        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds()

        # Store in database
        await db.compliance_chat_history.update_one(
            {
                "user_id": current_user.id,
                "session_id": session_id
            },
            {
                "$push": {
                    "messages": {
                        "query": query,
                        "response": response,
                        "experts_consulted": experts,
                        "response_time": response_time,
                        "timestamp": end_time,
                        "is_compliance": True
                    }
                },
                "$set": {
                    "last_updated": end_time
                }
            },
            upsert=True
        )

        logger.info("Successfully processed chat request")
        return {
            "response": response,
            "session_id": session_id,
            "experts_consulted": experts,
            "response_time": response_time,
            "is_compliance": True
        }

    except Exception as e:
        logger.error(f"Error in compliance_chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
async def reset_compliance_chat(
    request: Request,
    current_user: UserInDB = Depends(get_current_user)  # Changed to UserInDB
):
    try:
        data = await request.json()
        session_id = data.get("session_id")
        if not session_id:
            raise HTTPException(status_code=422, detail="session_id is required")
            
        if session_id in conversation_histories:
            conversation_histories[session_id].reset()
        return {"message": "Chat history reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear-cache")
async def clear_query_cache(
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Clear all cached responses to force fresh answers from experts.
    This clears the query cache without affecting the caching system logic.
    """
    try:
        cache_entries_before = len(QUERY_CACHE)
        
        # Clear the in-memory cache
        QUERY_CACHE.clear()
        
        # Save the empty cache to disk
        save_query_cache()
        
        logger.info(f"Cache cleared by user {current_user.id}: {cache_entries_before} entries removed")
        
        return {
            "message": "Query cache cleared successfully",
            "cache_entries_cleared": cache_entries_before,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")

@router.get("/history")
async def get_compliance_chat_history(
    current_user: UserInDB = Depends(get_current_user),
    session_id: str = None,
    db = Depends(lambda: database.db)
):
    try:
        # Get specific session or latest messages
        query = {"user_id": current_user.id}
        if session_id:
            query["session_id"] = session_id
            
        session = await db.compliance_chat_history.find_one(
            query,
            sort=[("last_updated", -1)]
        )
        
        if not session:
            return {"history": []}
            
        return {
            "history": session["messages"]
        }
    except Exception as e:
        logger.error(f"Error fetching chat history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics")
async def get_chatbot_analytics(
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db)
):
    try:
        # For management_team, get combined analytics from compliance_team and it_team members
        # For other roles, get only their own analytics
        if current_user.role == 'management_team':
            # Get all users with compliance_team or it_team role in the same organization
            target_users = await db.users.find({
                "role": {"$in": ["compliance_team", "it_team"]},
                "organization_id": current_user.organization_id,
                "is_active": True
            }).to_list(length=None)
            
            if not target_users:
                # No compliance or IT team members found, return empty stats
                return {
                    "totalQueries": 0,
                    "averageResponseTime": 0,
                    "successRate": 0,
                    "mostCommonTopics": []
                }
            
            # Get user IDs (convert ObjectId to string to match format in compliance_chat_history)
            user_ids = [str(user["_id"]) for user in target_users]
            
            # Get all chat sessions from compliance and IT team members
            sessions = await db.compliance_chat_history.find(
                {"user_id": {"$in": user_ids}}
            ).to_list(length=None)
        else:
            # Get all chat sessions for the current user only
            sessions = await db.compliance_chat_history.find(
                {"user_id": current_user.id}
            ).to_list(length=None)
        
        # Calculate total queries from all messages in all sessions
        total_queries = sum(len(session.get('messages', [])) for session in sessions)
        
        # Calculate average response time
        response_times = []
        for session in sessions:
            for message in session.get('messages', []):
                if 'response_time' in message:
                    response_times.append(message['response_time'])
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Calculate success rate:
        # Treat any stored answer as a success, only deduct when the chatbot failed to produce a response.
        successful_responses = 0
        failed_responses = 0
        for session in sessions:
            for message in session.get('messages', []):
                response_text = (message.get('response') or "").strip()
                has_error_flag = bool(message.get('error')) or bool(message.get('error_message'))
                if response_text and not has_error_flag:
                    successful_responses += 1
                else:
                    failed_responses += 1

        total_attempts = successful_responses + failed_responses
        success_rate = (successful_responses / total_attempts * 100) if total_attempts > 0 else 0
        
        # Get most common topics (based on query content)
        from collections import Counter
        topics = []
        for session in sessions:
            for message in session.get('messages', []):
                query = message.get('query', '').lower()
                if 'compliance' in query:
                    topics.append('Compliance')
                elif 'security' in query:
                    topics.append('Security')
                elif 'privacy' in query:
                    topics.append('Privacy')
                elif 'regulatory' in query:
                    topics.append('Regulatory')
                else:
                    topics.append('General')
        
        most_common_topics = [topic for topic, _ in Counter(topics).most_common(3)]
        
        return {
            "totalQueries": total_queries,
            "averageResponseTime": round(avg_response_time, 2),
            "successRate": round(success_rate, 1),
            "mostCommonTopics": most_common_topics
        }
    except Exception as e:
        logger.error(f"Error fetching chatbot analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all-history")
async def get_all_compliance_chat_history(
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db)
):
    try:
        # Get all chat sessions for the user
        sessions = await db.compliance_chat_history.find(
            {"user_id": current_user.id}
        ).sort("last_updated", -1).to_list(length=None)
        
        return {
            "history": [
                {
                    "session_id": session["session_id"],
                    "messages": session["messages"],
                    "timestamp": session["last_updated"]
                }
                for session in sessions
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching all chat history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    query: Optional[str] = Form(None),
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db)
):
    try:
        logger.info(f"Received document upload request from user: {current_user.id}")
        logger.info(f"File details - Name: {file.filename}, Content-Type: {file.content_type}")

        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.docx')):
            logger.error(f"Invalid file type: {file.content_type}")
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed")

        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        logger.info(f"Upload directory: {upload_dir.absolute()}")

        # Create a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = upload_dir / filename
        logger.info(f"Target file path: {file_path}")

        # Save the file
        try:
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            logger.info("File saved successfully")
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

        # Process the document using compliance_rag
        try:
            logger.info("Processing document...")
            document_text = process_uploaded_document(str(file_path))
            if not document_text:
                raise ValueError("No text content could be extracted from the document")
            logger.info("Document processed successfully")
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            # Clean up the file if processing fails
            try:
                file_path.unlink()
            except:
                pass
            raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

        # Classify document type using hybrid LLM-based classifier
        try:
            doc_type = classify_document_type(document_text, allow_general_docs=True)
            logger.info(f"Upload-time document type: {doc_type}")
        except Exception:
            doc_type = "other"
        
        # Reject non-allowed document types immediately
        if doc_type not in ("privacy_policy", "terms_and_conditions", "general_documentation"):
            # Delete the uploaded file since it's not allowed
            try:
                os.remove(file_path)
                logger.info(f"Deleted rejected document: {filename}")
            except Exception as e:
                logger.error(f"Error deleting rejected file: {e}")
            
            # User-friendly error response for frontend dialog/popup
            error_detail = {
                "type": "INVALID_DOCUMENT_TYPE",
                "title": "Document Type Not Supported",
                "detected_type": doc_type.replace('_', ' ').title(),
                "message": (
                    f"The uploaded document appears to be a **{doc_type.replace('_', ' ').title()}** document, "
                    "which cannot be analyzed by this system.\n\n"
                    "**I can only analyze these document types:**\n\n"
                    "✅ **Privacy Policies** - GDPR, CCPA, or other privacy policy documents\n\n"
                    "✅ **Terms and Conditions** - Terms of Service, User Agreements\n\n"
                    "✅ **System/Software Documentation** - Technical design docs, API specifications, architecture documents\n\n"
                    "**Please upload one of the supported document types to continue.**"
                ),
                "allowed_types": [
                    {
                        "name": "Privacy Policy",
                        "description": "GDPR, CCPA, or other privacy policy documents",
                        "icon": "🔒"
                    },
                    {
                        "name": "Terms and Conditions",
                        "description": "Terms of Service, User Agreements",
                        "icon": "📜"
                    },
                    {
                        "name": "System/Software Documentation",
                        "description": "Technical design docs, API specs, architecture docs",
                        "icon": "📋"
                    }
                ],
                "rejected_reason": (
                    "ISO compliance standards, regulatory framework documents, academic content, "
                    "and personal documents (CVs, resumes) are not supported for analysis."
                )
            }
            
            raise HTTPException(
                status_code=400,
                detail=error_detail
            )

        # Store document info in database
        try:
            document = {
                "filename": filename,
                "original_name": file.filename,
                "session_id": session_id,
                "user_id": current_user.id,
                "upload_date": datetime.utcnow(),
                "file_path": str(file_path),
                "file_type": file.content_type,
                "status": "processed",
                "content": document_text,
                "doc_type": doc_type
            }
            
            result = await db.documents.insert_one(document)
            logger.info(f"Document info stored in database with ID: {result.inserted_id}")
        except Exception as e:
            logger.error(f"Error storing document info: {str(e)}")
            # Clean up the file if database operation fails
            try:
                file_path.unlink()
            except:
                pass
            raise HTTPException(status_code=500, detail=f"Error storing document info: {str(e)}")

        # Return only attachment metadata to avoid injecting chat text in UI
        return {
            "attachment": {
                "document_id": str(document["_id"]),
            "filename": file.filename,
                "doc_type": doc_type,
                "session_id": session_id
            },
            "echoed_query": query
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload_document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    finally:
        try:
            file.file.close()
        except:
            pass

@router.post("/analyze-privacy-policy")
async def analyze_policy(
    file: UploadFile = File(...),
    framework: str = Form(...),
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db)
):
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.docx')):
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed")

        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)

        # Create a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = upload_dir / filename

        # Save the file
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Process the document
        document_text = process_uploaded_document(str(file_path))

        # Get segments and index for analysis
        segments, embeddings, index = process_documents()

        # Analyze the privacy policy
        analysis = analyze_privacy_policy(document_text, segments, index, framework)

        # Store analysis in database
        analysis_record = {
            "user_id": current_user.id,
            "filename": filename,
            "framework": framework,
            "analysis": analysis,
            "timestamp": datetime.utcnow()
        }
        
        await db.privacy_policy_analyses.insert_one(analysis_record)

        return {
            "message": "Privacy policy analysis completed",
            "analysis": analysis,
            "framework": framework
        }

    except Exception as e:
        logger.error(f"Error analyzing privacy policy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        file.file.close()

@router.post("/generate-privacy-policy")
async def generate_policy(
    framework: str = Form(...),
    format: str = Form(...),
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db)
):
    try:
        # Generate privacy policy
        policy_text = generate_privacy_policy(format)

        # Store generation record in database
        generation_record = {
            "user_id": current_user.id,
            "framework": framework,
            "format": format,
            "timestamp": datetime.utcnow()
        }
        
        await db.privacy_policy_generations.insert_one(generation_record)

        return {
            "message": "Privacy policy generated successfully",
            "policy": policy_text,
            "framework": framework,
            "format": format
        }

    except Exception as e:
        logger.error(f"Error generating privacy policy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-terms")
async def generate_terms(
    framework: str = Form(...),
    format: str = Form(...),
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db)
):
    try:
        # Generate Terms & Conditions
        terms_text = generate_terms_and_conditions(framework, format)

        # Store generation record in database
        generation_record = {
            "user_id": current_user.id,
            "framework": framework,
            "format": format,
            "document_type": "terms",
            "timestamp": datetime.utcnow()
        }
        
        await db.document_generations.insert_one(generation_record)

        # Create download URL
        file_path = terms_text.split("saved as ")[-1] if "saved as" in terms_text else None
        download_url = f"/api/compliance/download/{os.path.basename(file_path)}" if file_path else None

        return {
            "message": "Terms and Conditions generated successfully",
            "terms": terms_text,
            "framework": framework,
            "format": format,
            "download_url": download_url
        }

    except Exception as e:
        logger.error(f"Error generating Terms and Conditions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{filename}")
async def download_file(
    filename: str,
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        # Check in downloads directory first (new location)
        downloads_path = os.path.join("downloads", filename)
        if os.path.exists(downloads_path):
            return FileResponse(
                downloads_path,
                media_type="application/octet-stream",
                filename=filename
            )
        
        # Fallback to generated_documents directory (legacy location)
        generated_path = os.path.join("generated_documents", filename)
        if os.path.exists(generated_path):
            return FileResponse(
                generated_path,
                media_type="application/octet-stream",
                filename=filename
            )
            
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-framework")
async def upload_framework(
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db)
):
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.docx')):
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed")

        # Create frameworks directory if it doesn't exist
        frameworks_dir = Path("compliance_frameworks")
        frameworks_dir.mkdir(exist_ok=True)

        # Create a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = frameworks_dir / filename
        logger.info(f"Target file path: {file_path}")

        # Save the file
        try:
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            logger.info("File saved successfully")
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

        # Process the document using compliance_rag
        try:
            logger.info("Processing framework document...")
            # Process only the new document
            segments, embeddings, index = process_documents(str(file_path))
            logger.info("Framework document processed successfully")

            # Store framework info in database
            framework_doc = {
                "filename": filename,
                "original_name": file.filename,
                "user_id": current_user.id,
                "upload_date": datetime.utcnow(),
                "file_path": str(file_path),
                "file_type": file.content_type,
                "status": "processed",
                "file_hash": hashlib.md5(str(file_path).encode()).hexdigest(),
                "content_hash": hashlib.sha256(open(file_path, 'rb').read()).hexdigest(),
                "segments_count": len(segments) if segments is not None else 0,
                "embeddings_count": embeddings.shape[0] if embeddings is not None else 0,
                "index_vectors": index.ntotal if index is not None else 0
            }
            
            result = await db.framework_documents.insert_one(framework_doc)
            logger.info(f"Framework document info stored in database with ID: {result.inserted_id}")

            return {
                "message": "Framework document uploaded and processed successfully",
                "filename": file.filename,
                "document_id": str(result.inserted_id)
            }

        except Exception as e:
            logger.error(f"Error processing framework document: {str(e)}")
            # Clean up the file if processing fails
            try:
                file_path.unlink()
            except:
                pass
            raise HTTPException(status_code=500, detail=f"Error processing framework document: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload_framework: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    finally:
        try:
            file.file.close()
        except:
            pass 

@router.get("/framework-documents")
async def get_framework_documents(
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db)
):
    try:
        # Fetch all framework documents
        cursor = db.framework_documents.find({})
        documents = await cursor.to_list(length=None)
        
        # Transform the documents to include only necessary fields
        transformed_docs = []
        for doc in documents:
            transformed_docs.append({
                "id": str(doc["_id"]),
                "filename": doc["original_name"],
                "upload_date": doc["upload_date"],
                "file_type": doc["file_type"],
                "status": doc["status"],
                "segments_count": doc["segments_count"],
                "embeddings_count": doc["embeddings_count"],
                "index_vectors": doc["index_vectors"]
            })
        
        return transformed_docs
    except Exception as e:
        logger.error(f"Error fetching framework documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback")
async def submit_feedback(
    request: Request,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Submit feedback on chatbot responses to improve future query classification.
    """
    try:
        data = await request.json()
        
        query = data.get("query")
        was_helpful = data.get("was_helpful")  # Boolean
        session_id = data.get("session_id")
        
        if not all([query is not None, was_helpful is not None, session_id]):
            raise HTTPException(
                status_code=422, 
                detail="query, was_helpful, and session_id are required"
            )
        
        # Determine if the query was actually compliance-related based on user feedback
        # If user found it helpful, then our classification was likely correct
        # If not helpful and we classified as compliance, then we were wrong
        actual_classification = was_helpful  # Simplified assumption
        
        # Learn from this interaction
        learn_from_user_interaction(query, was_helpful, actual_classification)
        
        # Store feedback in database for analytics
        feedback_record = {
            "user_id": current_user.id,
            "session_id": session_id,
            "query": query,
            "was_helpful": was_helpful,
            "timestamp": datetime.utcnow()
        }
        
        await database.db.feedback.insert_one(feedback_record)
        
        return {
            "message": "Feedback received successfully",
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/classification-accuracy")
async def get_classification_accuracy(
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Get classification accuracy metrics for system monitoring.
    """
    try:
        # Only allow admins and superadmins to view these metrics
        if current_user.role not in ["admin", "superadmin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can view classification metrics"
            )
        
        # Get feedback data from database
        feedback_data = await database.db.feedback.find({}).to_list(length=None)
        
        if not feedback_data:
            return {
                "total_queries": 0,
                "helpful_responses": 0,
                "accuracy_rate": 0.0,
                "recent_accuracy": 0.0
            }
        
        total_queries = len(feedback_data)
        helpful_responses = sum(1 for f in feedback_data if f.get("was_helpful", False))
        accuracy_rate = helpful_responses / total_queries if total_queries > 0 else 0.0
        
        # Calculate recent accuracy (last 50 queries)
        recent_feedback = sorted(feedback_data, key=lambda x: x.get("timestamp", datetime.min()))[-50:]
        recent_helpful = sum(1 for f in recent_feedback if f.get("was_helpful", False))
        recent_accuracy = recent_helpful / len(recent_feedback) if recent_feedback else 0.0
        
        return {
            "total_queries": total_queries,
            "helpful_responses": helpful_responses,
            "accuracy_rate": round(accuracy_rate * 100, 2),
            "recent_accuracy": round(recent_accuracy * 100, 2),
            "recent_sample_size": len(recent_feedback)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching classification accuracy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/management-logs")
async def get_management_logs(
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    activity_type: Optional[str] = None,
    team_member: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    skip: int = 0
):
    """
    Get activity logs for management team dashboard.
    Aggregates logs from Azure compliance, UI testing, document uploads, and reports.
    """
    try:
        # Only allow management_team to access this endpoint
        if current_user.role != 'management_team':
            raise HTTPException(
                status_code=403,
                detail="Only management team can access activity logs"
            )
        
        # Get all users in the same organization (compliance_team and it_team)
        target_users = await db.users.find({
            "role": {"$in": ["compliance_team", "it_team"]},
            "organization_id": current_user.organization_id,
            "is_active": True
        }).to_list(length=None)
        
        if not target_users:
            return {
                "logs": [],
                "summary": {
                    "today": {"scans": 0, "analyses": 0, "reports": 0, "uploads": 0},
                    "this_week": {"scans": 0, "analyses": 0, "reports": 0, "uploads": 0}
                },
                "total": 0
            }
        
        user_ids = [str(user["_id"]) for user in target_users]
        user_emails = {str(user["_id"]): user.get("email", "Unknown") for user in target_users}
        user_roles = {str(user["_id"]): user.get("role", "Unknown") for user in target_users}
        
        # If team_member is provided, look up user by email to get their user_id
        team_member_user_id = None
        if team_member:
            # Try to find user by email
            user_by_email = await db.users.find_one({
                "email": team_member,
                "organization_id": current_user.organization_id,
                "is_active": True
            })
            if user_by_email:
                team_member_user_id = str(user_by_email["_id"])
            # If user not found by email, we'll filter logs by email later
        
        # Build date filter
        date_filter = {}
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                date_filter["$gte"] = start_dt
            except ValueError:
                pass
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                date_filter["$lt"] = end_dt
            except ValueError:
                pass
        
        all_logs = []
        
        # 1. Azure Compliance Analyses
        azure_query = {"user_id": {"$in": user_ids}}
        if date_filter:
            azure_query["created_at"] = date_filter
        if team_member_user_id:
            azure_query["user_id"] = team_member_user_id
        if status:
            if status == "success":
                azure_query["overall_status"] = {"$in": ["Compliant", "Partial"]}
            elif status == "failed":
                azure_query["overall_status"] = "Non-Compliant"
        
        azure_results = await db.azure_compliance_results.find(azure_query).sort("created_at", -1).limit(limit).to_list(length=None)
        for result in azure_results:
            all_logs.append({
                "id": str(result["_id"]),
                "timestamp": result.get("created_at", result.get("analyzed_at", datetime.utcnow())),
                "user_id": result.get("user_id"),
                "user_email": result.get("user_email", user_emails.get(result.get("user_id"), "Unknown")),
                "user_role": user_roles.get(result.get("user_id"), "Unknown"),
                "activity_type": "azure_analysis",
                "activity_label": "Azure Compliance Analysis",
                "description": f"Analyzed document: {result.get('document_name', 'Unknown')}",
                "status": "success" if result.get("overall_status") in ["Compliant", "Partial"] else "warning",
                "details": {
                    "document_name": result.get("document_name"),
                    "score": result.get("overall_score", result.get("score", 0)),
                    "status": result.get("overall_status"),
                    "frameworks": result.get("frameworks_analyzed", [])
                },
                "icon": "📊"
            })
        
        # 2. UI Testing Scans
        ui_query = {"organization_id": current_user.organization_id}
        if date_filter:
            ui_query["created_at"] = date_filter
        if team_member_user_id:
            ui_query["user_id"] = team_member_user_id
        
        ui_results = await db.ui_testing_site_results.find(ui_query).sort("created_at", -1).limit(limit).to_list(length=None)
        for result in ui_results:
            user_id = result.get("user_id")
            scan_result = result.get("result", {})
            summary = scan_result.get("summary", {})
            all_logs.append({
                "id": str(result["_id"]),
                "timestamp": datetime.fromtimestamp(result.get("created_at", 0)) if isinstance(result.get("created_at"), int) else result.get("created_at", datetime.utcnow()),
                "user_id": user_id,
                "user_email": user_emails.get(user_id, "Unknown") if user_id else "System",
                "user_role": user_roles.get(user_id, "Unknown") if user_id else "System",
                "activity_type": "ui_scan",
                "activity_label": "UI Testing Scan",
                "description": f"Scanned website: {result.get('url', 'Unknown')}",
                "status": "success",
                "details": {
                    "url": result.get("url"),
                    "pages_scanned": summary.get("pages_scanned", 0),
                    "accessibility_score": summary.get("accessibility_score", 0),
                    "mode": result.get("mode", "all")
                },
                "icon": "🔍"
            })
        
        # 3. Document Uploads
        doc_query = {"user_id": {"$in": user_ids}}
        if date_filter:
            doc_query["upload_date"] = date_filter
        if team_member_user_id:
            doc_query["user_id"] = team_member_user_id
        
        doc_results = await db.documents.find(doc_query).sort("upload_date", -1).limit(limit).to_list(length=None)
        for result in doc_results:
            all_logs.append({
                "id": str(result["_id"]),
                "timestamp": result.get("upload_date", datetime.utcnow()),
                "user_id": result.get("user_id"),
                "user_email": user_emails.get(result.get("user_id"), "Unknown"),
                "user_role": user_roles.get(result.get("user_id"), "Unknown"),
                "activity_type": "document_upload",
                "activity_label": "Document Upload",
                "description": f"Uploaded document: {result.get('original_name', result.get('filename', 'Unknown'))}",
                "status": result.get("status", "processed") == "processed" and "success" or "warning",
                "details": {
                    "filename": result.get("original_name", result.get("filename")),
                    "doc_type": result.get("doc_type", "unknown"),
                    "file_type": result.get("file_type")
                },
                "icon": "📄"
            })
        
        # 4. Compliance Checklist Generation
        checklist_query = {"user_id": {"$in": user_ids}, "activity_type": "checklist_generation"}
        if date_filter:
            checklist_query["timestamp"] = date_filter
        if team_member_user_id:
            checklist_query["user_id"] = team_member_user_id
        
        checklist_logs = await db.activity_logs.find(checklist_query).sort("timestamp", -1).limit(limit).to_list(length=None)
        
        logger.info(f"Found {len(checklist_logs)} checklist generation logs")
        for log_entry in checklist_logs:
            user_id_checklist = log_entry.get("user_id")
            all_logs.append({
                "id": str(log_entry.get("_id", "")),
                "timestamp": log_entry.get("timestamp", log_entry.get("generated_at", datetime.utcnow())),
                "user_id": user_id_checklist,
                "user_email": user_emails.get(user_id_checklist, log_entry.get("user_email", "Unknown")),
                "user_role": user_roles.get(user_id_checklist, "Unknown"),
                "activity_type": "checklist_generation",
                "activity_label": log_entry.get("activity_label", "Compliance Checklist Generated"),
                "description": log_entry.get("description", "Generated compliance checklist"),
                "status": log_entry.get("status", "success"),
                "details": log_entry.get("details", {}),
                "icon": log_entry.get("icon", "✅")
            })
        
        # 5. Report Downloads (from Azure compliance results - we'll track report generation as downloads)
        # Reports are generated on-demand, so we'll use the generate-report endpoint calls
        # For now, we'll note that reports can be generated from existing analyses
        
        # Filter by activity_type if specified
        if activity_type:
            all_logs = [log for log in all_logs if log["activity_type"] == activity_type]
        
        # Filter by email if team_member was provided but user_id wasn't found (or filter by email for exact match)
        if team_member and not team_member_user_id:
            # Filter logs by email (case-insensitive partial match)
            all_logs = [log for log in all_logs if team_member.lower() in log.get("user_email", "").lower()]
        elif team_member and team_member_user_id:
            # Double-check by email for exact match
            all_logs = [log for log in all_logs if log.get("user_email", "").lower() == team_member.lower()]
        
        # Filter by status if specified
        if status:
            all_logs = [log for log in all_logs if log["status"] == status]
        
        # Sort all logs by timestamp (most recent first)
        all_logs.sort(key=lambda x: x["timestamp"] if isinstance(x["timestamp"], datetime) else datetime.fromisoformat(str(x["timestamp"])), reverse=True)
        
        # Store total count before pagination
        total_count = len(all_logs)
        
        # Calculate summary statistics BEFORE pagination (to get accurate counts)
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        week_start = today_start - timedelta(days=now.weekday())
        
        today_logs = [log for log in all_logs if isinstance(log["timestamp"], datetime) and log["timestamp"] >= today_start]
        week_logs = [log for log in all_logs if isinstance(log["timestamp"], datetime) and log["timestamp"] >= week_start]
        
        # Apply pagination (skip and limit) AFTER calculating summary
        all_logs = all_logs[skip:skip + limit]
        
        summary = {
            "today": {
                "scans": len([l for l in today_logs if l["activity_type"] == "ui_scan"]),
                "analyses": len([l for l in today_logs if l["activity_type"] == "azure_analysis"]),
                "reports": 0,  # Reports are generated on-demand, not stored
                "uploads": len([l for l in today_logs if l["activity_type"] == "document_upload"]),
                "checklists": len([l for l in today_logs if l["activity_type"] == "checklist_generation"])
            },
            "this_week": {
                "scans": len([l for l in week_logs if l["activity_type"] == "ui_scan"]),
                "analyses": len([l for l in week_logs if l["activity_type"] == "azure_analysis"]),
                "reports": 0,
                "uploads": len([l for l in week_logs if l["activity_type"] == "document_upload"]),
                "checklists": len([l for l in week_logs if l["activity_type"] == "checklist_generation"])
            }
        }
        
        # Convert timestamps to ISO format strings
        for log in all_logs:
            if isinstance(log["timestamp"], datetime):
                log["timestamp"] = log["timestamp"].isoformat()
        
        return {
            "logs": all_logs,
            "summary": summary,
            "total": total_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching management logs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compliance-logs")
async def get_compliance_logs(
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    activity_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    skip: int = 0
):
    """
    Get activity logs for compliance team dashboard.
    Shows only the current user's own activities.
    Aggregates logs from Azure compliance analyses, document uploads, and reports.
    """
    try:
        # Only allow compliance_team to access this endpoint
        if current_user.role != 'compliance_team':
            raise HTTPException(
                status_code=403,
                detail="Only compliance team can access compliance logs"
            )
        
        user_id = str(current_user.id)
        user_email = current_user.email
        
        # Import ObjectId for proper user_id matching
        from bson import ObjectId
        
        # Build date filter
        date_filter = {}
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                date_filter["$gte"] = start_dt
            except ValueError:
                pass
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                date_filter["$lt"] = end_dt
            except ValueError:
                pass
        
        all_logs = []
        
        # 1. Azure Compliance Analyses (user's own)
        # Handle both ObjectId and string user_id formats
        try:
            user_id_obj = ObjectId(current_user.id) if isinstance(current_user.id, str) else current_user.id
        except:
            user_id_obj = current_user.id
        
        azure_query = {"$or": [{"user_id": user_id_obj}, {"user_id": user_id}]}
        if date_filter:
            azure_query["created_at"] = date_filter
        if status:
            if status == "success":
                azure_query["overall_status"] = {"$in": ["Compliant", "Partial"]}
            elif status == "failed":
                azure_query["overall_status"] = "Non-Compliant"
        
        azure_results = await db.azure_compliance_results.find(azure_query).sort("created_at", -1).limit(limit * 2).to_list(length=None)
        logger.info(f"Found {len(azure_results)} Azure compliance results for user {user_id}")
        for result in azure_results:
            frameworks = result.get("frameworks_analyzed", [])
            if isinstance(frameworks, dict):
                frameworks = list(frameworks.keys())
            
            all_logs.append({
                "id": str(result["_id"]),
                "timestamp": result.get("created_at", result.get("analyzed_at", datetime.utcnow())),
                "user_id": user_id,
                "user_email": user_email,
                "activity_type": "azure_analysis",
                "activity_label": "Azure Compliance Analysis",
                "description": f"Analyzed document: {result.get('document_name', 'Unknown')}",
                "status": "success" if result.get("overall_status") in ["Compliant", "Partial"] else "warning",
                "details": {
                    "document_name": result.get("document_name"),
                    "score": result.get("overall_score", result.get("score", 0)),
                    "status": result.get("overall_status"),
                    "frameworks": frameworks if frameworks else ["azure"]
                },
                "icon": "📊"
            })
        
        # 2. Document Uploads (user's own)
        # Handle both ObjectId and string user_id formats
        doc_query = {"$or": [{"user_id": user_id_obj}, {"user_id": user_id}]}
        if date_filter:
            doc_query["upload_date"] = date_filter
        
        doc_results = await db.documents.find(doc_query).sort("upload_date", -1).limit(limit).to_list(length=None)
        logger.info(f"Found {len(doc_results)} document uploads for user {user_id}")
        for result in doc_results:
            doc_type = result.get("doc_type", "unknown")
            # More precise framework detection - only exact matches or explicit framework types
            # Exclude common document types that should never be frameworks
            excluded_types = ["privacy_policy", "terms_and_conditions", "general_documentation", "other", "unknown"]
            is_framework = (
                doc_type in ["framework", "compliance_framework"] or 
                (isinstance(doc_type, str) and doc_type.lower() == "framework") or
                (isinstance(doc_type, str) and "compliance_framework" in doc_type.lower() and doc_type.lower() not in excluded_types)
            )
            
            # Ensure activity_type is correctly set - document_upload should NOT appear in other filters
            # Always default to document_upload unless explicitly a framework
            activity_type_value = "framework_upload" if is_framework else "document_upload"
            activity_label = "Framework Document Uploaded" if is_framework else "Document Upload"
            
            # Log for debugging
            logger.debug(f"Document upload: {result.get('original_name')}, doc_type: {doc_type}, is_framework: {is_framework}, activity_type: {activity_type_value}")
            
            all_logs.append({
                "id": str(result["_id"]),
                "timestamp": result.get("upload_date", datetime.utcnow()),
                "user_id": user_id,
                "user_email": user_email,
                "activity_type": activity_type_value,  # Use the correctly determined activity type
                "activity_label": activity_label,
                "description": f"Uploaded {result.get('original_name', result.get('filename', 'Unknown'))}",
                "status": result.get("status", "processed") == "processed" and "success" or "warning",
                "details": {
                    "filename": result.get("original_name", result.get("filename")),
                    "doc_type": doc_type,
                    "file_type": result.get("file_type"),
                    "is_framework": is_framework
                },
                "icon": "📚" if is_framework else "📄"
            })
        
        # 3. Azure AD Configuration Fetches (if user has Azure connection)
        # Handle both ObjectId and string user_id formats
        azure_config_query = {
            "$or": [{"user_id": user_id_obj}, {"user_id": user_id}],
            "organization_id": current_user.organization_id
        }
        if date_filter:
            azure_config_query["timestamp"] = date_filter
        
        azure_config_logs = await db.azure_config_logs.find(azure_config_query).sort("timestamp", -1).limit(limit).to_list(length=None)
        for log_entry in azure_config_logs:
            all_logs.append({
                "id": str(log_entry.get("_id", "")),
                "timestamp": log_entry.get("timestamp", datetime.utcnow()),
                "user_id": user_id,
                "user_email": user_email,
                "activity_type": "azure_config_fetch",
                "activity_label": "Azure AD Config Fetch",
                "description": f"Fetched Azure AD configuration: {log_entry.get('change_type', 'config_fetch')}",
                "status": "success" if log_entry.get("status") == "success" else "failed",
                "details": {
                    "change_type": log_entry.get("change_type"),
                    "error_message": log_entry.get("error_message")
                },
                "icon": "🔐"
            })
        
        # 4. Compliance Checklist Generation (user's own)
        checklist_query = {"$or": [{"user_id": user_id_obj}, {"user_id": user_id}], "activity_type": "checklist_generation"}
        if date_filter:
            checklist_query["timestamp"] = date_filter
        
        checklist_logs = await db.activity_logs.find(checklist_query).sort("timestamp", -1).limit(limit).to_list(length=None)
        
        logger.info(f"Found {len(checklist_logs)} checklist generation logs for user {user_id}")
        for log_entry in checklist_logs:
            all_logs.append({
                "id": str(log_entry.get("_id", "")),
                "timestamp": log_entry.get("timestamp", log_entry.get("generated_at", datetime.utcnow())),
                "user_id": user_id,
                "user_email": user_email,
                "activity_type": "checklist_generation",
                "activity_label": log_entry.get("activity_label", "Compliance Checklist Generated"),
                "description": log_entry.get("description", "Generated compliance checklist"),
                "status": log_entry.get("status", "success"),
                "details": log_entry.get("details", {}),
                "icon": log_entry.get("icon", "✅")
            })
        
        # Filter by activity_type if specified - ensure strict matching
        if activity_type:
            filtered_logs = []
            for log in all_logs:
                # Strict equality check - ensure activity_type matches exactly
                log_activity_type = log.get("activity_type")
                if log_activity_type == activity_type:
                    filtered_logs.append(log)
                # Debug logging for mismatches
                elif log_activity_type and activity_type:
                    logger.debug(f"Filter mismatch: log activity_type='{log_activity_type}', filter='{activity_type}'")
            logger.info(f"Filtered logs: {len(all_logs)} -> {len(filtered_logs)} (filter: {activity_type})")
            all_logs = filtered_logs
        
        # Filter by status if specified
        if status:
            all_logs = [log for log in all_logs if log.get("status") == status]
        
        # Sort all logs by timestamp (most recent first)
        all_logs.sort(key=lambda x: x["timestamp"] if isinstance(x["timestamp"], datetime) else datetime.fromisoformat(str(x["timestamp"])), reverse=True)
        
        # Store total count before pagination
        total_count = len(all_logs)
        
        # Calculate summary statistics BEFORE pagination
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        week_start = today_start - timedelta(days=now.weekday())
        
        today_logs = [log for log in all_logs if isinstance(log["timestamp"], datetime) and log["timestamp"] >= today_start]
        week_logs = [log for log in all_logs if isinstance(log["timestamp"], datetime) and log["timestamp"] >= week_start]
        
        # Apply pagination (skip and limit) AFTER calculating summary
        all_logs = all_logs[skip:skip + limit]
        
        # Calculate summary
        summary = {
            "today": {
                "analyses": len([l for l in today_logs if l["activity_type"] == "azure_analysis"]),
                "uploads": len([l for l in today_logs if l["activity_type"] == "document_upload"]),
                "framework_uploads": len([l for l in today_logs if l["activity_type"] == "framework_upload"]),
                "config_fetches": len([l for l in today_logs if l["activity_type"] == "azure_config_fetch"]),
                "checklists": len([l for l in today_logs if l["activity_type"] == "checklist_generation"]),
                "total": len(today_logs)
            },
            "this_week": {
                "analyses": len([l for l in week_logs if l["activity_type"] == "azure_analysis"]),
                "uploads": len([l for l in week_logs if l["activity_type"] == "document_upload"]),
                "framework_uploads": len([l for l in week_logs if l["activity_type"] == "framework_upload"]),
                "config_fetches": len([l for l in week_logs if l["activity_type"] == "azure_config_fetch"]),
                "checklists": len([l for l in week_logs if l["activity_type"] == "checklist_generation"]),
                "total": len(week_logs)
            }
        }
        
        # Convert timestamps to ISO format strings
        for log in all_logs:
            if isinstance(log["timestamp"], datetime):
                log["timestamp"] = log["timestamp"].isoformat()
        
        return {
            "logs": all_logs,
            "summary": summary,
            "total": total_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching compliance logs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 