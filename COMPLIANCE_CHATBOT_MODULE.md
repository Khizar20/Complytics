# Compliance Chatbot Module - Roman Urdu Documentation

## Module Ka Naam
**Compliance Chatbot Module** - Ye ek AI-powered chatbot hai jo compliance frameworks (GDPR, ISO 27001, SOC 2, HIPAA, PCI DSS, etc.) ke baare mein sawaal ka jawab deta hai.

## Module Ka Kaam Kya Hai?

Ye module users ko compliance-related queries ka intelligent jawab deta hai. Ye system:
- User ke sawaal ko samajhta hai
- Relevant compliance experts ko select karta hai
- Uploaded documents ko analyze karta hai
- Privacy policies aur terms & conditions generate karta hai
- Conversation history maintain karta hai

## Flow Kaise Kaam Karta Hai?

### 1. User Query Receive Karna
- User frontend se query bhejta hai (`/api/compliance/chat` endpoint par)
- System query ko receive karta hai aur session ID ke saath track karta hai

### 2. Query Analysis
- **Ambiguous Query Detection**: Agar query unclear hai, system clarification mangta hai
- **Intent Analysis**: System query ka intent detect karta hai (document analysis, general QA, scenario guidance, etc.)
- **Document Check**: System check karta hai ke user ne koi document upload kiya hai ya nahi

### 3. Expert Selection
- System relevant compliance experts ko select karta hai based on:
  - Query type (GDPR, ISO 27001, SOC 2, etc.)
  - Framework detection
  - Document type (privacy policy, terms & conditions, general docs)
- Experts use RAG (Retrieval Augmented Generation) technique se select hote hain

### 4. Response Generation
- Selected experts se relevant information retrieve hoti hai
- AI (Gemini) use karke comprehensive response generate hota hai
- Response ko format karke user ko bhej diya jata hai

### 5. Document Processing (Agar Upload Kiya Ho)
- Document type detect hota hai (privacy policy, terms, general)
- Document analyze hota hai against compliance frameworks
- Improvements suggest kiye jate hain
- New documents generate kiye ja sakte hain

### 6. History Management
- Har conversation session ke liye history maintain hoti hai
- Database mein store hoti hai
- Context ke liye use hoti hai future queries mein

## Technical Working

### RAG (Retrieval Augmented Generation) System
1. **Embeddings**: Compliance documents ka embeddings create hota hai using SentenceTransformer
2. **FAISS Index**: Embeddings FAISS index mein store hote hain fast retrieval ke liye
3. **Query Embedding**: User query ka embedding create hota hai
4. **Similarity Search**: Similar documents retrieve hote hain
5. **Context Building**: Retrieved documents se context build hota hai
6. **AI Generation**: Gemini AI use karke final response generate hota hai

### Expert System
- Har compliance framework ka ek expert hota hai
- Experts specialized knowledge rakhte hain apne framework ke baare mein
- System automatically relevant experts ko select karta hai

### Caching System
- Frequently asked queries ka cache maintain hota hai
- Same queries ke liye fast response milta hai
- Cache file: `compliance_cache/query_cache.json`

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
   - Embedding generation
   - FAISS index management
   - Expert selection logic
   - Query processing functions
   - Document analysis functions
   - Response generation functions

3. **`Complytics Backend/compliance_rag_refined.py`**
   - Refined intent analysis
   - Expert routing logic
   - Document compliance expert
   - Scenario guidance expert
   - Short QA answer generation

4. **`Complytics Backend/db.py`**
   - Database connection
   - MongoDB operations

5. **`Complytics Backend/schemas/users.py`**
   - User schema definitions

### Frontend Files (React/JSX)

1. **`src/components/team/ComplianceChat.jsx`**
   - Main chat interface component
   - Message display
   - Input handling
   - File upload UI
   - Session management
   - History display

2. **`src/components/ui/FormattedResponse.jsx`**
   - Response formatting component
   - Markdown rendering
   - Code highlighting
   - Expert tags display

3. **`src/lib/api.js`**
   - API utility functions
   - API URL building

4. **`src/context/AuthContext.jsx`**
   - Authentication context
   - Token management

### Configuration Files

1. **`Complytics Backend/config.py`**
   - Application configuration
   - Environment variables

2. **`Complytics Backend/requirements.txt`**
   - Python dependencies

### Data Files

1. **`Complytics Backend/compliance_frameworks/`**
   - PDF files of compliance frameworks
   - Source documents for RAG

2. **`Complytics Backend/embeddings/`**
   - `document_embeddings.npy` - Document embeddings
   - `document_map.json` - Document mapping

3. **`Complytics Backend/faiss_indexes/`**
   - `compliance_index.faiss` - FAISS index file

4. **`Complytics Backend/compliance_cache/`**
   - `query_cache.json` - Query cache

## Key Functions

### Main Functions in `compliance_rag.py`:
- `process_query_optimized()` - Query processing
- `select_relevant_experts_optimized()` - Expert selection
- `get_embedding_optimized()` - Embedding generation
- `detect_query_type()` - Query type detection
- `analyze_document_intent()` - Document intent analysis
- `generate_privacy_policy()` - Privacy policy generation
- `generate_terms_and_conditions()` - Terms generation
- `process_uploaded_document()` - Document processing

### Main Functions in `compliance_rag_refined.py`:
- `analyze_refined_intent()` - Intent analysis
- `scenario_guidance_expert()` - Scenario guidance
- `document_compliance_expert()` - Document compliance
- `short_qa_answer()` - Short answers

## Database Collections

1. **`compliance_chat_history`** - Chat history storage
2. **`documents`** - Uploaded documents storage

## API Endpoints

- `POST /api/compliance/chat` - Chat query endpoint
- `POST /api/compliance/upload` - Document upload endpoint
- `POST /api/compliance/reset` - Reset conversation endpoint

## Dependencies

- **FastAPI** - Web framework
- **Google Gemini AI** - LLM for response generation
- **SentenceTransformer** - Embedding model
- **FAISS** - Vector similarity search
- **MongoDB** - Database
- **PyPDF2/pdfplumber** - PDF processing
- **python-docx** - DOCX processing

## Summary

Ye module ek intelligent compliance chatbot hai jo:
- User queries ko understand karta hai
- Relevant experts ko select karta hai
- Comprehensive answers generate karta hai
- Documents ko analyze aur generate karta hai
- Conversation context maintain karta hai

Sab kuch RAG technique aur AI (Gemini) ke combination se kaam karta hai.

