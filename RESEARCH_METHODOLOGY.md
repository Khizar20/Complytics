# Research Methodology: Complytics RAG Chatbot

## 1. Objective
Design and evaluate a Retrieval-Augmented Generation (RAG) system specialized for regulatory compliance assistance. The system should (a) retrieve grounded evidence from authoritative frameworks, (b) produce concise, accurate responses, (c) support document-centric workflows (upload, analysis, generation), and (d) learn from user feedback to improve routing and answer quality.

## 2. System Overview
- Backend: FastAPI service (see `Complytics Backend/app.py`) exposing `/api/compliance/*` routes (`routes/compliance.py`).
- Core RAG: `compliance_rag.py` implements retrieval, embeddings, FAISS indexing, expert routing, generation, caching, and conversation memory.
- Frontend: React UI (`src/components/team/ComplianceChat.jsx`) supporting chat, uploads, analysis, and download flows.
- Storage: MongoDB for chat logs, feedback, document records; local files for embeddings (`embeddings/`), indices (`faiss_indexes/`), and corpora (`compliance_frameworks/`).

## 3. Data and Knowledge Sources
- Primary corpus: curated PDFs in `Complytics Backend/compliance_frameworks/` (e.g., GDPR, ISO 27001/27017/27035, PCI-DSS v4.0.1, SOC 2, NIST, HIPAA, SOX, COBIT, CIS Controls). Documents are segmented and embedded.
- User-provided documents: PDFs/DOCX uploaded via `/api/compliance/upload-document`, parsed and optionally analyzed or used to generate improved compliant drafts.

## 4. Retrieval Pipeline
- Segmentation: Framework PDFs are chunked into semantically coherent segments to balance recall and context length.
- Embeddings: Sentence-level dense embeddings (via `sentence-transformers`) are computed and persisted to `embeddings/` (e.g., `document_embeddings.npy`, `document_map.json`).
- Indexing: FAISS index built and stored under `faiss_indexes/` (e.g., `compliance_index.faiss`) and loaded at runtime by `process_documents()`.
- Query encoding: `get_embedding_optimized(query)` encodes queries. Top-k nearest segments are retrieved via FAISS and concatenated into `retrieved_context`.

## 5. Generation and Expert Routing
- Compliance classification: `is_compliance_related_optimized(query, conversation_context)` implements a fast-path filter for non-compliance queries, producing direct responses when applicable.
- Expert selection: `select_relevant_experts_optimized(query)` routes to a subset of domain experts (privacy, audit, security, financial, healthcare, international, operational, industry_specific).
- Expert responses: Each expert function produces a grounded answer conditioned on `query`, `retrieved_context`, and conversation context. Responses are cached via `cached_expert_response` keyed by content hashes.
- Aggregation: `aggregate_expert_outputs(expert_responses, query, context)` fuses multi-expert outputs into a single answer with prioritization rules.
- LLM calls and rate limiting: `rate_limited_generate_content_optimized` enforces API limits, reduced retries, and token budgets; prompt- and temperature-based hashes enable response caching.

## 6. Conversation Memory and Personalization
- Short-term memory: `ConversationHistory` stores recent exchanges per `session_id` to provide dialogue context and continuity.
- Context usage: Memory is consulted for disambiguation, document intent detection, and to avoid repetition. Long-term memory is not persisted as vectors in the current implementation.

## 7. Document Workflows
- Upload: `/api/compliance/upload-document` stores files to `uploads/` and parses content.
- Analyze: `/api/compliance/analyze-privacy-policy` compares uploaded content against a target framework using the same retrieval engine.
- Generate: `/api/compliance/generate-privacy-policy` and `/generate-terms` produce compliant drafts; generated files are served by `/api/compliance/download/{filename}`.

## 8. Feedback Loop
- Explicit feedback: `/api/compliance/feedback` collects per-message thumbs up/down and persists records (`database.db.feedback`).
- Learning: `learn_from_user_interaction(query, was_helpful, actual_classification)` updates in-memory signals used by classification and routing heuristics.
- Metrics: `/api/compliance/classification-accuracy` summarizes counts and recent accuracy (last N samples) for monitoring.

## 9. Experimental Setup
- Environments: Backend served by Uvicorn (FastAPI) with CORS for the Vite React app. MongoDB required. Environment variables managed via `config.py` and `.env`.
- Corpora: Use provided PDFs under `compliance_frameworks/`. Ensure embeddings and FAISS indexes are built by calling chat endpoints or explicit preprocessing (via `process_documents()`).
- Datasets for sanity-check QA: `testingData.json` contains compliance-focused Q/A for spot checks.

## 10. Evaluation Methodology
We evaluate from two perspectives: text quality/semantic alignment and hallucination risk, plus targeted unit tests for the expert router and classifier.

10.1 Text Quality and Hallucination
- Metrics
  - BERTScore F1 (semantic similarity): `analyze_results.py` computes BERTScore(value in [0,1]).
  - Hallucination proxy (1 − TF-IDF cosine similarity): higher is worse.
