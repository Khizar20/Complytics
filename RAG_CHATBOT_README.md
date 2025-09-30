# Complytics RAG Chatbot

## Overview
The Complytics RAG (Retrieval-Augmented Generation) Chatbot provides compliance-focused assistance, document analysis, and compliant document generation. It combines retrieval over compliance frameworks with expert-style generation and conversation memory, exposed via FastAPI endpoints and a React UI.

## High-Level Architecture
- Backend (FastAPI): `Complytics Backend/`
  - Core RAG engine: `compliance_rag.py`
  - HTTP API: `routes/compliance.py`, mounted at `/api/compliance`
  - App init and CORS: `app.py`
  - Configuration/env: `config.py`
  - Persistence: MongoDB via `db.py` and `database.py`
  - Artifacts: `compliance_frameworks/`, `embeddings/`, `faiss_indexes/`, `uploads/`, `downloads/`
- Frontend (React, MUI): `src/components/team/ComplianceChat.jsx`
  - Chat UI with session history, uploads, analytics, feedback

## Data Flow
1) User query is sent from the frontend to `POST /api/compliance/chat`.
2) Backend creates or retrieves `ConversationHistory` for `session_id`.
3) Intent routing (document analyze/generate/improve vs. general Q&A) via `analyze_document_intent`.
4) If general compliance Q&A:
   - Ensure vectors exist: `process_documents()` builds/loads segments, embeddings, FAISS index from `compliance_frameworks/`.
   - Embed query: `get_embedding_optimized(query)`.
   - Retrieve top-k segments with FAISS, form `retrieved_context`.
   - Process with fast path expert system: `process_query_optimized(query, context, conversation_context, conversation_obj)`.
   - Expert selection: `select_relevant_experts_optimized(query)` and cached sub-experts like `expert_privacy_regulations`, `expert_security_controls`, ... Aggregate via `aggregate_expert_outputs`.
   - Generation is rate-limited and cached: `rate_limited_generate_content_optimized` with prompt-hash keying into `QUERY_CACHE`.
5) Update `ConversationHistory` and write analytics and messages to MongoDB (`compliance_chat_history`).
6) Return `{ response, experts_consulted, response_time, session_id }`.

## Key Components
- Retrieval
  - Preprocessed framework PDFs (GDPR, ISO 27001, SOC 2, PCI DSS, etc.) in `compliance_frameworks/`.
  - Text segmentation + `sentence-transformers` embeddings saved to `embeddings/`.
  - FAISS index stored under `faiss_indexes/` and reused across runs.
- Expert System + Aggregation
  - Lightweight routing to relevant domain “experts” (privacy, audit, security, finance, international, operational, industry_specific).
  - Cached expert responses via `cached_expert_response` and hash keys.
  - Aggregation merges multiple expert answers into a concise final response.
- Generation
  - LLM calls via `rate_limited_generate_content_optimized` with exponential backoff, caching, and token limits for speed.
- Conversation & Analytics
  - `ConversationHistory` maintains short-term context and `get_context()` informs classification and response shaping.
  - MongoDB collections persist chat history, feedback, document generations, and analytics.
- Document Workflows
  - Upload PDFs/DOCX at `POST /api/compliance/upload-document` → extraction and storage.
  - Analyze privacy policies: `POST /api/compliance/analyze-privacy-policy`.
  - Generate privacy policy or terms: `POST /api/compliance/generate-privacy-policy`, `POST /api/compliance/generate-terms` with downloadable DOCX links.

## Backend APIs (selected)
- `POST /api/compliance/chat` — main chat entrypoint (auth required)
- `POST /api/compliance/reset` — reset session conversation
- `GET /api/compliance/history?session_id=` — session history
- `GET /api/compliance/all-history` — all sessions for user
- `GET /api/compliance/analytics` — aggregates for dashboard
- `POST /api/compliance/upload-document` — upload PDF/DOCX
- `POST /api/compliance/analyze-privacy-policy` — analyze document
- `POST /api/compliance/generate-privacy-policy` — generate privacy policy
- `POST /api/compliance/generate-terms` — generate terms & conditions
- `GET /api/compliance/download/{filename}` — download generated files
- `POST /api/compliance/feedback` — submit response feedback
- `GET /api/compliance/classification-accuracy` — admin metrics

