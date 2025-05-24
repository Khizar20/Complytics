from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from typing import Optional, List
import os
from datetime import datetime
import shutil
from pathlib import Path
import logging
from schemas.users import UserInDB  # Changed to UserInDB which is the correct model
from db import database
from compliance_rag import (
    process_documents,
    interactive_compliance_query,
    ConversationHistory,
    select_relevant_experts,
    expert_security_controls,
    expert_privacy_regulations,
    expert_audit_compliance,
    aggregate_expert_outputs,
    is_compliance_related,
    generate_non_compliance_response,
    detect_query_type,
    get_framework_recommendation,
    process_uploaded_document,
    analyze_privacy_policy,
    generate_privacy_policy,
    extract_text_from_pdf,
    extract_text_from_docx,
    rate_limited_generate_content,
    generate_terms_and_conditions,
    learn_from_user_interaction,
    analyze_document_intent,
    generate_comprehensive_document_analysis,
    generate_intelligent_compliant_document,
    create_docx_with_download_link,
    format_document_response_with_download,
    generate_document_improvement_suggestions
)
from routes.auth import get_current_user  # Add this import for authentication
from fastapi.responses import FileResponse
import hashlib
from fastapi import status

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["compliance"])

# Initialize conversation history
conversation_histories = {}

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

        # Check if user has uploaded documents
        has_uploaded_doc = False
        latest_doc = await db.documents.find_one(
            {"session_id": session_id},
            sort=[("upload_date", -1)]
        )
        if latest_doc:
            has_uploaded_doc = True

        # Intelligent document intent analysis
        intent_analysis = analyze_document_intent(query, conversation_context, has_uploaded_doc)
        logger.info(f"Intent analysis: {intent_analysis}")

        # Handle different document intents
        if intent_analysis["intent"] == "ANALYZE_UPLOADED":
            if not has_uploaded_doc:
                response = "I'd be happy to analyze your document for compliance! However, I don't see any uploaded documents in our current session. Please upload your privacy policy or terms & conditions document first, and then I can provide a comprehensive compliance analysis."
                experts = []
            else:
                # Extract text from the latest document
                if latest_doc["file_path"].endswith('.pdf'):
                    document_text = extract_text_from_pdf(latest_doc["file_path"])
                elif latest_doc["file_path"].endswith('.docx'):
                    document_text = extract_text_from_docx(latest_doc["file_path"])
                else:
                    document_text = "Unsupported file format"
                
                # Generate comprehensive analysis
                framework = intent_analysis.get("framework", "GDPR")
                document_type = intent_analysis.get("document_type", "document")
                
                response = generate_comprehensive_document_analysis(
                    document_text, framework, document_type
                )
                experts = ['privacy', 'audit']

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
                if latest_doc["file_path"].endswith('.pdf'):
                    document_text = extract_text_from_pdf(latest_doc["file_path"])
                elif latest_doc["file_path"].endswith('.docx'):
                    document_text = extract_text_from_docx(latest_doc["file_path"])
                else:
                    document_text = "Unsupported file format"
                
                framework = intent_analysis.get("framework", "GDPR")
                document_type = intent_analysis.get("document_type", "document")
                
                response = generate_comprehensive_document_analysis(
                    document_text, framework, document_type
                )
                experts = ['privacy', 'audit']

        elif intent_analysis["intent"] == "GET_IMPROVEMENT_SUGGESTIONS":
            if not has_uploaded_doc:
                response = "I'd be happy to provide improvement suggestions for your document! Please upload your current privacy policy or terms & conditions document first, and I'll analyze it and give you specific recommendations on how to make it better."
                experts = []
            else:
                # Extract text from uploaded document
                if latest_doc["file_path"].endswith('.pdf'):
                    document_text = extract_text_from_pdf(latest_doc["file_path"])
                elif latest_doc["file_path"].endswith('.docx'):
                    document_text = extract_text_from_docx(latest_doc["file_path"])
                else:
                    document_text = "Unsupported file format"
                
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
                if latest_doc["file_path"].endswith('.pdf'):
                    document_text = extract_text_from_pdf(latest_doc["file_path"])
                elif latest_doc["file_path"].endswith('.docx'):
                    document_text = extract_text_from_docx(latest_doc["file_path"])
                else:
                    document_text = "Unsupported file format"
                
                framework = intent_analysis.get("framework", "GDPR")
                document_type = intent_analysis.get("document_type", "privacy_policy")
                
                # First analyze the current document
                analysis = generate_comprehensive_document_analysis(
                    document_text, framework, document_type
                )
                
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
            "document says", "in the uploaded document", "from the document"
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
                
                response = rate_limited_generate_content(prompt)
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
                is_compliance, reason = is_compliance_related(query, conversation_context)
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

                    # Detect query type and get required experts
                    query_type, required_experts = detect_query_type(query, conversation_context)
                    logger.info(f"Query type: {query_type}, Required experts: {required_experts}")

                    # For framework selection queries, use specialized handler
                    if query_type == 'framework_selection':
                        response, processing_time = get_framework_recommendation(query)
                        experts = ['audit']
                    else:
                        # Get expert responses
                        expert_responses = []
                        for expert in required_experts:
                            logger.info(f"Getting response from expert: {expert}")
                            if expert == "security":
                                response = expert_security_controls(query, conversation_context, conversation_context)
                            elif expert == "privacy":
                                response = expert_privacy_regulations(query, conversation_context, conversation_context)
                            elif expert == "audit":
                                response = expert_audit_compliance(query, conversation_context, conversation_context)
                            expert_responses.append(response)

                        # Aggregate expert responses
                        logger.info("Aggregating expert responses...")
                        response = aggregate_expert_outputs(expert_responses, query, conversation_context)
                        experts = required_experts

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
        # Get all chat sessions for the user
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
        
        # Calculate success rate (assuming responses with experts consulted are successful)
        successful_responses = sum(
            1 for session in sessions
            for message in session.get('messages', [])
            if message.get('experts_consulted')
        )
        success_rate = (successful_responses / total_queries * 100) if total_queries > 0 else 0
        
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
                "status": "processed"
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

        return {
            "message": "Document uploaded and processed successfully",
            "filename": file.filename,
            "document_id": str(document["_id"])
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