- Protocol
  - Two regimes: “with reasoning” vs “without reasoning” CSVs (see repo root: `with reasoning.csv`, `without reasoning.csv`).
  - References: `Answer by RAG` columns; Comparisons: `Answer by Gemini`, `Answer by Chatgpt`, `Answer By Deepseek`.
  - The script iterates rows, computes BERTScore and hallucination proxy against the RAG answer, aggregates means by model, and saves plots (`model_comparison_scores.png`).
- Visualization
  - `plot_scores.py` generates four bar plots saved to PNG: BERT/hallucination with and without reasoning.

10.2 Functional Unit Tests (Routing/Classification)
- `test_enhanced_experts.py` & `test_enhanced_experts_simple.py`
  - Expert selection coverage across domains; pass if ≥ threshold (e.g., >70% expected-domain presence and >80% coverage).
- `test_expert_selection.py`
  - Prints selected experts and detected query types for diverse queries; used for manual inspection of router behavior.

10.3 User-facing Metrics
- API-level latency and response time recorded in `/api/compliance/chat` responses.
- Dashboard analytics (`/api/compliance/analytics`): total queries, average response time, most common topics, and success rate derived from “experts consulted.”

## 11. Implementation Details
- Caching: In-memory/file-backed `QUERY_CACHE` keyed by MD5 hashes of prompts, contexts, and temperatures. Periodic persistence reduces I/O overhead.
- Rate limiting: Decorators (`@limits`, `@sleep_and_retry`) wrap generation calls to respect model quotas.
- Robustness: Defensive checks ensure segments, embeddings, and FAISS index exist, returning friendly errors otherwise.
- Security: Auth required for endpoints; uploads restricted to PDF/DOCX; file I/O guarded; download endpoints verify file presence.

## 12. Reproducibility Notes
- Pin Python dependencies from `Complytics Backend/requirements.txt` and Node dependencies from `package.json`.
- Ensure `compliance_frameworks/` and `embeddings/` directories are consistent across runs; re-generate embeddings and FAISS indices when updating corpora.
- Keep `.env` stable for MongoDB connection and secrets.

## 13. Threats to Validity
- Reference bias: Using RAG answers as the reference for BERTScore may favor similarity over factuality or completeness.
- Hallucination proxy: TF-IDF cosine is a proxy; does not guarantee factual grounding.
- Domain coverage: Performance depends on the breadth/quality of loaded frameworks and segmentation heuristics.
- Heuristic routing: Expert selection relies on optimized heuristics; may misroute nuanced queries.

## 14. Ethical/Compliance Considerations
- The assistant provides guidance but not legal advice. Results should be reviewed by qualified compliance officers.
- Sensitive documents should be handled with encryption at rest and access control; consider redaction and on-prem deployment for high-sensitivity contexts.

## 15. Results (Representative)
- `plot_scores.py` suggests higher BERTScore and lower hallucination in “with reasoning” vs “without reasoning,” and shows RAG’s grounding benefit as a baseline.
- Unit tests indicate broad but not perfect expert routing coverage, guiding targeted improvements.

## 16. Ablation/Variant Ideas (Optional for Paper)
- Retrieval k and chunk size sweep; analyze BERTScore/hallucination trade-offs.
- Hybrid retrieval (BM25 + dense) with cross-encoder reranking vs. dense-only FAISS.
- Expert router alternatives: keyword-heuristics vs. small classifier fine-tuned on user logs.

## 17. Future Work: A New Research Problem
Title: Grounded MoE RAG with Certified Evidence Attribution for Compliance Assistance

Problem Definition
- Develop a Mixture-of-Experts RAG framework that (1) learns a data-driven router for compliance subdomains, (2) enforces evidence attribution at the claim level, and (3) provides calibrated uncertainty for each answer segment.

Research Questions
- RQ1: Can a learned router (multi-label classifier or differentiable MoE) outperform heuristic expert selection on coverage and accuracy without added latency?
- RQ2: Does integrating a cross-encoder verifier with explicit evidence IDs reduce hallucinations while preserving informativeness?
- RQ3: Can we calibrate uncertainty (conformal prediction or evidential deep learning) to abstain or trigger retrieval retries on low-confidence claims?

Methodology Sketch
- Router: Train a lightweight classifier on labeled chat logs + feedback (`/feedback`) to predict expert labels and retrieval depth.
- Evidence Attribution: Require each sentence to cite segment IDs; verify with NLI-based entailment between answer sentences and retrieved spans; reject or revise non-entailed claims.
- Uncertainty: Compute per-claim uncertainty from verifier logits and retrieval agreement; add abstention or re-retrieval policy.
- Evaluation: Expand dataset with human labels (entailed/contradicted/uncertain); measure faithfulness (NLI), usefulness (BERTScore vs. human reference), and calibrated coverage-risk curves.

Anticipated Contributions
- A principled, auditable RAG pipeline with claim-level citations and uncertainty-aware responses for high-stakes compliance.
- Empirical evidence that MoE routing + verification improves accuracy and reduces hallucinations under real-world workloads.

Artifacts to Release
- Router training set derived from anonymized chat logs + feedback.
- Benchmarks and scripts to reproduce evidence-attribution metrics and calibration plots.

---
This methodology is grounded in the current implementation and evaluation scripts (`analyze_results.py`, `plot_scores.py`, `test_*.py`) and can be directly adapted into the Methods and Future Work sections of a research paper.