## Frontend (ComplianceChat.jsx)
- Sends chat to `POST /api/compliance/chat` with `session_id`.
- Shows typewriter responses, expert labels, and download links.
- Supports uploads, analysis, generation dialogs.
- Provides thumbs-up/down feedback per message.
- Loads history (`/api/compliance/history`, `/all-history`) and analytics for dashboard.

## Caching & Rate Limiting
- `QUERY_CACHE` caches LLM generations and expert responses via prompt/content hashes.
- Save-to-disk cadence (every N entries) to reduce I/O.
- `sleep_and_retry` + limits with a reduced backoff and max retries.

## Configuration & Persistence
- Env config via `config.py` and `.env` (MongoDB, auth, SMTP).
- Embeddings: `embeddings/` (np arrays and document maps).
- Indexes: `faiss_indexes/` (shared across sessions).
- Uploads/downloads stored under `uploads/` and `downloads/`.

## Running the System
- Backend
  - Activate venv and install requirements: `pip install -r "Complytics Backend/requirements.txt"`
  - Start FastAPI app (e.g., `uvicorn Complytics Backend.app:app --reload`)
- Frontend
  - Install: `npm install`
  - Start: `npm run dev` (Vite on `http://localhost:5173`)

## Limitations
- Retrieval corpus limited to provided PDFs; coverage impacts recall.
- Simple expert selection/aggregation can mis-rank contexts for complex multi-framework queries.
- Caching is file-based and single-node; not distributed.
- Conversation context windowing is lightweight; no long-term vector memory of prior chats.

## Research-Grade Improvement Ideas
- Retrieval & Indexing
  - Use hybrid search (sparse BM25 + dense bi-encoder) and rerankers (e.g., monoT5/Cross-Encoder) to improve top-k quality.
  - Segment-aware indexing (structural parsing of PDFs to preserve headings/sections) and hierarchical retrieval (document → section → chunk).
  - Query expansion with reciprocal rank fusion and ColBERT-style late interaction for precision at k.
- Generation & Reasoning
  - Multi-step CoT/ToT: have experts produce chain-of-thought/drafts, then a verifier model refines and grounds with citations.
  - Toolformer-style retrieval calls during generation; selective re-retrieval when the model detects uncertainty.
  - Evidence-citation enforcement: require each claim to trace to retrieved spans; add JSON schema for answers with explicit evidence IDs.
- Routing & Orchestration
  - Learned expert router (Mixture-of-Experts) using small classifier fine-tuned from chat logs + feedback.
  - Adaptive compute: quick path for easy Qs, full pipeline for ambiguous or high-risk compliance queries.
  - Add streaming with server-sent events for progressive answers from `get_progressive_response`.
- Memory & Personalization
  - Vector memory per user/session; store long-term embeddings for prior Q&A and org context.
  - Retrieval-time personalization using tenant metadata and role.
- Feedback & Evaluation
  - Close the loop with RLHF-style preference models trained on `/feedback` data.
  - Automatic offline evaluation with BERTScore, BLEU, faithfulness metrics and synthetic query sets per framework.
  - Hallucination detection via entailment models (e.g., DeBERTa NLI) that check answer claims against retrieved evidence.
- Reliability & Ops
  - Distributed cache (Redis) and background workers for embedding/index refresh.
  - Observability: tracing spans around retrieval/generation; token/log costs; per-expert latency.
  - Canary evaluation for new framework uploads; indexing pipelines with checksums and data versioning (DVC or LakeFS).

## Security Considerations
- Enforce auth on all endpoints; PII scrubbing pre-log.
- Validate uploads, limit sizes/types, sandbox PDF parsing.
- Rate limit per-user; quota for generation tokens.
- Store only necessary chat metadata; encrypt at rest for sensitive docs.

## File Map (selected)
- `Complytics Backend/app.py` — FastAPI app and routers
- `Complytics Backend/routes/compliance.py` — chatbot routes and document flows
- `Complytics Backend/compliance_rag.py` — retrieval, embedding, expert system, generation
- `src/components/team/ComplianceChat.jsx` — React chat UI
- `Complytics Backend/compliance_frameworks/` — source PDFs
- `Complytics Backend/embeddings/` — embeddings and maps
- `Complytics Backend/faiss_indexes/` — FAISS index files
- `Complytics Backend/uploads/`, `downloads/` — user files and generated outputs

---
For questions or contributions, open an issue or submit a PR focusing on retrieval quality, grounding, or evaluation improvements.
