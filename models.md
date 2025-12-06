# Models Documentation

This document provides a comprehensive overview of all models used in the Complytics project, including machine learning models, AI/LLM models, embedding models, and data models.

---

## Table of Contents

1. [Machine Learning Models](#machine-learning-models)
2. [AI/LLM Models](#aillm-models)
3. [Embedding Models](#embedding-models)
4. [Vector Search Models](#vector-search-models)
5. [Data Models (Database Schemas)](#data-models-database-schemas)

---

## Machine Learning Models

### 1. Accessibility Severity Classification Model

**Model Type:** Random Forest Classifier  
**Location:** `Complytics Backend/ml/outputs/model.joblib`  
**Training Script:** `Complytics Backend/ml/train_accessibility_severity.py`  
**Prediction Script:** `Complytics Backend/ml/predict_accessibility_severity.py`

#### Overview

This model automatically classifies WCAG accessibility violations by severity level (Critical, Serious, Moderate, Minor) based on violation metadata. It's used in the UI Testing module to provide consistent severity ratings for accessibility issues.

#### Model Architecture

- **Algorithm:** Random Forest Classifier
- **Number of Trees:** 300
- **Random State:** 42 (for reproducibility)
- **Preprocessing Pipeline:**
  - **Categorical Features:** One-Hot Encoded
    - `rule_id` - WCAG rule identifier
    - `impact` - Impact level (Critical, Serious, Moderate, Minor)
  - **Numeric Features:** Pass-through (no scaling needed for Random Forest)
    - `nodes` - Number of affected DOM nodes
    - `target_text_len` - Length of target element text
  - **Boolean Features:** Pass-through
    - `has_help_url` - Help documentation available?
    - `has_aria` - ARIA attributes present?
    - `is_interactive` - Interactive element?

#### Training Data

- **Dataset:** `Complytics Backend/ml/data/web content accessibility.csv`
- **Total Samples:** 5,472 accessibility violations
- **Train/Test Split:** 80/20 (4,377 training, 1,095 test)
- **Stratification:** Yes (ensures balanced classes in train/test sets)

#### Model Performance

**Overall Accuracy:** 81.52%

**Class-wise Performance:**

| Severity | Precision | Recall | F1-Score | Support |
|----------|-----------|--------|----------|---------|
| Critical | 0.857 | 0.751 | 0.801 | 385 |
| Serious | 0.811 | 0.795 | 0.803 | 342 |
| Moderate | 0.775 | 0.799 | 0.855 | 353 |
| Minor | 0.911 | 0.895 | 0.903 | 357 |

**Macro Averages:**
- Precision: 0.851
- Recall: 0.815
- F1-Score: 0.899

#### How It Works

1. **Feature Extraction:**
   - When a WCAG violation is detected during UI testing, metadata is extracted
   - Features are prepared according to the training schema

2. **Prediction:**
   - The trained model (loaded from `model.joblib`) receives the features
   - Random Forest aggregates predictions from 300 decision trees
   - Majority vote determines the final severity classification

3. **Integration:**
   - Predicted severity is attached to the violation
   - Used for:
     - UI display (severity badges)
     - Scoring calculations (severity-based deductions)
     - AI recommendations (prioritization)

#### Why Random Forest?

- **Handles Mixed Data Types:** Naturally works with categorical, numeric, and boolean features
- **Feature Importance:** Provides interpretability (which features drive severity)
- **Fast Inference:** <5ms per prediction, suitable for real-time UI scoring
- **Robust to Overfitting:** Ensemble method reduces overfitting risk
- **No Feature Scaling Required:** Works well with raw numeric values

#### Model Files

- `model.joblib` - Trained model pipeline (preprocessing + classifier)
- `model_info.json` - Model metadata and performance metrics
- `model_metrics.png` - Visualization of model performance

#### Retraining

To retrain the model with new data:

```bash
python -m Complytics\ Backend.ml.train_accessibility_severity \
  --data "Complytics Backend/ml/data/web content accessibility.csv" \
  --out-dir "Complytics Backend/ml/outputs" \
  --model-type rf \
  --test-size 0.2 \
  --random-state 42
```

---

## AI/LLM Models

### 1. Google Gemini 2.0 Flash

**Model Name:** `gemini-2.0-flash`  
**Provider:** Google Generative AI  
**Location:** `Complytics Backend/compliance_rag.py`  
**Usage:** Compliance chatbot, document analysis, recommendations generation

#### Overview

Gemini 2.0 Flash is used as the primary LLM for the compliance chatbot. It handles natural language understanding, document analysis, compliance framework queries, and generates intelligent responses.

#### Configuration

```python
generation_config = {
    "temperature": 0.1,        # Low temperature for consistent, factual responses
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 3200,  # Maximum response length
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]
```

#### Key Features

- **Multi-API Key Support:** Rotates between multiple API keys for rate limit handling
- **Rate Limiting:** Built-in rate limiting to prevent API quota exhaustion
- **Error Handling:** Automatic fallback to alternative API keys on failure
- **Context-Aware:** Maintains conversation history for coherent responses

#### Use Cases

1. **Compliance Queries:**
   - Answers questions about GDPR, ISO 27001, SOC 2, HIPAA, etc.
   - Provides framework-specific guidance
   - Explains compliance requirements

2. **Document Analysis:**
   - Analyzes uploaded privacy policies and terms & conditions
   - Identifies compliance gaps
   - Generates improvement suggestions

3. **Document Generation:**
   - Creates compliant privacy policies
   - Generates terms & conditions documents
   - Customizes documents based on user requirements

4. **Intent Classification:**
   - Classifies user queries (USE_MAIN_EXPERTS, DOC_ANALYSIS, DOC_GENERATION, etc.)
   - Handles ambiguous queries with clarification requests

#### How It Works

1. **Query Processing:**
   - User query is received
   - Intent is classified using LLM
   - Relevant context is retrieved from FAISS index

2. **Context Retrieval:**
   - Query is converted to embedding
   - Similar document segments are retrieved
   - Top-k most relevant segments are selected

3. **Response Generation:**
   - LLM receives query + retrieved context + conversation history
   - Generates response using RAG (Retrieval-Augmented Generation)
   - Response is formatted and returned to user

4. **Expert System:**
   - Different "experts" (privacy, audit, general compliance) are consulted
   - Expert responses are aggregated for comprehensive answers

---

## Embedding Models

### 1. SentenceTransformer - all-MiniLM-L6-v2

**Model Name:** `all-MiniLM-L6-v2`  
**Provider:** Sentence Transformers (Hugging Face)  
**Location:** `Complytics Backend/compliance_rag.py`  
**Dimension:** 384  
**Usage:** Text embeddings for semantic search

#### Overview

This model converts text (queries and documents) into dense vector representations (embeddings) that capture semantic meaning. These embeddings enable similarity search using FAISS.

#### Model Specifications

- **Architecture:** MiniLM (distilled BERT)
- **Embedding Dimension:** 384
- **Input:** Text strings (max 500 words for performance)
- **Output:** 384-dimensional float32 numpy array
- **Normalization:** L2 normalized for cosine similarity

#### How It Works

1. **Initialization:**
   ```python
   embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
   ```

2. **Text to Embedding:**
   ```python
   embedding = embedding_model.encode(text, convert_to_numpy=True)
   ```

3. **Caching:**
   - In-memory cache (max 1000 entries) for frequently used texts
   - Hash-based lookup for fast retrieval
   - Reduces redundant computations

#### Use Cases

- **Query Embeddings:** Convert user queries to vectors for semantic search
- **Document Embeddings:** Convert compliance framework documents to vectors
- **Similarity Search:** Find relevant document segments using cosine similarity

#### Performance Optimizations

- **Text Truncation:** Long texts (>500 words) are truncated
- **Batch Processing:** Multiple texts can be embedded simultaneously
- **Memory Caching:** Frequently used embeddings are cached
- **Normalized Embeddings:** L2 normalization for efficient cosine similarity

---

## Vector Search Models

### 1. FAISS Index

**Library:** Facebook AI Similarity Search (FAISS)  
**Index Type:** IndexFlatL2 (Euclidean distance) / IndexFlatIP (Inner Product)  
**Location:** `Complytics Backend/faiss_indexes/compliance_index.faiss`  
**Usage:** Fast similarity search for RAG

#### Overview

FAISS (Facebook AI Similarity Search) is used to store document embeddings and perform fast similarity searches. It enables the RAG system to quickly find relevant document segments for user queries.

#### Index Structure

- **Embeddings Storage:** `embeddings/document_embeddings.npy`
- **Document Mapping:** `embeddings/document_map.json`
- **FAISS Index:** `faiss_indexes/compliance_index.faiss`

#### How It Works

1. **Index Creation:**
   - Document segments are converted to embeddings
   - Embeddings are stored in FAISS index
   - Document metadata is stored in mapping file

2. **Query Processing:**
   - User query is converted to embedding
   - FAISS searches for similar embeddings
   - Top-k most similar segments are retrieved

3. **Similarity Calculation:**
   - Cosine similarity (for normalized embeddings)
   - L2 distance (Euclidean distance)
   - Inner product (for non-normalized embeddings)

#### Performance

- **Search Speed:** <10ms for queries on thousands of documents
- **Scalability:** Handles large document collections efficiently
- **Memory Efficient:** Compressed index format

#### Integration with RAG

1. Query → Embedding
2. FAISS Search → Top-k similar segments
3. Segments + Query → LLM (Gemini)
4. LLM generates response using retrieved context

---

## Data Models (Database Schemas)

### 1. User Model

**Location:** `Complytics Backend/schemas/users.py`  
**Collection:** `users`

#### Schema

```python
class UserInDB(BaseModel):
    id: str                    # MongoDB ObjectId (as string)
    email: EmailStr            # User email address
    first_name: str            # First name
    last_name: str             # Last name
    role: UserRole             # it_team, compliance_team, management_team, superadmin
    organization_id: Optional[str]  # Organization ID
    is_active: bool            # Account status
    created_at: datetime       # Creation timestamp
    updated_at: datetime       # Last update timestamp
    created_by: Optional[str]  # Creator user ID
```

#### User Roles

- `it_team` - IT team members
- `compliance_team` - Compliance team members
- `management_team` - Management team members
- `superadmin` - Super administrator

### 2. Organization Model

**Location:** `Complytics Backend/schemas/users.py`  
**Collection:** `organizations`

#### Schema

```python
class OrganizationInDB(BaseModel):
    id: str                    # MongoDB ObjectId (as string)
    name: str                  # Organization name
    domain: str                # Organization domain
    created_at: datetime       # Creation timestamp
    updated_at: datetime       # Last update timestamp
    created_by: Optional[str]  # Creator user ID
```

### 3. Document Model

**Location:** `Complytics Backend/routes/compliance.py`  
**Collection:** `documents`

#### Schema

```python
{
    "filename": str,           # Generated filename
    "original_name": str,      # Original uploaded filename
    "session_id": str,         # Chat session ID
    "user_id": str,            # Uploader user ID
    "upload_date": datetime,   # Upload timestamp
    "file_path": str,          # File storage path
    "file_type": str,          # MIME type
    "status": str,             # "processed"
    "content": str,            # Extracted text content
    "doc_type": str            # privacy_policy, terms_and_conditions, general_documentation
}
```

### 4. UI Testing Results Model

**Location:** `Complytics Backend/routes/ui_testing.py`  
**Collection:** `ui_testing_site_results`

#### Schema

```python
{
    "organization_id": str,    # Organization ID
    "user_id": str,            # User ID who ran the scan
    "url": str,                # Scanned URL
    "mode": str,               # all, accessibility, security
    "result": {
        "summary": {...},      # Scan summary
        "wcag_aggregate": {...}, # WCAG violations aggregate
        "security_aggregate": {...}, # Security findings aggregate
        "page_results": [...],  # Individual page results
        "crawl_result": {...}   # Crawl statistics
    },
    "created_at": int,         # Unix timestamp
    "specific_urls_mode": bool # Whether specific URLs were scanned
}
```

### 5. Compliance Chat History Model

**Location:** `Complytics Backend/routes/compliance.py`  
**Collection:** `chat_history`

#### Schema

```python
{
    "session_id": str,         # Chat session ID
    "user_id": str,            # User ID
    "query": str,              # User query
    "response": str,           # Bot response
    "timestamp": datetime,     # Message timestamp
    "experts_consulted": List[str], # Expert types used
    "response_time": float,    # Response generation time (seconds)
    "is_compliance": bool      # Whether query was compliance-related
}
```

---

## Model Integration Flow

### Complete Workflow

1. **User Query → Intent Classification (Gemini)**
   - Determines query type and required framework

2. **Query → Embedding (SentenceTransformer)**
   - Converts query to 384-dimensional vector

3. **Embedding → FAISS Search**
   - Finds similar document segments

4. **Retrieved Context + Query → Gemini**
   - Generates response using RAG

5. **UI Testing Violations → ML Model (Random Forest)**
   - Classifies violation severity

6. **Results → Database (MongoDB)**
   - Stores all results and history

---

## Model Dependencies

### Python Packages

- `scikit-learn` - Random Forest, preprocessing
- `sentence-transformers` - Embedding model
- `faiss-cpu` / `faiss-gpu` - Vector search
- `google-generativeai` - Gemini API
- `joblib` - Model serialization
- `pandas` - Data processing
- `numpy` - Numerical operations

### Model Files

- `ml/outputs/model.joblib` - Trained Random Forest model
- `ml/outputs/model_info.json` - Model metadata
- `embeddings/document_embeddings.npy` - Document embeddings
- `faiss_indexes/compliance_index.faiss` - FAISS index
- `embeddings/document_map.json` - Document metadata mapping

---

## Model Maintenance

### Retraining ML Model

When new accessibility violation data is available:

1. Update `ml/data/web content accessibility.csv`
2. Run training script
3. Evaluate new model performance
4. Replace `model.joblib` if performance improves

### Updating Embeddings

When compliance framework documents are updated:

1. Process new documents
2. Generate embeddings
3. Rebuild FAISS index
4. Update document mapping

### Monitoring

- Track model performance metrics
- Monitor API usage and costs
- Log prediction confidence scores
- Track user feedback on predictions

---

## Conclusion

The Complytics project uses a combination of:

- **Machine Learning** for automated severity classification
- **Large Language Models** for intelligent compliance assistance
- **Embedding Models** for semantic search
- **Vector Search** for fast retrieval
- **Data Models** for structured storage

Together, these models provide a comprehensive compliance management system with AI-powered insights and automation.

