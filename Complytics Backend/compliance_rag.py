import os
import json
import logging
import time
import faiss
import google.generativeai as genai
import requests
import pdfplumber
import numpy as np
import re
from typing import List, Dict, Any, Tuple, Optional, AsyncIterator
from sentence_transformers import SentenceTransformer
from ratelimit import limits, sleep_and_retry
import concurrent.futures
from datetime import datetime
import hashlib
from functools import lru_cache
import asyncio
from sklearn.metrics.pairwise import cosine_similarity
import docx
import PyPDF2
from pathlib import Path
from docx import Document
import random
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
# GOOGLE_API_KEY = "AIzaSyAF5hhERrZXTudmLVJkjmTgMxPH2h5PWtI"
GOOGLE_API_KEY="AIzaSyBESSLYw4V10xeLYtyIuez9IxXVS41mC_8"
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize the embedding model
logger.info("Initializing embedding model...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Directory structure for embeddings and indexes
EMBEDDING_DIR = "embeddings"
INDEX_DIR = "faiss_indexes"
CACHE_DIR = "compliance_cache"
PDF_FOLDER = "compliance_frameworks"

EMBEDDING_CACHE_FILE = os.path.join(EMBEDDING_DIR, "document_embeddings.npy")
DOCUMENT_MAP_FILE = os.path.join(EMBEDDING_DIR, "document_map.json")
FAISS_INDEX_FILE = os.path.join(INDEX_DIR, "compliance_index.faiss")
QUERY_CACHE_FILE = os.path.join(CACHE_DIR, "query_cache.json")

# Create directories if they don't exist
for directory in [EMBEDDING_DIR, INDEX_DIR, CACHE_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Initialize query cache
QUERY_CACHE = {}
if os.path.exists(QUERY_CACHE_FILE):
    try:
        with open(QUERY_CACHE_FILE, 'r') as f:
            QUERY_CACHE = json.load(f)
        logger.info(f"Loaded {len(QUERY_CACHE)} cached queries")
    except Exception as e:
        logger.error(f"Error loading query cache: {e}")

def save_query_cache():
    """Save query cache to disk"""
    try:
        with open(QUERY_CACHE_FILE, 'w') as f:
            json.dump(QUERY_CACHE, f)
        logger.info(f"Saved {len(QUERY_CACHE)} queries to cache")
    except Exception as e:
        logger.error(f"Error saving query cache: {e}")

# Set up the Gemini model
generation_config = {
    "temperature": 0.1,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 3200,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config,
    safety_settings=safety_settings
)

# Optimized rate limiting configuration
CALLS_PER_MINUTE = 40  # Increased from 20
DELAY_BETWEEN_CALLS = 1.5  # Reduced from 3 seconds
last_call_time = 0

# Define timing decorator first
def timing_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"\n{func.__name__} execution time: {execution_time:.2f} seconds")
        return result
    return wrapper

def wait_for_rate_limit_optimized():
    """Optimized rate limiting with shorter delays."""
    global last_call_time
    current_time = time.time()
    time_since_last_call = current_time - last_call_time
    if time_since_last_call < DELAY_BETWEEN_CALLS:
        sleep_time = DELAY_BETWEEN_CALLS - time_since_last_call
        time.sleep(sleep_time)
    last_call_time = time.time()

def _ollama_params() -> tuple:
    base = (os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434/v1").rstrip("/")
    model = os.getenv("OLLAMA_MODEL") or "llama3.1"
    return base, model

def _generate_via_ollama(prompt: str, temperature: float = 0.1, max_tokens: int = 3200) -> str:
    try:
        base, model_name = _ollama_params()
        # Clamp tokens for faster local generation and allow env override
        max_tokens_ollama = int(os.getenv("OLLAMA_MAX_TOKENS", "800"))
        max_tokens_ollama = max(1, min(max_tokens_ollama, max_tokens))
        req_timeout = int(os.getenv("OLLAMA_TIMEOUT", "120"))
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(max(0.0, min(1.0, temperature))),
            "max_tokens": max_tokens_ollama,
        }
        r = requests.post(f"{base}/chat/completions", json=payload, timeout=req_timeout)
        r.raise_for_status()
        data = r.json()
        text = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        return text
    except Exception as e:
        logger.info(f"Ollama generation failed: {e}")
        return ""

@sleep_and_retry
@limits(calls=CALLS_PER_MINUTE, period=60)
@timing_decorator
def rate_limited_generate_content_optimized(prompt: str, temperature: float = 0.1, max_tokens: int = 3200) -> str:
    """Optimized rate-limited content generation with reduced tokens for speed."""
    # Check cache first using hash of prompt + temperature
    prompt_hash = hash_text(f"{prompt}:{temperature}:{max_tokens}")
    cache_key = f"gemini_opt:{prompt_hash}"
    
    if cache_key in QUERY_CACHE:
        logger.info("Cache hit for optimized Gemini API call")
        return QUERY_CACHE[cache_key]
    
    wait_for_rate_limit_optimized()
    
    # Reduced retry attempts for speed
    max_retries = 3
    base_delay = 1.5
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens  # Limit response length for speed
                }
            )
            result = response.text.strip()
            
            # Cache the result
            QUERY_CACHE[cache_key] = result
            
            # Less frequent cache saves
            if len(QUERY_CACHE) % 20 == 0:
                save_query_cache()
                
            return result
        except Exception as e:
            if "429" in str(e):
                retry_delay = base_delay * (1.5 ** attempt)  # Reduced exponential backoff
                logger.info(f"Rate limit hit, retrying in {retry_delay:.1f}s (attempt {attempt+1}/{max_retries})")
                time.sleep(retry_delay)
                if attempt == max_retries - 1:
                    break
            else:
                logger.error(f"API error: {e}")
                break
    # Gemini unavailable -> fallback to Ollama
    ollama_text = _generate_via_ollama(prompt, temperature=temperature, max_tokens=max_tokens)
    if ollama_text:
        QUERY_CACHE[cache_key] = ollama_text
        return ollama_text
    return "Response temporarily unavailable. Please try again."

@timing_decorator
def get_embedding(text: str) -> np.ndarray:
    """Get embeddings using sentence-transformers model."""
    if len(text.split()) > 8000:
        text = " ".join(text.split()[:8000])
    try:
        embeddings = embedding_model.encode([text], convert_to_numpy=True)
        return embeddings[0]
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None

def save_embeddings(embeddings: List[np.ndarray], document_map: List[Dict[str, Any]]) -> None:
    """Save embeddings and document mapping to disk."""
    try:
        embeddings_array = np.array(embeddings)
        np.save(EMBEDDING_CACHE_FILE, embeddings_array)
        with open(DOCUMENT_MAP_FILE, 'w') as f:
            json.dump(document_map, f, indent=2)
        logger.info(f"Saved {len(embeddings)} embeddings to {EMBEDDING_CACHE_FILE}")
    except Exception as e:
        logger.error(f"Error saving embeddings: {e}")

def load_embeddings() -> Tuple[Optional[np.ndarray], Optional[List[Dict[str, Any]]]]:
    """Load embeddings and document mapping from disk."""
    try:
        if os.path.exists(EMBEDDING_CACHE_FILE) and os.path.exists(DOCUMENT_MAP_FILE):
            embeddings = np.load(EMBEDDING_CACHE_FILE)
            with open(DOCUMENT_MAP_FILE, 'r') as f:
                document_map = json.load(f)
            logger.info(f"Loaded {len(embeddings)} embeddings from cache")
            return embeddings, document_map
    except Exception as e:
        logger.error(f"Error loading embeddings: {e}")
    return None, None

def build_and_save_faiss_index(embeddings: np.ndarray) -> Optional[faiss.Index]:
    """Build and save optimized FAISS index for fast retrieval."""
    try:
        dimension = embeddings.shape[1]
        n_vectors = embeddings.shape[0]
        
        logger.info(f"Building optimized FAISS index for {n_vectors} vectors, dimension {dimension}")
        
        # For small datasets (< 10k), use flat index for speed
        if n_vectors < 10000:
            index = faiss.IndexFlatL2(dimension)
            index.add(embeddings)
            logger.info("Using IndexFlatL2 for optimal small dataset performance")
        else:
            # For larger datasets, use optimized IVF
            n_clusters = min(int(np.sqrt(n_vectors) * 2), n_vectors // 20)
            n_clusters = max(n_clusters, 4)
            
            # Create optimized quantizer
            quantizer = faiss.IndexFlatL2(dimension)
            index = faiss.IndexIVFFlat(quantizer, dimension, n_clusters)
            
            # Optimize search parameters for speed
            index.nprobe = max(1, n_clusters // 8)  # Faster search with slight accuracy trade-off
            
            # Train and add vectors
            logger.info(f"Training IVF index with {n_clusters} clusters, nprobe={index.nprobe}")
            index.train(embeddings)
            index.add(embeddings)
        
        # Enable multi-threading for search
        faiss.omp_set_num_threads(4)
        
        faiss.write_index(index, FAISS_INDEX_FILE)
        logger.info(f"Saved optimized FAISS index with {index.ntotal} vectors")
        return index
        
    except Exception as e:
        logger.error(f"Error building optimized FAISS index: {e}")
        return None

def load_faiss_index() -> Optional[faiss.Index]:
    """Load FAISS index from disk."""
    try:
        if os.path.exists(FAISS_INDEX_FILE):
            index = faiss.read_index(FAISS_INDEX_FILE)
            logger.info(f"Loaded FAISS index with {index.ntotal} vectors")
            return index
    except Exception as e:
        logger.error(f"Error loading FAISS index: {e}")
    return None

def process_documents(new_document_path: Optional[str] = None) -> Tuple[List[str], np.ndarray, Any]:
    """Process documents and generate embeddings with optimized segmentation and caching.
    If new_document_path is provided, only process that document and merge with existing embeddings."""
    
    # Ensure required directories exist
    for directory in [EMBEDDING_DIR, INDEX_DIR, CACHE_DIR, PDF_FOLDER]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")
    
    logger.info("Checking for existing embeddings...")
    cached_embeddings, cached_doc_map = load_embeddings()
    
    all_segments = []
    all_embeddings = []
    document_map = []
    
    # If we have cached embeddings, use them as a base
    if cached_embeddings is not None and cached_doc_map is not None:
        logger.info(f"Loaded {len(cached_embeddings)} embeddings from cache")
        all_segments = [doc["text"] for doc in cached_doc_map]
        all_embeddings = list(cached_embeddings)
        document_map = cached_doc_map.copy()
        logger.info("Found existing embeddings!")
    
    # If a new document path is provided, only process that document
    if new_document_path:
        logger.info(f"Processing new document: {new_document_path}")
        try:
            # Extract text from the document
            if new_document_path.lower().endswith('.pdf'):
                text = extract_text_from_pdf(new_document_path)
            elif new_document_path.lower().endswith('.docx'):
                text = extract_text_from_docx(new_document_path)
            else:
                logger.error(f"Unsupported file format: {new_document_path}")
                return None, None, None

            if not text:
                logger.error(f"No text content could be extracted from {new_document_path}")
                return None, None, None

            # Process the new document
            segments = process_text_into_segments(text)
            logger.info(f"Created {len(segments)} segments from {new_document_path}")

            # Generate embeddings for new segments
            batch_size = 32
            for i in range(0, len(segments), batch_size):
                batch = segments[i:i+batch_size]
                try:
                    batch_embeddings = embedding_model.encode(batch, convert_to_numpy=True)
                    all_embeddings.extend(batch_embeddings)
                    all_segments.extend(batch)
                except Exception as e:
                    logger.error(f"Error generating batch embeddings: {e}")
                    continue
                logger.info(f"Processed batch {i//batch_size + 1}/{(len(segments)-1)//batch_size + 1}")

            # Add new document to document map
            document_map.append({
                "filename": os.path.basename(new_document_path),
                "text": text,
                "segments": segments,
                "position": len(all_segments) - len(segments)
            })

        except Exception as e:
            logger.error(f"Error processing new document: {e}")
            return None, None, None
    else:
        # Check if we already have embeddings and they cover all current documents
        frameworks_dir = Path(__file__).parent / "compliance_frameworks"
        if not frameworks_dir.exists():
            logger.error(f"compliance_frameworks directory not found at: {frameworks_dir.absolute()}")
            return None, None, None

        # Get list of all PDF and DOCX files
        framework_files = list(frameworks_dir.glob("*.pdf")) + list(frameworks_dir.glob("*.docx"))
        current_filenames = {file_path.name for file_path in framework_files}
        
        # If we have cached embeddings, check if they cover all current files
        if cached_embeddings is not None and cached_doc_map is not None:
            cached_filenames = {doc["filename"] for doc in cached_doc_map}
            
            # If all current files are already cached, return cached data
            if current_filenames.issubset(cached_filenames):
                logger.info(f"All {len(current_filenames)} documents are already processed. Using cached data.")
                # Load and return the existing FAISS index
                index = load_faiss_index()
                if index is not None:
                    logger.info(f"Loaded FAISS index with {index.ntotal} vectors")
                    return all_segments, cached_embeddings, index
                else:
                    logger.info("FAISS index not found, rebuilding...")
                    index = build_and_save_faiss_index(cached_embeddings)
                    return all_segments, cached_embeddings, index
            else:
                # Some files are new, process only the new ones
                new_files = current_filenames - cached_filenames
                logger.info(f"Found {len(new_files)} new documents to process: {new_files}")
                
                # Process only new files
                for file_path in framework_files:
                    if file_path.name in new_files:
                        try:
                            logger.info(f"Processing {file_path.name}")
                            if file_path.suffix.lower() == '.pdf':
                                text = extract_text_from_pdf(str(file_path))
                            else:  # .docx
                                text = extract_text_from_docx(str(file_path))

                            if not text:
                                logger.warning(f"No text content extracted from {file_path.name}")
                                continue

                            segments = process_text_into_segments(text)
                            logger.info(f"Created {len(segments)} segments from {file_path.name}")

                            # Generate embeddings in batches
                            batch_size = 32
                            for i in range(0, len(segments), batch_size):
                                batch = segments[i:i+batch_size]
                                try:
                                    batch_embeddings = embedding_model.encode(batch, convert_to_numpy=True)
                                    all_embeddings.extend(batch_embeddings)
                                    all_segments.extend(batch)
                                except Exception as e:
                                    logger.error(f"Error generating batch embeddings: {e}")
                                    continue
                                logger.info(f"Processed batch {i//batch_size + 1}/{(len(segments)-1)//batch_size + 1}")

                            # Add to document map
                            document_map.append({
                                "filename": file_path.name,
                                "text": text,
                                "segments": segments,
                                "position": len(all_segments) - len(segments)
                            })

                        except Exception as e:
                            logger.error(f"Error processing {file_path.name}: {e}")
                            continue
        else:
            # No cached embeddings, process all documents
            logger.info("No cached embeddings found. Processing all documents...")
            for file_path in framework_files:
                try:
                    logger.info(f"Processing {file_path.name}")
                    if file_path.suffix.lower() == '.pdf':
                        text = extract_text_from_pdf(str(file_path))
                    else:  # .docx
                        text = extract_text_from_docx(str(file_path))

                    if not text:
                        logger.warning(f"No text content extracted from {file_path.name}")
                        continue

                    segments = process_text_into_segments(text)
                    logger.info(f"Created {len(segments)} segments from {file_path.name}")

                    # Generate embeddings in batches
                    batch_size = 32
                    for i in range(0, len(segments), batch_size):
                        batch = segments[i:i+batch_size]
                        try:
                            batch_embeddings = embedding_model.encode(batch, convert_to_numpy=True)
                            all_embeddings.extend(batch_embeddings)
                            all_segments.extend(batch)
                        except Exception as e:
                            logger.error(f"Error generating batch embeddings: {e}")
                            continue
                        logger.info(f"Processed batch {i//batch_size + 1}/{(len(segments)-1)//batch_size + 1}")

                    # Add to document map
                    document_map.append({
                        "filename": file_path.name,
                        "text": text,
                        "segments": segments,
                        "position": len(all_segments) - len(segments)
                    })

                except Exception as e:
                    logger.error(f"Error processing {file_path.name}: {e}")
                    continue

    if not all_segments:
        logger.info("No segments were created. Please check your documents.")
        return None, None, None
    
    # Only save and rebuild index if we processed new documents
    if new_document_path or (cached_embeddings is None) or len(document_map) > len(cached_doc_map or []):
        logger.info(f"Updating embeddings and index with {len(all_embeddings)} total embeddings")
        embeddings_array = np.array(all_embeddings)
        
        # Save the updated embeddings and document map
        save_embeddings(all_embeddings, document_map)
        
        # Build and save the new index
        index = build_and_save_faiss_index(embeddings_array)
        
        logger.info(f"Returning {len(all_segments)} total segments")
        return all_segments, embeddings_array, index
    else:
        # Return cached data with existing index
        index = load_faiss_index()
        if index is None:
            logger.info("Rebuilding FAISS index from cached embeddings")
            embeddings_array = np.array(all_embeddings)
            index = build_and_save_faiss_index(embeddings_array)
        
        return all_segments, np.array(all_embeddings), index

def detect_concise_request(query: str) -> bool:
    """Detect if user is asking for a concise/brief response."""
    concise_indicators = [
        "concisely", "briefly", "short", "quick", "summarize", "summary",
        "in brief", "quick answer", "short answer", "bullet points",
        "key points", "main points", "overview", "tldr", "tl;dr"
    ]
    query_lower = query.lower()
    return any(indicator in query_lower for indicator in concise_indicators)

def get_concise_max_tokens(query: str) -> int:
    """Return appropriate max_tokens based on whether user wants concise response."""
    if detect_concise_request(query):
        return 512  # Much shorter for concise requests
    return 2500  # Full length for detailed requests

@timing_decorator
def expert_security_controls(query: str, context: str, conversation_context: str = "") -> str:
    """Expert analysis for security controls."""
    is_concise = detect_concise_request(query)
    max_tokens = get_concise_max_tokens(query)
    
    if is_concise:
        prompt = (
            "Provide a CONCISE, bullet-point response for this security/compliance query.\n\n"
            f"Query: {query}\n"
            f"Context: {context[:500]}\n\n"
            "Format as:\n"
            "**Key Steps:**\n"
            "• Point 1\n"
            "• Point 2\n"
            "• Point 3\n\n"
            "Keep it under 150 words total. Focus on actionable steps only."
        )
    else:
        prompt = (
            "You are a cybersecurity and information security expert specializing in enterprise security controls and compliance frameworks.\n\n"
            f"Previous conversation context:\n{conversation_context}\n\n"
            f"Current Query: {query}\n"
            f"Relevant Context from Documents: {context}\n\n"
            "Provide a comprehensive analysis focusing on:\n"
            "1. **Security Controls & Requirements**: Specific controls from NIST, ISO 27001, CIS, etc.\n"
            "2. **Implementation Guidelines**: Step-by-step technical implementation\n"
            "3. **Risk Assessment**: Identify threats, vulnerabilities, and risk levels\n"
            "4. **Monitoring & Validation**: Methods to verify control effectiveness\n"
            "5. **Best Practices**: Industry-proven security measures\n"
            "6. **Compliance Mapping**: How controls map to regulatory requirements\n\n"
            "Structure your response with clear headings and actionable recommendations.\n"
            "Use technical precision while remaining practical for implementation.\n\n"
            "Once you write an answer iterate over it to see all points are covered before showing it to user\n\n"
            "Response:"
        )
    return rate_limited_generate_content_optimized(prompt, max_tokens=max_tokens)

@timing_decorator
def expert_privacy_regulations(query: str, context: str, conversation_context: str = "") -> str:
    """Expert analysis for privacy regulations."""
    prompt = (
        "You are a data privacy and protection expert with deep knowledge of global privacy regulations and data governance.\n\n"
        f"Previous conversation context:\n{conversation_context}\n\n"
        f"Current Query: {query}\n"
        f"Relevant Context from Documents: {context}\n\n"
        "Provide a comprehensive analysis focusing on:\n"
        "1. **Regulatory Requirements**: Specific obligations under GDPR, CCPA, PIPEDA, etc.\n"
        "2. **Data Subject Rights**: Individual rights and how to implement them\n"
        "3. **Legal Basis & Consent**: Lawful processing and consent mechanisms\n"
        "4. **Data Protection Measures**: Technical and organizational safeguards\n"
        "5. **Cross-Border Transfers**: International data transfer requirements\n"
        "6. **Breach Response**: Notification requirements and procedures\n"
        "7. **Documentation**: Required policies, records, and assessments\n\n"
        "Include specific regulatory citations and practical implementation guidance.\n"
        "Address both legal compliance and operational requirements.\n\n"
        "Response:"
    )
    return rate_limited_generate_content_optimized(prompt)

@timing_decorator
def expert_audit_compliance(query: str, context: str, conversation_context: str = "") -> str:
    """Expert analysis for audit compliance."""
    prompt = (
        "You are an audit and compliance expert with expertise in enterprise risk management and regulatory compliance frameworks.\n\n"
        f"Previous conversation context:\n{conversation_context}\n\n"
        f"Current Query: {query}\n"
        f"Relevant Context from Documents: {context}\n\n"
        "Provide a comprehensive analysis focusing on:\n"
        "1. **Audit Requirements**: Specific audit standards and procedures\n"
        "2. **Evidence Collection**: Documentation and artifacts needed\n"
        "3. **Compliance Verification**: Methods to assess and validate compliance\n"
        "4. **Risk Assessment Framework**: Identify, analyze, and prioritize risks\n"
        "5. **Control Testing**: Procedures to test control effectiveness\n"
        "6. **Remediation Planning**: Steps to address findings and gaps\n"
        "7. **Continuous Monitoring**: Ongoing compliance assurance processes\n\n"
        "Reference relevant frameworks (ISO 27001, SOC 2, NIST, COBIT) and provide\n"
        "specific audit procedures and compliance checklists where applicable.\n\n"
        "Think step by step before answering\n\n"
        "Response:"
    )
    return rate_limited_generate_content_optimized(prompt)

@timing_decorator
def expert_financial_compliance(query: str, context: str, conversation_context: str = "") -> str:
    """Expert analysis for financial compliance and regulations."""
    prompt = (
        "As a financial compliance expert, analyze the following query:\n\n"
        f"{conversation_context}"
        f"Query: {query}\n"
        f"Context: {context}\n"
        "Focus on:\n"
        "1. Financial regulations (PCI DSS, SOX, Basel III, etc.)\n"
        "2. Anti-money laundering (AML) and Know Your Customer (KYC)\n"
        "3. Payment card industry standards\n"
        "4. Banking and financial services compliance\n"
        "5. Financial reporting and disclosure requirements\n"
        "6. Risk management frameworks (COSO, Basel)\n"
        "Chain-of-Thought Analysis:"
    )
    return rate_limited_generate_content_optimized(prompt)

@timing_decorator
def expert_healthcare_compliance(query: str, context: str, conversation_context: str = "") -> str:
    """Expert analysis for healthcare compliance and HIPAA."""
    is_concise = detect_concise_request(query)
    max_tokens = get_concise_max_tokens(query)
    
    if is_concise:
        prompt = (
            "Provide a CONCISE, bullet-point response for HIPAA/healthcare compliance.\n\n"
            f"Query: {query}\n"
            f"Context: {context[:500]}\n\n"
            "Format as:\n"
            "**HIPAA Compliance Steps:**\n"
            "• Step 1\n"
            "• Step 2\n"
            "• Step 3\n\n"
            "Keep it under 150 words total. Focus on actionable steps only."
        )
    else:
        prompt = (
            "As a healthcare compliance expert, analyze the following query:\n\n"
            f"{conversation_context}"
            f"Query: {query}\n"
            f"Context: {context}\n\n"
            "Focus on:\n"
            "1. HIPAA Privacy and Security Rules\n"
            "2. Healthcare data protection and PHI handling\n"
            "3. Medical device regulations (FDA, CE marking)\n"
            "4. Clinical trial compliance (GCP, ICH guidelines)\n"
            "5. Healthcare IT security requirements\n"
            "6. Patient consent and data rights\n"
            "Chain-of-Thought Analysis:"
        )
    return rate_limited_generate_content_optimized(prompt, max_tokens=max_tokens)

@timing_decorator
def expert_international_compliance(query: str, context: str, conversation_context: str = "") -> str:
    """Expert analysis for international and cross-border compliance."""
    prompt = (
        "As an international compliance expert, analyze the following query:\n\n"
        f"{conversation_context}"
        f"Query: {query}\n"
        f"Context: {context}\n\n"
        "Focus on:\n"
        "1. Cross-border data transfer requirements\n"
        "2. International privacy laws (GDPR, LGPD, PIPEDA, etc.)\n"
        "3. Export control and trade compliance\n"
        "4. Multi-jurisdictional regulatory requirements\n"
        "5. Data localization and sovereignty issues\n"
        "6. International standards harmonization\n"
        "Chain-of-Thought Analysis:"
    )
    return rate_limited_generate_content_optimized(prompt)

@timing_decorator
def expert_operational_compliance(query: str, context: str, conversation_context: str = "") -> str:
    """Expert analysis for operational compliance and business processes."""
    prompt = (
        "As an operational compliance expert, analyze the following query:\n\n"
        f"{conversation_context}"
        f"Query: {query}\n"
        f"Context: {context}\n\n"
        "Focus on:\n"
        "1. Business process compliance and controls\n"
        "2. Vendor and third-party risk management\n"
        "3. Operational risk assessment and mitigation\n"
        "4. Business continuity and disaster recovery\n"
        "5. Change management and configuration control\n"
        "6. Incident response and breach notification\n"
        "Chain-of-Thought Analysis:"
    )
    return rate_limited_generate_content_optimized(prompt)

@timing_decorator
def expert_industry_specific(query: str, context: str, conversation_context: str = "") -> str:
    """Expert analysis for industry-specific compliance requirements."""
    prompt = (
        "As an industry-specific compliance expert, analyze the following query:\n\n"
        f"{conversation_context}"
        f"Query: {query}\n"
        f"Context: {context}\n\n"
        "Focus on:\n"
        "1. Industry-specific regulations (FERPA for education, GLBA for finance, etc.)\n"
        "2. Sector-specific standards and frameworks\n"
        "3. Professional licensing and certification requirements\n"
        "4. Industry best practices and guidance\n"
        "5. Regulatory body requirements and guidance\n"
        "6. Industry-specific risk factors and controls\n"
        "Chain-of-Thought Analysis:"
    )
    return rate_limited_generate_content_optimized(prompt)

@timing_decorator
def aggregate_expert_outputs(outputs: List[str], query: str, context: str) -> str:
    """Advanced aggregation and synthesis of expert outputs with cross-domain insights."""
    if not outputs:
        return "No expert analysis available."
    
    if len(outputs) == 1:
        return outputs[0]
    
    is_concise = detect_concise_request(query)
    max_tokens = get_concise_max_tokens(query)
    
    # Create a comprehensive synthesis prompt
    expert_analyses_text = ""
    for i, output in enumerate(outputs, 1):
        expert_analyses_text += f"\n--- Expert Analysis {i} ---\n{output}\n"
    
    if is_concise:
        prompt = f"""
Synthesize these expert analyses into a CONCISE, actionable response.

Original Query: {query}
Expert Analyses:{expert_analyses_text[:1000]}

Provide response as:
**Key Steps:**
• Action 1
• Action 2  
• Action 3

**Critical Requirements:**
• Requirement 1
• Requirement 2

Keep total response under 200 words. Focus only on actionable steps.
"""
    else:
        prompt = f"""
You are a senior compliance consultant tasked with synthesizing multiple expert analyses into a comprehensive, actionable response.

Original Query: {query}
Context: {context}

Expert Analyses:{expert_analyses_text}

Synthesize these expert analyses into a cohesive response that:

1. **Executive Summary**: Provide a clear, concise overview of the key findings
2. **Comprehensive Analysis**: Integrate insights from all experts, highlighting:
   - Common themes and recommendations
   - Complementary perspectives
   - Any conflicting viewpoints and how to resolve them
3. **Cross-Domain Considerations**: Identify how different compliance areas interact
4. **Prioritized Recommendations**: List actionable steps in order of importance
5. **Implementation Timeline**: Suggest phases for implementation where applicable
6. **Risk Assessment**: Highlight critical risks and mitigation strategies
7. **Next Steps**: Specific actions the user should take

Guidelines:
- Eliminate redundancy while preserving important details
- Use clear headings and bullet points for readability
- Provide specific, actionable guidance
- Include relevant regulatory citations and standards
- Maintain technical accuracy while being accessible
- Address both immediate needs and long-term compliance strategy

Synthesized Response:
"""
    
    return rate_limited_generate_content_optimized(prompt, max_tokens=max_tokens)

# Add ConversationHistory class to maintain context across queries
class ConversationHistory:
    def __init__(self, max_turns=3, timeout_seconds=600):
        self.history = []
        self.max_turns = max_turns
        self.timeout_seconds = timeout_seconds
        self.last_update_time = time.time()
        self.context_embedding = None
        self.last_compliance_status = True  # Track if last query was compliance-related

    def add_exchange(self, user_query, bot_response, is_compliance=True):
        current_time = time.time()
        if current_time - self.last_update_time > self.timeout_seconds:
            self.reset()
        
        # Only add to history if it's a compliance-related query
        if is_compliance:
            # Limit response size to prevent context growth
            truncated_response = bot_response
            if len(truncated_response) > 1000:
                truncated_response = truncated_response[:950] + "... [truncated for brevity]"
            
            self.history.append((user_query, truncated_response))
            if len(self.history) > self.max_turns:
                self.history.pop(0)
            
            self.last_update_time = current_time
            self.context_embedding = None  # Reset - will be lazily generated when needed
        
        self.last_compliance_status = is_compliance

    def get_context(self, compact=False):
        # If last query was non-compliance, don't provide context
        if not self.last_compliance_status:
            return ""
            
        if not self.history:
            return ""
        
        if compact:
            context = ""
            for i, (user, bot) in enumerate(self.history[-2:]):
                context += f"User: {user}\nResponse: [Summary of previous response]\n"
            return context
        
        context = "Previous conversation:\n"
        for user, bot in self.history:
            context += f"User: {user}\nBot: {bot}\n"
        return context

    def reset(self):
        """Reset conversation history"""
        self.history = []

@timing_decorator
def classify_compliance_query(query: str, conversation_context: str = "") -> bool:
    """Determine if query is compliance-related using AI-based classification"""
    # First, check if the query is about compliance, regulations, or business requirements
    prompt = (
        "You are a compliance query classifier. Your task is to determine if the following query is related to compliance, regulations, policies, standards, or legal requirements. "
        "Consider ONLY these specific topics:\n"
        "1. Regulatory compliance (GDPR, CCPA, HIPAA, etc.)\n"
        "2. Security standards and controls\n"
        "3. Data protection and privacy policies\n"
        "4. Business process compliance\n"
        "5. Audit requirements and documentation\n"
        "6. Legal requirements for businesses\n\n"
        "If the query is about ANYTHING ELSE, including but not limited to:\n"
        "- Personal or general topics\n"
        "- Health or medical advice\n"
        "- Social or cultural topics\n"
        "- Scientific or technical topics not related to compliance\n"
        "- Any other non-business or non-regulatory topics\n"
        "Answer 'no'.\n\n"
        f"Query: {query}\n"
        "Answer with ONLY 'yes' or 'no':"
    )
    response = rate_limited_generate_content_optimized(prompt)
    return "yes" in response.lower()

# Track recent non-compliance responses to ensure variety
recent_non_compliance_responses = {}

def generate_non_compliance_response(query: str, user_id: str = None) -> str:
    """Generate a dynamic, contextual response for non-compliance queries"""
    try:
        # Analyze the query to understand what the user is asking about
        query_lower = query.lower()
        
        # Determine the category of non-compliance query
        response_category = "general"
        query_subject = ""
        
        # Categorize the query
        if any(word in query_lower for word in ["what is", "what are", "explain", "define"]):
            if any(word in query_lower for word in ["cooking", "recipe", "food", "restaurant"]):
                response_category = "cooking_food"
                query_subject = "cooking and food topics"
            elif any(word in query_lower for word in ["movie", "film", "tv", "show", "entertainment"]):
                response_category = "entertainment"
                query_subject = "entertainment topics"
            elif any(word in query_lower for word in ["sports", "football", "cricket", "basketball", "game"]):
                response_category = "sports"
                query_subject = "sports topics"
            elif any(word in query_lower for word in ["health", "medical", "doctor", "medicine"]):
                response_category = "health"
                query_subject = "personal health topics"
            elif any(word in query_lower for word in ["weather", "climate", "temperature"]):
                response_category = "weather"
                query_subject = "weather information"
            else:
                response_category = "general_knowledge"
                query_subject = "general knowledge topics"
        elif any(word in query_lower for word in ["how to", "tutorial", "guide"]):
            response_category = "tutorial"
            query_subject = "tutorials and guides"
        elif any(word in query_lower for word in ["joke", "funny", "humor"]):
            response_category = "humor"
            query_subject = "humor and jokes"
        
        # Check if user has recent responses to avoid repetition
        avoid_phrases = []
        if user_id and user_id in recent_non_compliance_responses:
            recent_responses = recent_non_compliance_responses[user_id]
            # Extract key phrases from recent responses to avoid
            for recent_response in recent_responses[-3:]:  # Check last 3 responses
                if "curious about" in recent_response:
                    avoid_phrases.append("curious about")
                if "interesting question" in recent_response:
                    avoid_phrases.append("interesting question")
                if "outside my area" in recent_response:
                    avoid_phrases.append("outside my area")
        
        # Generate a contextual response using AI
        prompt = f"""
Generate a polite, helpful response for a user who asked a non-compliance question in a compliance chatbot.

User's question: "{query}"
Question category: {response_category}
Question subject: {query_subject}
Avoid using these phrases: {', '.join(avoid_phrases) if avoid_phrases else 'none'}

The response should:
1. Be polite and understanding
2. Briefly acknowledge what they're asking about
3. Redirect them to compliance topics
4. Suggest 2-3 specific compliance topics that might interest them
5. Be conversational and helpful, not robotic
6. Be 2-3 sentences maximum
7. Use different phrasing than previous responses

Examples of compliance topics to suggest:
- Data protection and GDPR compliance
- Security frameworks (ISO 27001, SOC 2)
- Identity and access management
- Cloud security compliance
- Audit requirements and controls
- Privacy policy development
- Risk assessment procedures
- Vendor compliance management

Make it sound natural and varied - don't use the same phrases every time.
Avoid being overly formal or robotic.
"""

        response = rate_limited_generate_content_optimized(prompt, max_tokens=3200)  # Increased max_tokens for more variety
        
        # Add compliance topic suggestions based on query context
        topic_suggestions = get_contextual_compliance_suggestions(query_lower, response_category)
        
        if topic_suggestions and response:
            response += f" {topic_suggestions}"
        
        # Fallback responses if AI generation fails
        if not response or len(response.strip()) < 10:
            fallback_responses = [
                f"I understand you're curious about {query_subject if query_subject else 'that topic'}, but I'm specialized in compliance and regulatory matters. I'd be happy to help you with questions about data protection, security frameworks, or audit requirements instead!",
                
                f"That's an interesting question about {query_subject if query_subject else 'that subject'}! However, my expertise is in compliance and governance. Feel free to ask me about GDPR compliance, identity management, or security controls.",
                
                f"I can see you're asking about {query_subject if query_subject else 'that area'}, but I'm designed to assist with compliance topics. I'd love to help you understand privacy regulations, risk assessments, or compliance frameworks instead!",
                
                f"While that's outside my area of expertise, I'm here to help with all things compliance! Whether you need information about ISO 27001, data protection policies, or vendor compliance, I'm ready to assist.",
                
                f"I focus specifically on compliance, security, and regulatory guidance. Though I can't help with {query_subject if query_subject else 'that topic'}, I'd be excited to discuss cloud security, audit procedures, or privacy impact assessments with you!",
                
                f"My specialty is in regulatory and compliance matters rather than {query_subject if query_subject else 'that area'}. How about we explore some fascinating compliance topics like zero-trust security, privacy by design, or regulatory change management?",
                
                f"That question falls outside my compliance expertise, but I'd love to help you navigate the world of data governance, security compliance, or regulatory frameworks instead!",
                
                f"I'm built to tackle compliance challenges! While I can't assist with {query_subject if query_subject else 'that topic'}, I'm excited to discuss compliance automation, risk management strategies, or security audit procedures with you.",
                
                f"Ah, {query_subject if query_subject else 'that topic'} isn't in my wheelhouse, but compliance definitely is! How about we dive into some exciting areas like breach response planning, vendor risk assessments, or privacy impact analyses?",
                
                f"I wish I could help with {query_subject if query_subject else 'that'}, but my superpower is in compliance and security! Let's talk about something in my domain - perhaps regulatory reporting, access controls, or compliance monitoring?",
                
                f"That's not really my thing, but compliance frameworks absolutely are! I'd love to chat about topics like SOC 2 implementations, GDPR compliance strategies, or security control effectiveness instead.",
                
                f"I'm afraid {query_subject if query_subject else 'that topic'} isn't where I shine, but ask me anything about compliance and I'm your bot! How about we explore business continuity planning, third-party risk management, or regulatory change tracking?",
                
                f"Sorry, but {query_subject if query_subject else 'that area'} is outside my zone of expertise. I'm much better with compliance topics like incident response procedures, control testing methodologies, or privacy program development!",
                
                f"I'd love to help, but {query_subject if query_subject else 'that'} isn't my forte. My strength lies in compliance matters - shall we discuss compliance training programs, audit readiness, or regulatory gap analyses instead?"
            ]
            
            # Filter out responses with avoided phrases
            if avoid_phrases:
                filtered_responses = [r for r in fallback_responses if not any(phrase in r.lower() for phrase in avoid_phrases)]
                fallback_responses = filtered_responses if filtered_responses else fallback_responses
            
            response = random.choice(fallback_responses)
        
        # Track this response for variety in future interactions
        if user_id:
            if user_id not in recent_non_compliance_responses:
                recent_non_compliance_responses[user_id] = []
            recent_non_compliance_responses[user_id].append(response)
            # Keep only last 5 responses to avoid memory issues
            if len(recent_non_compliance_responses[user_id]) > 5:
                recent_non_compliance_responses[user_id].pop(0)
        
        return response.strip()
        
    except Exception as e:
        logger.error(f"Error generating non-compliance response: {e}")
        # Final fallback
        return "I'm a compliance assistant focused on regulatory and security topics. I'd be happy to help you with compliance frameworks, privacy regulations, or security requirements instead!"

def get_contextual_compliance_suggestions(query_lower: str, category: str) -> str:
    """Generate contextual compliance topic suggestions based on the query"""
    try:
        suggestions_map = {
            "cooking_food": "You might be interested in food industry compliance, restaurant data protection policies, or PCI DSS for payment processing.",
            "entertainment": "Perhaps you'd like to know about content privacy policies, digital media compliance, or COPPA regulations for entertainment platforms?",
            "sports": "You could explore sports data analytics compliance, fan data protection, or privacy policies for sports platforms.",
            "health": "I can help with HIPAA compliance, healthcare data protection, or medical device security standards instead.",
            "weather": "Maybe you're interested in IoT device compliance, environmental data protection, or smart city privacy frameworks?",
            "tutorial": "I can guide you through compliance implementation tutorials, security assessment procedures, or privacy policy creation guides.",
            "humor": "How about some 'seriously fun' compliance topics like gamification in security training or user-friendly privacy notices?",
            "general_knowledge": "I can share knowledge about regulatory frameworks, compliance best practices, or security standards."
        }
        
        base_suggestions = [
            "Would you like to explore identity and access management or cloud security instead?",
            "How about learning about data protection laws or security compliance frameworks?",
            "I could help you understand audit requirements or privacy regulations.",
            "Perhaps you're interested in risk assessment procedures or compliance monitoring?",
            "Would GDPR compliance, ISO 27001, or SOC 2 frameworks be helpful to discuss?"
        ]
        
        if category in suggestions_map:
            return suggestions_map[category]
        else:
            return random.choice(base_suggestions)
            
    except Exception as e:
        logger.error(f"Error generating compliance suggestions: {e}")
        return "Feel free to ask about any compliance, security, or regulatory topics!"

def search_documents(query: str, segments: List[str], index: Any, top_k: int = 3) -> List[str]:
    """
    Search documents using FAISS similarity search.
    
    Args:
        query (str): Search query
        segments (List[str]): List of document segments
        index (Any): FAISS index
        top_k (int): Number of top results to return
        
    Returns:
        List[str]: List of relevant segments
    """
    try:
        # Get query embedding
        query_embedding = get_embedding(query)
        if query_embedding is None:
            return []
        
        # Search using FAISS index
        query_embedding = np.expand_dims(query_embedding, axis=0)
        distances, idxs = index.search(query_embedding, top_k)
        
        # Return relevant segments
        relevant_segments = []
        for idx in idxs[0]:
            if idx < len(segments):
                relevant_segments.append(segments[idx])
        
        return relevant_segments
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return []

# Precomputed expert selection for performance
EXPERT_KEYWORD_SCORES = {
    'security': {
        'azure': 5, 'azure ad': 5, 'identity': 4, 'authentication': 4, 'access control': 4,
        'security': 3, 'firewall': 3, 'encryption': 3, 'cybersecurity': 3
    },
    'privacy': {
        'gdpr': 5, 'ccpa': 5, 'privacy': 4, 'data protection': 4, 'personal data': 4,
        'consent': 3, 'data subject': 3, 'pii': 3
    },
    'audit': {
        'compliance': 4, 'audit': 4, 'iso27001': 5, 'soc2': 5, 'nist': 4,
        'framework': 3, 'control': 3, 'assessment': 3
    },
    'financial': {
        'pci dss': 5, 'sox': 5, 'financial': 4, 'payment': 4, 'banking': 3
    }
}

@timing_decorator
def select_relevant_experts_optimized(query: str) -> List[str]:
    """Optimized expert selection using precomputed scores."""
    query_lower = query.lower()
    expert_scores = {}
    
    # Fast scoring using precomputed weights
    for expert, keywords in EXPERT_KEYWORD_SCORES.items():
        score = 0
        for keyword, weight in keywords.items():
            if keyword in query_lower:
                score += weight
        if score > 0:
            expert_scores[expert] = score
    
    # Return top 2 experts for speed (reduced from 3)
    if expert_scores:
        sorted_experts = sorted(expert_scores.items(), key=lambda x: x[1], reverse=True)
        selected = [expert for expert, score in sorted_experts[:2]]
        logger.info(f"Fast expert selection: {', '.join(selected)}")
        return selected
    
    # Quick fallback
    return ['audit', 'security']

# Add support for DOCX files in upload_privacy_policy
def upload_privacy_policy(file_path: str) -> str:
    """Upload and extract text from a privacy policy document."""
    try:
        if file_path.endswith('.pdf'):
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
        elif file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        elif file_path.endswith('.docx'):
            import docx
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        else:
            return "Unsupported file format. Please upload a PDF, TXT, or DOCX file."
        return text
    except Exception as e:
        return f"Error uploading document: {e}"

# Modify analyze_privacy_policy to accept a specific framework for analysis
def analyze_privacy_policy(file_path: str, segments: List[str], index: Any, framework: str) -> str:
    """
    Analyze a privacy policy document against a specific compliance framework.
    """
    try:
        # Extract text from the document
        if file_path.endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        elif file_path.endswith('.docx'):
            text = extract_text_from_docx(file_path)
        else:
            return "Unsupported file format. Please upload a PDF or DOCX file."

        # Get framework requirements
        requirements = get_framework_requirements(framework)
        
        # Analyze each requirement
        analysis_results = []
        for req in requirements:
            # Search for relevant content in the document
            query = f"Find content related to {req['title']} and {req['description']}"
            relevant_segments = search_documents(query, segments, index, top_k=3)
            
            # Check if requirement is met
            is_met = any(req['title'].lower() in segment.lower() or 
                        req['description'].lower() in segment.lower() 
                        for segment in relevant_segments)
            
            analysis_results.append({
                'requirement': req['title'],
                'description': req['description'],
                'is_met': is_met,
                'relevant_content': relevant_segments if is_met else []
            })
        
        # Generate analysis report
        report = f"Privacy Policy Analysis against {framework} Requirements\n\n"
        
        # Summary
        total_reqs = len(analysis_results)
        met_reqs = sum(1 for r in analysis_results if r['is_met'])
        report += f"Summary:\n"
        report += f"- Total Requirements: {total_reqs}\n"
        report += f"- Requirements Met: {met_reqs}\n"
        report += f"- Requirements Missing: {total_reqs - met_reqs}\n"
        report += f"- Compliance Score: {(met_reqs/total_reqs)*100:.1f}%\n\n"
        
        # Detailed Analysis
        report += "Detailed Analysis:\n"
        for result in analysis_results:
            report += f"\nRequirement: {result['requirement']}\n"
            report += f"Description: {result['description']}\n"
            report += f"Status: {'✓ Met' if result['is_met'] else '✗ Missing'}\n"
            if result['is_met']:
                report += "Relevant Content Found:\n"
                for content in result['relevant_content']:
                    report += f"- {content}\n"
            else:
                report += "Recommendation: Add content addressing this requirement\n"
        
        return report
        
    except Exception as e:
        logger.error(f"Error analyzing privacy policy: {str(e)}")
        return f"Error analyzing privacy policy: {str(e)}"

# Add function to generate a privacy policy document
def generate_privacy_policy(framework: str, format: str = "txt") -> str:
    """
    Generate a privacy policy document based on a specific compliance framework.
    """
    try:
        # Get framework requirements
        requirements = get_framework_requirements(framework)
        
        # Generate policy sections
        sections = []
        
        # Introduction
        sections.append(f"Privacy Policy\n")
        sections.append(f"Last Updated: {datetime.now().strftime('%Y-%m-%d')}\n")
        sections.append(f"This Privacy Policy describes how we collect, use, and protect your personal information in compliance with {framework} requirements.\n")
        
        # Generate content for each requirement using AI
        for req in requirements:
            section_title = req['title']
            prompt = (
                f"Generate a detailed section for a {framework} compliant privacy policy about {req['title']}.\n"
                f"Requirement: {req['description']}\n"
                "The section should:\n"
                "1. Be specific and actionable\n"
                "2. Include all necessary legal requirements\n"
                "3. Use clear, professional language\n"
                "4. Be comprehensive but concise\n"
                "5. Include practical implementation details\n\n"
                "Generate the section content:"
            )
            
            section_content = rate_limited_generate_content(prompt)
            sections.append(f"\n{section_title}\n")
            sections.append(f"{section_content}\n")
        
        # Add standard sections
        standard_sections = {
            "Contact Information": "For any questions or concerns regarding this Privacy Policy or our data practices, please contact us at:\n\n[Company Name]\n[Address]\n[Email]\n[Phone]",
            "Changes to This Policy": f"We may update this Privacy Policy from time to time to reflect changes in our practices or for other operational, legal, or regulatory reasons. The updated version will be indicated by an updated 'Last Updated' date.",
            "Compliance and Certification": f"We are committed to maintaining compliance with {framework} requirements and regularly review our practices to ensure they meet the highest standards of data protection and privacy."
        }
        
        for title, content in standard_sections.items():
            sections.append(f"\n{title}\n")
            sections.append(f"{content}\n")
        
        # Combine all sections
        policy_text = "\n".join(sections)
        
        # Convert to requested format
        if format.lower() == "pdf":
            # Convert to PDF
            doc = Document()
            for section in sections:
                doc.add_paragraph(section)
            pdf_path = f"generated_policy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            doc.save(pdf_path)
            return f"Policy generated and saved as {pdf_path}"
            
        elif format.lower() == "docx":
            # Convert to DOCX
            doc = Document()
            for section in sections:
                doc.add_paragraph(section)
            docx_path = f"generated_policy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
            doc.save(docx_path)
            return f"Policy generated and saved as {docx_path}"
            
        else:
            return policy_text
            
    except Exception as e:
        logger.error(f"Error generating privacy policy: {str(e)}")
        return f"Error generating privacy policy: {str(e)}"

def get_framework_requirements(framework: str) -> List[Dict[str, str]]:
    """
    Get the requirements for a specific compliance framework.
    """
    requirements = {
        "GDPR": [
            {
                "title": "Data Collection and Processing",
                "description": "Clear information about what personal data is collected, how it is processed, and the purposes of processing"
            },
            {
                "title": "Legal Basis for Processing",
                "description": "Explanation of the legal grounds for processing personal data, including consent, contract, legal obligation, vital interests, public task, and legitimate interests"
            },
            {
                "title": "Data Subject Rights",
                "description": "Detailed explanation of data subject rights under GDPR, including right to access, rectification, erasure, restriction, portability, and objection"
            },
            {
                "title": "Data Retention",
                "description": "Clear information about data retention periods and criteria for determining retention periods"
            },
            {
                "title": "Data Security",
                "description": "Comprehensive description of technical and organizational security measures implemented to protect personal data"
            },
            {
                "title": "International Data Transfers",
                "description": "Information about international data transfers and appropriate safeguards implemented"
            },
            {
                "title": "Data Breach Notification",
                "description": "Procedures for handling and reporting data breaches in compliance with GDPR requirements"
            },
            {
                "title": "Data Protection Officer",
                "description": "Information about the Data Protection Officer (DPO) and their contact details"
            }
        ],
        "CCPA": [
            {
                "title": "Personal Information Collection",
                "description": "Categories of personal information collected and the business or commercial purposes for collection"
            },
            {
                "title": "Consumer Rights",
                "description": "Detailed explanation of consumer rights under CCPA, including right to know, delete, and opt-out"
            },
            {
                "title": "Data Sales",
                "description": "Information about sale of personal information and opt-out rights"
            },
            {
                "title": "Financial Incentives",
                "description": "Details about any financial incentives offered for personal information"
            }
        ],
        "HIPAA": [
            {
                "title": "Protected Health Information",
                "description": "How PHI is collected, used, and disclosed in compliance with HIPAA requirements"
            },
            {
                "title": "Privacy Practices",
                "description": "Detailed description of privacy practices and patient rights under HIPAA"
            },
            {
                "title": "Security Measures",
                "description": "Comprehensive description of security measures implemented to protect PHI"
            }
        ]
    }
    
    return requirements.get(framework, requirements["GDPR"])

def generate_section_content(requirement: str, framework: str) -> str:
    """
    Generate content for a specific section based on the requirement and framework.
    """
    # This is a simplified version. In a real implementation, you would use
    # a more sophisticated approach, possibly using a language model to generate
    # appropriate content based on the requirement and framework.
    
    content_templates = {
        "GDPR": {
            "Data Collection and Processing": "We collect and process your personal data in accordance with GDPR requirements. This includes [specific data types] which we use for [specific purposes].",
            "Legal Basis": "We process your personal data based on the following legal grounds: [list of legal bases].",
            "Data Subject Rights": "Under GDPR, you have the right to access, rectify, erase, and port your personal data. You can exercise these rights by [instructions].",
            "Data Retention": "We retain your personal data for [specific period] or as required by law.",
            "Data Security": "We implement appropriate technical and organizational measures to protect your personal data."
        },
        "CCPA": {
            "Personal Information Collection": "We collect the following categories of personal information: [list of categories].",
            "Business Purpose": "We collect your personal information for the following business purposes: [list of purposes].",
            "Consumer Rights": "Under CCPA, you have the right to know, delete, and opt-out of the sale of your personal information.",
            "Data Sales": "We [do/do not] sell your personal information to third parties."
        },
        "HIPAA": {
            "Protected Health Information": "We collect and use your protected health information (PHI) for treatment, payment, and healthcare operations.",
            "Privacy Practices": "We maintain the privacy of your PHI and provide you with notice of our privacy practices.",
            "Security Measures": "We implement appropriate safeguards to protect your PHI from unauthorized access, use, or disclosure."
        }
    }
    
    # Find the most relevant template
    for key, template in content_templates.get(framework, content_templates["GDPR"]).items():
        if key.lower() in requirement.lower():
            return template
    
    return f"We handle {requirement.lower()} in accordance with {framework} requirements."

# Cache embeddings for performance
@lru_cache(maxsize=1000)
def get_cached_embedding(text_hash: str, text: str) -> np.ndarray:
    """Cached version of get_embedding"""
    return get_embedding(text)

# Hash function for text to use with lru_cache
def hash_text(text: str) -> str:
    """Create a hash of text for caching purposes"""
    return hashlib.md5(text.encode()).hexdigest()

# Add cached version of expertise functions
def cached_expert_response(expert_type: str, query: str, context: str, conversation_context: str = "") -> str:
    """Get expert response from cache if available, otherwise generate and cache it"""
    cache_key = f"{expert_type}:{hash_text(query)}:{hash_text(context)}:{hash_text(conversation_context)}"
    
    if cache_key in QUERY_CACHE:
        logger.info(f"Cache hit for {expert_type} expert")
        return QUERY_CACHE[cache_key]
    
    # Call appropriate expert function based on type
    if expert_type == "security":
        response = expert_security_controls(query, context, conversation_context)
    elif expert_type == "privacy":
        response = expert_privacy_regulations(query, context, conversation_context)
    elif expert_type == "audit":
        response = expert_audit_compliance(query, context, conversation_context)
    elif expert_type == "financial":
        response = expert_financial_compliance(query, context, conversation_context)
    elif expert_type == "healthcare":
        response = expert_healthcare_compliance(query, context, conversation_context)
    elif expert_type == "international":
        response = expert_international_compliance(query, context, conversation_context)
    elif expert_type == "operational":
        response = expert_operational_compliance(query, context, conversation_context)
    elif expert_type == "industry_specific":
        response = expert_industry_specific(query, context, conversation_context)
    else:
        return ""
    
    # Cache the response
    QUERY_CACHE[cache_key] = response
    
    # Periodically save the cache (every 10 new entries)
    if len(QUERY_CACHE) % 10 == 0:
        save_query_cache()
        
    return response

@timing_decorator
def process_expert_analyses(query: str, context: str, conversation_context: str, experts: List[str]) -> List[str]:
    """Process multiple expert analyses in parallel with optimized scheduling."""
    results = []
    
    # Process experts in parallel using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for expert in experts:
            futures.append(executor.submit(cached_expert_response, expert, query, context, conversation_context))
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Error processing expert analysis: {e}")
    
    return results

@timing_decorator
def is_compliance_related_optimized(query: str, conversation_context: str = "") -> Tuple[bool, str]:
    """
    Optimized compliance query classification with fast-path processing.
    """
    
    # Fast Path 1: Check cache first
    cache_key = f"classification:{hash_text(query)}"
    if cache_key in QUERY_CACHE:
        cached_result = QUERY_CACHE[cache_key]
        if isinstance(cached_result, dict) and 'is_compliance' in cached_result:
            return cached_result['is_compliance'], cached_result.get('reason', 'Cached result')
    
    # Fast Path 2: Simple keyword screening for obviously non-compliant topics
    sensitive_topics = [
        "sex", "sexual", "porn", "pornography", "nude", "nudity",
        "drug", "drugs", "weapon", "weapons", "violence", "violent",
        "suicide", "self-harm", "cooking", "recipe", "sports", "football", 
        "cricket", "entertainment", "movie", "film", "music", "celebrity", "gossip"
    ]
    
    query_lower = query.lower()
    for topic in sensitive_topics:
        if topic in query_lower:
            professional_context = [
                "compliance", "policy", "regulation", "standard", "framework",
                "business", "organization", "company", "workplace", "professional"
            ]
            if not any(context in query_lower for context in professional_context):
                result = (False, f"Query about non-compliance topic: {topic}")
                QUERY_CACHE[cache_key] = {'is_compliance': False, 'reason': result[1]}
                return result
    
    # Fast Path 3: Strong compliance indicators
    strong_compliance_keywords = [
        "gdpr", "ccpa", "hipaa", "sox", "iso27001", "soc2", "nist", "pci dss",
        "data protection", "privacy policy", "compliance", "audit", "security framework",
        "regulatory", "governance", "risk management", "azure ad", "identity management"
    ]
    
    for keyword in strong_compliance_keywords:
        if keyword in query_lower:
            result = (True, f"Strong compliance keyword detected: {keyword}")
            QUERY_CACHE[cache_key] = {'is_compliance': True, 'reason': result[1]}
            return result
    
    # Fast Path 4: Business/technical context
    business_technical_keywords = [
        "azure", "cloud", "security", "identity", "authentication", "access control",
        "database", "network", "infrastructure", "application", "system",
        "organization", "business", "company", "enterprise", "corporate"
    ]
    
    if any(keyword in query_lower for keyword in business_technical_keywords):
        result = (True, f"Business/technical context detected")
        QUERY_CACHE[cache_key] = {'is_compliance': True, 'reason': result[1]}
        return result
    
    # Only use expensive AI analysis for borderline cases
    try:
        ai_classification, confidence = analyze_query_intent_with_ai(query, conversation_context)
        result = (ai_classification and confidence > 0.5, f"AI analysis: {confidence:.2f} confidence")
        QUERY_CACHE[cache_key] = {'is_compliance': result[0], 'reason': result[1]}
        return result
    except Exception as e:
        logger.warning(f"AI classification failed, defaulting to compliant: {e}")
        result = (True, "Defaulted to compliant due to analysis failure")
        QUERY_CACHE[cache_key] = {'is_compliance': True, 'reason': result[1]}
        return result

@timing_decorator
def detect_query_type(query: str, conversation_context: str = "") -> Tuple[str, List[str]]:
    """
    Detect the type of compliance query and required experts using enhanced selection.
    
    Args:
        query (str): The user's query
        conversation_context (str): The conversation context to help determine query type
        
    Returns:
        Tuple[str, List[str]]: (query_type, required_experts)
    """
    
    # Check for framework selection queries first
    framework_keywords = ['which framework', 'what framework', 'recommend framework', 
                         'choose framework', 'select framework', 'best framework',
                         'framework recommendation', 'framework selection']
    
    if any(keyword in query.lower() for keyword in framework_keywords):
        return 'framework_selection', ['audit']
    
    # Use the enhanced expert selection system for all other queries
    required_experts = select_relevant_experts_optimized(query)
    
    # Determine query type based on selected experts
    if len(required_experts) == 1:
        if required_experts[0] == 'security':
            query_type = 'security'
        elif required_experts[0] == 'privacy':
            query_type = 'privacy'
        elif required_experts[0] == 'financial':
            query_type = 'financial'
        elif required_experts[0] == 'healthcare':
            query_type = 'healthcare'
        elif required_experts[0] == 'international':
            query_type = 'international'
        elif required_experts[0] == 'operational':
            query_type = 'operational'
        elif required_experts[0] == 'industry_specific':
            query_type = 'industry_specific'
        else:
            query_type = 'audit'
    else:
        # Multi-expert query
        query_type = 'multi_domain'
    
    # Default to audit if no specific experts identified
    if not required_experts:
        required_experts = ['audit']
        query_type = 'general'
    
    return query_type, required_experts

@timing_decorator
def get_framework_recommendation(query: str) -> Tuple[str, float]:
    """Get framework recommendation for framework selection queries"""
    start_time = time.time()
    
    prompt = (
        "Based on the following query, recommend appropriate compliance frameworks or standards:\n\n"
        f"Query: {query}\n\n"
        "Provide a concise recommendation focusing on:\n"
        "1. Most relevant frameworks\n"
        "2. Key requirements\n"
        "3. Implementation considerations\n"
        "Response:"
    )
    
    response = rate_limited_generate_content(prompt)
    end_time = time.time()
    
    return response, end_time - start_time

async def get_progressive_response(query: str, experts: List[str], context: str, conversation_context: str) -> AsyncIterator[str]:
    """Generate progressive responses from multiple experts"""
    expert_responses = []
    
    for expert in experts:
        response = cached_expert_response(expert, query, context, conversation_context)
        expert_responses.append(response)
        yield aggregate_expert_outputs(expert_responses, query, context)

@timing_decorator
def process_query_optimized(query: str, context: str, conversation_context: str, conversation_history: 'ConversationHistory' = None) -> Tuple[str, float]:
    """Optimized query processing with fast response paths."""
    start_time = time.time()
    
    # Step 1: Validate input
    is_valid, error_message = validate_query_input(query)
    if not is_valid:
        end_time = time.time()
        return error_message, end_time - start_time
    
    # Step 2: Check for conversation history queries
    if detect_conversation_history_query(query):
        response = handle_conversation_history_query(conversation_history)
        end_time = time.time()
        return response, end_time - start_time
    
    # Fast Path: Check if this is a compliance-related query
    is_compliance, reason = is_compliance_related_optimized(query, conversation_context)
    
    if not is_compliance:
        # Quick non-compliance response
        response = generate_non_compliance_response(query)
        end_time = time.time()
        return response, end_time - start_time
    
    # Fast Path: Check for simple informational queries
    if detect_informational_query(query):
        logger.info("Detected informational query - using concise response")
        response = generate_concise_informational_response(query)
        end_time = time.time()
        return response, end_time - start_time
    
    # Check for exact cache match first
    cache_key = f"exact_query:{hash_text(query)}"
    if cache_key in QUERY_CACHE:
        cached_response = QUERY_CACHE[cache_key]
        if isinstance(cached_response, str):
            end_time = time.time()
            return cached_response, end_time - start_time
    
    # Fast expert selection
    required_experts = select_relevant_experts_optimized(query)
    
    # Check for partial cache matches (similar queries)
    similar_response = find_similar_cached_response(query, required_experts)
    if similar_response:
        logger.info("Using similar cached response")
        end_time = time.time()
        return similar_response, end_time - start_time
    
    # Process with optimized expert system
    expert_responses = []
    for expert in required_experts:
        response = cached_expert_response(expert, query, context, conversation_context)
        if response:
            expert_responses.append(response)
    
    # Quick aggregation for speed
    if len(expert_responses) == 1:
        final_response = expert_responses[0]
    else:
        final_response = aggregate_expert_outputs(expert_responses, query, context)
    
    # Cache the response
    QUERY_CACHE[cache_key] = final_response
    
    # Async save to avoid blocking
    if len(QUERY_CACHE) % 10 == 0:
        try:
            save_query_cache()
        except:
            pass  # Don't block on cache save errors
    
    end_time = time.time()
    return final_response, end_time - start_time

def find_similar_cached_response(query: str, experts: List[str]) -> Optional[str]:
    """Find similar cached responses for faster retrieval."""
    try:
        query_lower = query.lower()
        
        # Look for cached responses with similar expert combinations
        for cache_key, cached_data in QUERY_CACHE.items():
            if isinstance(cached_data, dict) and 'response' in cached_data:
                # Check if it's a similar query type
                if cached_data.get('experts') == experts:
                    # Simple keyword similarity check
                    cached_query = cached_data.get('original_query', '')
                    if cached_query:
                        # Count common words
                        query_words = set(query_lower.split())
                        cached_words = set(cached_query.lower().split())
                        similarity = len(query_words & cached_words) / len(query_words | cached_words)
                        
                        if similarity > 0.7:  # High similarity threshold
                            return cached_data['response']
        
        return None
        
    except Exception as e:
        logger.error(f"Error finding similar cached response: {e}")
        return None


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file with support for scanned documents."""
    try:
        logger.info(f"Extracting text from PDF: {file_path}")
        
        # First try with PyPDF2
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                # Validate PDF structure
                if not pdf_reader.metadata and len(pdf_reader.pages) == 0:
                    raise ValueError("Invalid PDF structure")
                
                text = ""
                for i, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                        else:
                            logger.warning(f"No text extracted from page {i+1}")
                    except Exception as e:
                        logger.error(f"Error extracting text from page {i+1}: {str(e)}")
                        continue
                
                if text.strip():
                    return text
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {str(e)}")
        
        # Try pdfplumber
        try:
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as e:
                        logger.error(f"Error extracting text with pdfplumber: {str(e)}")
                        continue
                
                if text.strip():
                    return text
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {str(e)}")
        
        # If no text was extracted, try OCR using pytesseract
        try:
            import pytesseract
            from pdf2image import convert_from_path
            import tempfile
            
            # Convert PDF to images
            with tempfile.TemporaryDirectory() as temp_dir:
                images = convert_from_path(file_path, output_folder=temp_dir)
                
                text = ""
                for i, image in enumerate(images):
                    try:
                        # Extract text using OCR
                        page_text = pytesseract.image_to_string(image)
                        if page_text:
                            text += page_text + "\n"
                        else:
                            logger.warning(f"No text extracted from page {i+1} using OCR")
                    except Exception as e:
                        logger.error(f"Error during OCR for page {i+1}: {str(e)}")
                        continue
                
                if text.strip():
                    return text
        except Exception as e:
            logger.warning(f"OCR extraction failed: {str(e)}")
        
        # If all methods fail, try to repair the PDF
        try:
            import pikepdf
            with pikepdf.open(file_path) as pdf:
                # Create a temporary file for the repaired version
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                    repaired_path = temp_file.name
                
                # Save repaired version
                pdf.save(repaired_path)
                
                # Try extraction again with the repaired file
                try:
                    with open(repaired_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        text = ""
                        for page in pdf_reader.pages:
                            text += page.extract_text() + "\n"
                        
                        if text.strip():
                            return text
                finally:
                    # Clean up repaired file
                    try:
                        os.remove(repaired_path)
                    except:
                        pass
        except Exception as e:
            logger.error(f"PDF repair attempt failed: {str(e)}")
        
        raise ValueError("All PDF extraction methods failed")
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise

def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    try:
        logger.info(f"Extracting text from DOCX: {file_path}")
        doc = docx.Document(file_path)
        text = ""
        for i, paragraph in enumerate(doc.paragraphs):
            try:
                if paragraph.text:
                    text += paragraph.text + "\n"
            except Exception as e:
                logger.error(f"Error extracting text from paragraph {i+1}: {str(e)}")
                continue
        return text
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {str(e)}")
        raise

def process_uploaded_document(file_path: str) -> str:
    """Process an uploaded document and return its text content."""
    try:
        logger.info(f"Processing document: {file_path}")
        
        # Determine file type and extract text
        if file_path.lower().endswith('.pdf'):
            logger.info("Extracting text from PDF")
            text = extract_text_from_pdf(file_path)
        elif file_path.lower().endswith('.docx'):
            logger.info("Extracting text from DOCX")
            text = extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path}")

        if not text or not text.strip():
            raise ValueError("No text content could be extracted from the document")

        logger.info(f"Successfully extracted {len(text)} characters of text")
        
        # Process the text into segments
        segments = process_text_into_segments(text)
        logger.info(f"Created {len(segments)} text segments")
        
        # Generate embeddings for the segments
        embeddings = []
        for i, segment in enumerate(segments):
            try:
                embedding = get_embedding(segment)
                if embedding is not None:
                    embeddings.append(embedding)
                else:
                    logger.warning(f"Failed to generate embedding for segment {i}")
            except Exception as e:
                logger.error(f"Error generating embedding for segment {i}: {str(e)}")
                continue
        
        if not embeddings:
            raise ValueError("Failed to generate embeddings for any segments")
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        # Create or update FAISS index
        try:
            embeddings_array = np.array(embeddings).astype('float32')
            dimension = embeddings_array.shape[1]
            
            # Create a new index or load existing one
            index_path = Path("faiss_indexes") / "uploaded_docs.index"
            if index_path.exists():
                logger.info("Loading existing FAISS index")
                index = faiss.read_index(str(index_path))
                # Add new vectors to existing index
                index.add(embeddings_array)
            else:
                logger.info("Creating new FAISS index")
                # Create new index
                index = faiss.IndexFlatL2(dimension)
                index.add(embeddings_array)
            
            # Save the updated index
            index_path.parent.mkdir(exist_ok=True)
            faiss.write_index(index, str(index_path))
            logger.info("FAISS index saved successfully")
            
            # Save segments and embeddings for future use
            segments_path = Path("embeddings") / "uploaded_docs_segments.json"
            embeddings_path = Path("embeddings") / "uploaded_docs_embeddings.npy"
            
            segments_path.parent.mkdir(exist_ok=True)
            embeddings_path.parent.mkdir(exist_ok=True)
            
            with open(segments_path, 'w', encoding='utf-8') as f:
                json.dump(segments, f)
            
            np.save(str(embeddings_path), embeddings_array)
            logger.info("Segments and embeddings saved successfully")
            
        except Exception as e:
            logger.error(f"Error creating/updating FAISS index: {str(e)}")
            # Continue even if index creation fails - we still have the text
        
        return text

    except Exception as e:
        logger.error(f"Error processing uploaded document: {str(e)}", exc_info=True)
        raise

def process_text_into_segments(text: str, max_segment_length: int = 1000) -> List[str]:
    """Process text into segments of appropriate length."""
    try:
        logger.info("Processing text into segments")
        # Split text into sentences (simple approach)
        sentences = text.replace('\n', ' ').split('. ')
        segments = []
        current_segment = ""
        
        for sentence in sentences:
            if len(current_segment) + len(sentence) < max_segment_length:
                current_segment += sentence + ". "
            else:
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = sentence + ". "
        
        if current_segment:
            segments.append(current_segment.strip())
        
        logger.info(f"Created {len(segments)} segments")
        return segments
    except Exception as e:
        logger.error(f"Error processing text into segments: {str(e)}")
        raise

def generate_terms_and_conditions(framework: str, format: str = "txt") -> str:
    """
    Generate Terms & Conditions document based on a specific compliance framework.
    """
    try:
        # Get framework requirements
        requirements = get_framework_requirements(framework)
        
        # Generate sections
        sections = []
        
        # Introduction
        sections.append(f"Terms and Conditions\n")
        sections.append(f"Last Updated: {datetime.now().strftime('%Y-%m-%d')}\n")
        sections.append(f"These Terms and Conditions govern your use of our services and are designed to comply with {framework} requirements.\n")
        
        # Generate content for each requirement using AI
        for req in requirements:
            section_title = req['title']
            prompt = (
                f"Generate a detailed section for {framework} compliant Terms and Conditions about {req['title']}.\n"
                f"Requirement: {req['description']}\n"
                "The section should:\n"
                "1. Be specific and actionable\n"
                "2. Include all necessary legal requirements\n"
                "3. Use clear, professional language\n"
                "4. Be comprehensive but concise\n"
                "5. Include practical implementation details\n\n"
                "Generate the section content:"
            )
            
            section_content = rate_limited_generate_content(prompt)
            sections.append(f"\n{section_title}\n")
            sections.append(f"{section_content}\n")
        
        # Add standard sections
        standard_sections = {
            "Acceptance of Terms": "By accessing or using our services, you agree to be bound by these Terms and Conditions.",
            "Service Description": "We provide compliance and security services designed to help organizations meet regulatory requirements.",
            "User Obligations": "Users must comply with all applicable laws and regulations while using our services.",
            "Intellectual Property": "All content and materials provided through our services are protected by intellectual property rights.",
            "Limitation of Liability": "We are not liable for any indirect, incidental, special, consequential, or punitive damages.",
            "Termination": "We reserve the right to terminate or suspend access to our services for violations of these terms.",
            "Governing Law": f"These terms are governed by applicable laws and {framework} requirements.",
            "Contact Information": "For questions about these Terms and Conditions, please contact us at:\n\n[Company Name]\n[Address]\n[Email]\n[Phone]"
        }
        
        for title, content in standard_sections.items():
            sections.append(f"\n{title}\n")
            sections.append(f"{content}\n")
        
        # Combine all sections
        terms_text = "\n".join(sections)
        
        # Convert to requested format
        if format.lower() == "pdf":
            # Convert to PDF
            doc = Document()
            for section in sections:
                doc.add_paragraph(section)
            pdf_path = f"generated_terms_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            doc.save(pdf_path)
            return f"Terms and Conditions generated and saved as {pdf_path}"
            
        elif format.lower() == "docx":
            # Convert to DOCX
            doc = Document()
            for section in sections:
                doc.add_paragraph(section)
            docx_path = f"generated_terms_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
            doc.save(docx_path)
            return f"Terms and Conditions generated and saved as {docx_path}"
            
        else:
            return terms_text
            
    except Exception as e:
        logger.error(f"Error generating Terms and Conditions: {str(e)}")
        return f"Error generating Terms and Conditions: {str(e)}"


# Dynamic learning system for query classification
CLASSIFICATION_FEEDBACK_FILE = os.path.join(CACHE_DIR, "classification_feedback.json")
classification_feedback = {}

# Load existing feedback
if os.path.exists(CLASSIFICATION_FEEDBACK_FILE):
    try:
        with open(CLASSIFICATION_FEEDBACK_FILE, 'r') as f:
            classification_feedback = json.load(f)
        logger.info(f"Loaded {len(classification_feedback)} classification feedback entries")
    except Exception as e:
        logger.error(f"Error loading classification feedback: {e}")

def save_classification_feedback():
    """Save classification feedback to disk"""
    try:
        with open(CLASSIFICATION_FEEDBACK_FILE, 'w') as f:
            json.dump(classification_feedback, f, indent=2)
        logger.info(f"Saved {len(classification_feedback)} classification feedback entries")
    except Exception as e:
        logger.error(f"Error saving classification feedback: {e}")

def learn_from_user_interaction(query: str, was_helpful: bool, actual_classification: bool):
    """Learn from user feedback to improve future classifications"""
    query_hash = hash_text(query)
    
    feedback_entry = {
        'query': query,
        'was_helpful': was_helpful,
        'actual_classification': actual_classification,
        'timestamp': datetime.now().isoformat(),
        'embedding': get_embedding(query).tolist() if get_embedding(query) is not None else None
    }
    
    classification_feedback[query_hash] = feedback_entry
    save_classification_feedback()

def get_historical_classification_patterns(query: str) -> Tuple[float, str]:
    """Analyze historical patterns to predict classification"""
    try:
        if not classification_feedback:
            return 0.0, "No historical data"
        
        query_embedding = get_embedding(query)
        if query_embedding is None:
            return 0.0, "Could not generate embedding"
        
        # Find similar historical queries
        similarities = []
        helpful_classifications = []
        
        for feedback in classification_feedback.values():
            if feedback.get('embedding'):
                hist_embedding = np.array(feedback['embedding'])
                similarity = cosine_similarity([query_embedding], [hist_embedding])[0][0]
                
                if similarity > 0.7:  # High similarity threshold
                    similarities.append(similarity)
                    if feedback['was_helpful']:
                        helpful_classifications.append(feedback['actual_classification'])
        
        if helpful_classifications:
            # Weight by similarity and recency
            compliance_score = sum(helpful_classifications) / len(helpful_classifications)
            confidence = min(1.0, len(helpful_classifications) * 0.2)  # More samples = higher confidence
            return compliance_score * confidence, f"Based on {len(helpful_classifications)} similar queries"
        
        return 0.0, "No similar historical queries found"
        
    except Exception as e:
        logger.error(f"Error in historical analysis: {e}")
        return 0.0, "Error in historical analysis"

def analyze_document_intent(query: str, conversation_context: str = "", has_uploaded_doc: bool = False) -> Dict[str, Any]:
    """
    Intelligently analyze user intent regarding document operations using AI.
    Returns classification of what the user wants to do with documents.
    """
    try:
        prompt = f"""
Analyze this user query to understand their intent. Be VERY precise in classification.

User Query: "{query}"
Conversation Context: "{conversation_context}"
Has Uploaded Document: {has_uploaded_doc}

CLASSIFICATION RULES:
1. GENERAL_COMPLIANCE - Simple informational questions about compliance concepts, frameworks, regulations
   Examples: "what is gdpr", "explain hipaa", "what are gdpr requirements", "tell me about ccpa"

2. ANALYZE_UPLOADED - Only when user explicitly asks about an uploaded document
   Examples: "analyze my document", "review my privacy policy", "check my uploaded file"

3. GENERATE_NEW - Only when user EXPLICITLY asks to CREATE/GENERATE a new document
   Examples: "create a privacy policy", "generate gdpr document", "make me a terms document"
   NOT: "what is gdpr", "explain privacy policy", "gdpr requirements"

4. COMPARE_COMPLIANCE - User wants to compare their document against standards
   Examples: "compare my document to gdpr", "how compliant is my policy"

5. GET_IMPROVEMENT_SUGGESTIONS - User wants suggestions (no document generation)
   Examples: "how can I improve", "what suggestions do you have", "how to make it better"

6. IMPROVE_DOCUMENT - User explicitly wants an improved version generated
   Examples: "generate improved version", "create better document", "make improved policy"

7. NON_DOCUMENT - Not related to compliance or documents

CRITICAL: 
- Simple questions about compliance topics = GENERAL_COMPLIANCE
- Questions about regulations/frameworks = GENERAL_COMPLIANCE  
- Only classify as GENERATE_NEW if user explicitly asks to CREATE/GENERATE/MAKE a document
- "what is X" questions are ALWAYS GENERAL_COMPLIANCE

Current Query Analysis:
- Is this asking WHAT something is? → GENERAL_COMPLIANCE
- Is this asking to CREATE/GENERATE? → GENERATE_NEW
- Is this about an uploaded document? → ANALYZE_UPLOADED

Respond in JSON format:
{{
  "intent": "CATEGORY_NAME",
  "document_type": "unknown",
  "framework": "general",
  "urgency": "low",
  "confidence": 0.0,
  "reasoning": "brief explanation"
}}
"""

        response = rate_limited_generate_content(prompt, temperature=0.1)
        
        try:
            # Try to parse JSON response
            import json
            intent_data = json.loads(response)
            
            # Validate required fields
            required_fields = ["intent", "document_type", "framework", "urgency", "confidence", "reasoning"]
            if all(field in intent_data for field in required_fields):
                return intent_data
        except:
            pass
        
        # Fallback analysis if AI parsing fails
        return analyze_document_intent_fallback(query, has_uploaded_doc)
        
    except Exception as e:
        logger.error(f"Error in document intent analysis: {e}")
        return analyze_document_intent_fallback(query, has_uploaded_doc)

def analyze_document_intent_fallback(query: str, has_uploaded_doc: bool) -> Dict[str, Any]:
    """Fallback document intent analysis using semantic similarity."""
    try:
        query_lower = query.lower()
        query_embedding = get_embedding(query)
        
        # First check for informational questions - these should NEVER be document generation
        informational_patterns = [
            "what is", "what are", "explain", "tell me about", "describe", 
            "define", "definition of", "meaning of", "what does", "how does"
        ]
        
        if any(pattern in query_lower for pattern in informational_patterns):
            # Check if it's about a framework
            framework = "general"
            frameworks = ["gdpr", "ccpa", "hipaa", "iso27001", "soc2", "nist", "pci"]
            for fw in frameworks:
                if fw in query_lower:
                    framework = fw.upper()
                    break
            
            return {
                "intent": "GENERAL_COMPLIANCE",
                "document_type": "unknown",
                "framework": framework,
                "urgency": "low",
                "confidence": 0.95,
                "reasoning": "Informational query about compliance topic"
            }
        
        # Define intent patterns with embeddings - updated with better patterns
        intent_patterns = {
            "ANALYZE_UPLOADED": [
                "analyze my document for compliance issues",
                "check if my privacy policy is compliant",
                "review my terms and conditions",
                "is my document following regulations"
            ],
            "GENERATE_NEW": [
                "create a new privacy policy for me",
                "generate compliant terms and conditions", 
                "make me a GDPR compliant document",
                "draft a privacy policy according to regulations"
            ],
            "COMPARE_COMPLIANCE": [
                "compare my document against GDPR requirements",
                "check compliance with specific framework",
                "how does my policy measure against standards"
            ],
            "GET_IMPROVEMENT_SUGGESTIONS": [
                "how can I make it better",
                "how to improve my document",
                "what should I fix in my policy",
                "give me suggestions to improve",
                "tell me how to make it better",
                "what improvements do you recommend"
            ],
            "IMPROVE_DOCUMENT": [
                "generate an improved version of my document",
                "create a better version of my policy",
                "make me an improved compliant document",
                "fix my document and generate new version"
            ]
        }
        
        best_intent = "GENERAL_COMPLIANCE"
        best_score = 0.0
        
        # Check for explicit generation keywords only if they exist
        generation_keywords = ["create", "generate", "make me", "draft", "produce", "build"]
        document_keywords = ["document", "policy", "terms", "agreement", "contract"]
        
        has_generation_intent = any(gen_word in query_lower for gen_word in generation_keywords)
        has_document_context = any(doc_word in query_lower for doc_word in document_keywords)
        
        # Only consider generation if BOTH generation keywords AND document context exist
        if has_generation_intent and has_document_context:
            # Check for specific suggestion keywords first
            suggestion_keywords = ["how can i", "how to", "what should i", "suggestions", "recommend", "advice", "tell me how"]
            if any(keyword in query_lower for keyword in suggestion_keywords):
                best_intent = "GET_IMPROVEMENT_SUGGESTIONS"
                best_score = 0.9
            else:
                # Use embedding similarity for generation intents
                if query_embedding is not None:
                    for intent, patterns in intent_patterns.items():
                        for pattern in patterns:
                            pattern_embedding = get_embedding(pattern)
                            if pattern_embedding is not None:
                                similarity = cosine_similarity([query_embedding], [pattern_embedding])[0][0]
                                if similarity > best_score and similarity > 0.7:  # Higher threshold for generation
                                    best_score = similarity
                                    best_intent = intent
        
        # Determine document type
        doc_type = "unknown"
        if any(term in query_lower for term in ["privacy policy", "privacy"]):
            doc_type = "privacy_policy"
        elif any(term in query_lower for term in ["terms", "conditions", "terms and conditions"]):
            doc_type = "terms_conditions"
        
        # Determine framework
        framework = "general"
        frameworks = ["gdpr", "ccpa", "hipaa", "iso27001", "soc2", "nist", "pci"]
        for fw in frameworks:
            if fw in query_lower:
                framework = fw.upper()
                break
        
        return {
            "intent": best_intent,
            "document_type": doc_type,
            "framework": framework,
            "urgency": "medium",
            "confidence": best_score,
            "reasoning": f"Semantic analysis with {best_score:.2f} confidence"
        }
        
    except Exception as e:
        logger.error(f"Error in fallback intent analysis: {e}")
        return {
            "intent": "GENERAL_COMPLIANCE",
            "document_type": "unknown", 
            "framework": "general",
            "urgency": "low",
            "confidence": 0.0,
            "reasoning": "Fallback analysis"
        }

def generate_comprehensive_document_analysis(document_text: str, framework: str, document_type: str) -> str:
    """Generate a comprehensive analysis of an uploaded document against compliance requirements."""
    try:
        prompt = f"""
Conduct a comprehensive compliance analysis of this {document_type} document against {framework} requirements.

Document Content (first 3000 characters):
{document_text[:3000]}

Provide a detailed analysis including:

1. **Executive Summary**
   - Overall compliance status (Compliant/Partially Compliant/Non-Compliant)
   - Compliance score (percentage)
   - Key findings summary

2. **Detailed Requirements Analysis**
   - List specific {framework} requirements
   - For each requirement: Met/Not Met/Partially Met
   - Evidence from the document
   - Missing elements

3. **Critical Issues** (if any)
   - High-priority compliance gaps
   - Legal risks
   - Immediate action items

4. **Recommendations**
   - Specific improvements needed
   - Additional clauses to add
   - Language modifications

5. **Implementation Roadmap**
   - Priority 1: Critical fixes
   - Priority 2: Important improvements  
   - Priority 3: Best practice enhancements

6. **Next Steps**
   - Immediate actions required
   - Timeline recommendations
   - Follow-up considerations

Format the response with clear headings and bullet points for easy reading.
"""

        analysis = rate_limited_generate_content(prompt, temperature=0.2)
        
        if not analysis or len(analysis.strip()) < 100:
            return f"I've analyzed your {document_type} document against {framework} requirements. The document appears to have some compliance gaps that need attention. Would you like me to generate a fully compliant version for you?"
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error generating document analysis: {e}")
        return f"I've reviewed your {document_type} document. There appear to be some areas that could be improved for {framework} compliance. Would you like me to create a fully compliant version for you?"

def generate_intelligent_compliant_document(document_type: str, framework: str, organization_context: str = "") -> str:
    """Generate a fully compliant document based on the framework and user context."""
    try:
        prompt = f"""
Generate a comprehensive, legally compliant {document_type} document that fully meets {framework} requirements.

Organization Context: {organization_context if organization_context else "General business organization"}
Document Type: {document_type}
Compliance Framework: {framework}

IMPORTANT FORMATTING INSTRUCTIONS:
- Generate ONLY clean, plain text content suitable for a professional legal document
- DO NOT use HTML tags, markdown syntax, or special formatting codes
- Use simple numbered sections (1., 2., 3., etc.) for main headings
- Use lettered subsections (a., b., c., etc.) for subsections when needed
- Use simple dashes (-) for bullet points
- Separate sections with double line breaks
- Use [PLACEHOLDERS] in brackets for items that need customization

The document should include:

1. **Complete Legal Framework Coverage**
   - All mandatory {framework} requirements
   - Appropriate legal language
   - Jurisdiction-specific considerations

2. **Professional Structure**
   - Clear section numbering and headings
   - Logical flow and organization
   - Proper paragraph structure

3. **Comprehensive Content**
   - All required disclosures
   - User rights and obligations
   - Data handling procedures (if applicable)
   - Contact information sections
   - Legal compliance statements

4. **Actionable Implementation**
   - Clear, understandable language
   - Specific procedures and processes
   - Compliance verification methods

5. **Future-Proof Elements**
   - Regulatory change adaptability
   - Update mechanisms
   - Version control considerations

Generate a complete, ready-to-use document that an organization can immediately implement.
Make it professional, legally sound, and fully compliant with {framework} standards.

Use placeholders like [COMPANY NAME], [CONTACT EMAIL], [ADDRESS], [DATE], etc. where customization is needed.

Start with the document title and generate the complete content in plain text format:
"""

        document_content = rate_limited_generate_content(prompt, temperature=0.2)
        
        if not document_content or len(document_content.strip()) < 500:
            # Fallback to template-based generation
            return generate_template_document(document_type, framework)
        
        # Clean any HTML content that might have been generated
        cleaned_content = clean_html_content(document_content)
        
        return cleaned_content
        
    except Exception as e:
        logger.error(f"Error generating compliant document: {e}")
        return generate_template_document(document_type, framework)

def clean_html_content(content: str) -> str:
    """Remove HTML tags and clean up content for DOCX generation."""
    try:
        import re
        
        # Remove HTML tags but preserve content
        content = re.sub(r'<[^>]+>', '', content)
        
        # Convert HTML entities to their text equivalents
        html_entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&apos;': "'",
            '&nbsp;': ' ',
            '&copy;': '©',
            '&reg;': '®',
            '&trade;': '™'
        }
        
        for entity, replacement in html_entities.items():
            content = content.replace(entity, replacement)
        
        # Remove excessive whitespace while preserving document structure
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Max 2 consecutive newlines
        content = re.sub(r'[ \t]+', ' ', content)  # Multiple spaces/tabs to single space
        content = re.sub(r' +\n', '\n', content)  # Remove trailing spaces
        content = re.sub(r'\n +', '\n', content)  # Remove leading spaces after newlines
        
        # Ensure proper line breaks and clean up
        content = content.strip()
        
        return content
        
    except Exception as e:
        logger.error(f"Error cleaning HTML content: {e}")
        return content

def generate_template_document(document_type: str, framework: str) -> str:
    """Generate a template document as fallback."""
    templates = {
        "privacy_policy": {
            "GDPR": """
PRIVACY POLICY

Last Updated: [DATE]

1. INTRODUCTION
[COMPANY NAME] is committed to protecting your personal data in accordance with the General Data Protection Regulation (GDPR).

2. DATA CONTROLLER
[COMPANY NAME]
[ADDRESS]
[CONTACT EMAIL]

3. PERSONAL DATA WE COLLECT
We collect and process the following categories of personal data:
- Identity data
- Contact data
- Technical data
- Usage data

4. LEGAL BASIS FOR PROCESSING
We process your personal data based on:
- Consent
- Contract performance
- Legal obligation
- Legitimate interests

5. YOUR RIGHTS UNDER GDPR
You have the right to:
- Access your personal data
- Rectify inaccurate data
- Erase your data
- Restrict processing
- Data portability
- Object to processing

6. DATA RETENTION
We retain your personal data only for as long as necessary for the purposes outlined in this policy.

7. DATA SECURITY
We implement appropriate technical and organizational measures to protect your personal data.

8. INTERNATIONAL TRANSFERS
Any international transfers of your personal data are conducted with appropriate safeguards in place.

9. CONTACT US
For any questions about this privacy policy or your personal data, please contact us at [CONTACT EMAIL].
            """,
            "CCPA": """
PRIVACY POLICY

Last Updated: [DATE]

CALIFORNIA CONSUMER PRIVACY ACT (CCPA) NOTICE

1. CATEGORIES OF PERSONAL INFORMATION
We collect the following categories of personal information:
- Identifiers
- Commercial information
- Internet activity
- Geolocation data

2. SOURCES OF PERSONAL INFORMATION
We collect personal information from:
- Directly from you
- Automatically through our services
- From third parties

3. BUSINESS PURPOSES
We use personal information for:
- Providing services
- Business operations
- Legal compliance

4. YOUR CALIFORNIA RIGHTS
Under CCPA, you have the right to:
- Know what personal information we collect
- Delete personal information
- Opt-out of sale of personal information
- Non-discrimination for exercising rights

5. HOW TO EXERCISE YOUR RIGHTS
To exercise your rights, contact us at [CONTACT EMAIL] or [PHONE NUMBER].

6. CONTACT INFORMATION
[COMPANY NAME]
[ADDRESS]
[CONTACT EMAIL]
            """
        },
        "terms_conditions": {
            "GDPR": """
TERMS AND CONDITIONS

Last Updated: [DATE]

1. ACCEPTANCE OF TERMS
By using our services, you agree to these terms and our Privacy Policy.

2. SERVICES DESCRIPTION
[COMPANY NAME] provides [DESCRIPTION OF SERVICES].

3. USER OBLIGATIONS
You agree to:
- Use services lawfully
- Provide accurate information
- Respect intellectual property rights

4. DATA PROTECTION
We process your personal data in accordance with GDPR. See our Privacy Policy for details.

5. LIMITATION OF LIABILITY
Our liability is limited to the maximum extent permitted by law.

6. GOVERNING LAW
These terms are governed by [JURISDICTION] law.

7. CONTACT INFORMATION
[COMPANY NAME]
[ADDRESS]
[CONTACT EMAIL]
            """
        }
    }
    
    if document_type in templates and framework in templates[document_type]:
        return templates[document_type][framework]
    else:
        return f"Template {document_type} document for {framework} compliance - Please customize with your specific requirements."

def create_docx_with_download_link(content: str, document_type: str, framework: str, user_id: str) -> Tuple[str, str]:
    """
    Create a DOCX file from content and return the file path and download URL.
    """
    try:
        from docx import Document
        from docx.shared import Inches, Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.style import WD_STYLE_TYPE
        import os
        from datetime import datetime
        import re
        
        # Clean content first
        content = clean_html_content(content)
        
        # Create document
        doc = Document()
        
        # Set up styles
        styles = doc.styles
        
        # Create a style for headings if it doesn't exist
        try:
            heading_style = styles['Heading 1']
        except KeyError:
            heading_style = styles.add_style('Custom Heading 1', WD_STYLE_TYPE.PARAGRAPH)
            heading_style.font.size = Pt(14)
            heading_style.font.bold = True
        
        # Add title
        title_para = doc.add_heading(
            f"{document_type.replace('_', ' ').title()} - {framework} Compliant", 
            level=0
        )
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add subtitle
        subtitle = doc.add_paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y')}")
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add separator line
        doc.add_paragraph("_" * 60).alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()  # Empty line
        
        # Process content line by line for better formatting
        lines = content.split('\n')
        current_list = None
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                # Empty line - add paragraph break
                doc.add_paragraph()
                i += 1
                continue
            
            # Check if it's a main heading (looks like "1. TITLE" or "TITLE" in caps)
            if (re.match(r'^\d+\.\s+[A-Z][A-Z\s]+$', line) or 
                (line.isupper() and len(line) < 80 and not line.startswith('-'))):
                
                # Add as heading
                heading = doc.add_heading(line, level=1)
                current_list = None
                
            # Check if it's a numbered subsection (like "1.1", "a.", etc.)
            elif re.match(r'^[a-z]\.|^\d+\.\d+', line):
                para = doc.add_paragraph(line)
                para.style = 'List Number'
                current_list = None
                
            # Check if it's a bullet point
            elif line.startswith('-') or line.startswith('•'):
                bullet_text = line[1:].strip()  # Remove bullet character
                if current_list is None:
                    current_list = doc.add_paragraph(bullet_text, style='List Bullet')
                else:
                    doc.add_paragraph(bullet_text, style='List Bullet')
                    
            # Regular paragraph
            else:
                para = doc.add_paragraph(line)
                current_list = None
            
            i += 1
        
        # Add footer note
        doc.add_paragraph()
        footer_para = doc.add_paragraph("Note: Please customize all placeholder values (shown in [BRACKETS]) with your specific organizational information before implementing this document.")
        footer_para.style.font.size = Pt(10)
        footer_para.style.font.italic = True
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{document_type}_{framework}_{user_id}_{timestamp}.docx"
        
        # Ensure downloads directory exists
        downloads_dir = Path("downloads")
        downloads_dir.mkdir(exist_ok=True)
        
        file_path = downloads_dir / filename
        
        # Save document
        doc.save(str(file_path))
        
        # Create download URL
        download_url = f"/api/compliance/download/{filename}"
        
        logger.info(f"Created DOCX file: {file_path}")
        
        return str(file_path), download_url
        
    except Exception as e:
        logger.error(f"Error creating DOCX file: {e}")
        
        # Fallback: create a simple text file
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{document_type}_{framework}_{user_id}_{timestamp}.txt"
            downloads_dir = Path("downloads")
            downloads_dir.mkdir(exist_ok=True)
            file_path = downloads_dir / filename
            
            # Clean content for text file
            clean_content = clean_html_content(content)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"{document_type.replace('_', ' ').title()} - {framework} Compliant\n")
                f.write(f"Generated on: {datetime.now().strftime('%B %d, %Y')}\n")
                f.write("=" * 60 + "\n\n")
                f.write(clean_content)
                f.write("\n\n" + "=" * 60 + "\n")
                f.write("Note: Please customize all placeholder values (shown in [BRACKETS]) with your specific organizational information.")
            
            download_url = f"/api/compliance/download/{filename}"
            return str(file_path), download_url
            
        except Exception as e2:
            logger.error(f"Error creating fallback text file: {e2}")
            return None, None

def format_document_response_with_download(content: str, download_url: str, document_type: str, framework: str) -> str:
    """Format the response with document content and download link."""
    
    response = f"""## ✅ {document_type.replace('_', ' ').title()} Generated Successfully!

I've created a comprehensive {framework}-compliant {document_type.replace('_', ' ')} document for you.

### 📋 Document Preview:
{content[:800]}{"..." if len(content) > 800 else ""}

### 📥 Download Your Document
**[Click here to download your {document_type.replace('_', ' ')} document]({download_url})**

The document includes:
- ✅ Full {framework} compliance requirements
- ✅ Professional legal language
- ✅ Ready-to-use format with placeholders
- ✅ Comprehensive coverage of all necessary sections

### 🔧 Customization Required:
Please customize the document by replacing placeholders like:
- [COMPANY NAME] - Your organization name
- [CONTACT EMAIL] - Your contact email
- [ADDRESS] - Your business address
- [DATE] - Current date

### 📋 Next Steps:
1. Download the document using the link above
2. Review and customize the placeholders
3. Have your legal team review if needed
4. Implement in your organization

Would you like me to create any additional compliance documents or help you with specific sections?"""

    return response

def generate_document_improvement_suggestions(document_text: str, framework: str, document_type: str) -> str:
    """Generate specific improvement suggestions for an uploaded document without creating a new document."""
    try:
        prompt = f"""
Analyze this {document_type} document and provide specific, actionable improvement suggestions for {framework} compliance.

Document Content (first 3000 characters):
{document_text[:3000]}

Provide improvement suggestions in the following format:

## 📋 Document Improvement Recommendations

### 🔍 Quick Assessment
- **Current Compliance Level**: [Estimate percentage]
- **Framework**: {framework}
- **Priority Issues**: [Number] critical issues found

### 🚨 Critical Issues to Fix Immediately

1. **[Issue Title]**
   - **Problem**: What's missing or incorrect
   - **Impact**: Why this matters for compliance
   - **Fix**: Specific action to take
   - **Example Language**: "Suggested text to add..."

2. **[Next Issue]**
   - [Continue pattern...]

### ⚠️ Important Improvements

1. **[Issue Title]**
   - **Current**: What the document currently says
   - **Improve To**: What it should say instead
   - **Reason**: Why this change is needed

### ✨ Best Practice Enhancements

1. **[Enhancement Title]**
   - **Suggestion**: What to add or improve
   - **Benefit**: How this helps compliance

### 📝 Specific Language Suggestions

**Section: [Name]**
- **Current**: "[Existing text]"
- **Suggested**: "[Improved text]"
- **Why**: [Explanation]

### 🎯 Next Steps Priority Order

1. **Immediate (This Week)**:
   - [Action items]

2. **Short-term (This Month)**:
   - [Action items]

3. **Ongoing (Regular Review)**:
   - [Action items]

### 📚 Additional Resources
- Consider reviewing [specific standards/guidelines]
- Regular compliance audits recommended

Focus on providing specific, actionable advice rather than generating new content.
"""

        suggestions = rate_limited_generate_content(prompt, temperature=0.2)
        
        if not suggestions or len(suggestions.strip()) < 100:
            return f"""## 📋 Document Improvement Recommendations

I've reviewed your {document_type.replace('_', ' ')} document against {framework} requirements.

### 🔍 Quick Assessment
- **Framework**: {framework}
- **Review Status**: Completed

### 🚨 Key Areas for Improvement

1. **Legal Language Precision**
   - **Issue**: Some sections may need more specific legal language
   - **Action**: Review with legal counsel for framework-specific requirements

2. **Compliance Completeness**
   - **Issue**: Ensure all {framework} requirements are explicitly addressed
   - **Action**: Cross-reference against official {framework} checklist

3. **User Rights Clarity**
   - **Issue**: User rights section may need more detail
   - **Action**: Add specific procedures for users to exercise their rights

### 📝 General Recommendations
- Consider regular compliance reviews
- Ensure all stakeholders review the updated document
- Implement a document version control system

Would you like me to analyze any specific section in more detail?"""
        
        return suggestions
        
    except Exception as e:
        logger.error(f"Error generating improvement suggestions: {e}")
        return f"""## 📋 Document Improvement Recommendations

I've reviewed your {document_type.replace('_', ' ')} document for {framework} compliance.

### 🔍 General Improvement Areas

1. **Framework Alignment**: Ensure all {framework} requirements are explicitly addressed
2. **Legal Language**: Review language for clarity and legal precision
3. **User Rights**: Clearly outline user rights and how to exercise them
4. **Data Handling**: Provide detailed information about data collection and processing
5. **Contact Information**: Ensure all contact details are current and accessible

### 📝 Next Steps
1. Review each section against the {framework} checklist
2. Consider legal review of updated language
3. Regular compliance audits and updates

Would you like me to focus on any specific aspect of your document?"""

# Add in-memory embedding cache for better performance
EMBEDDING_MEMORY_CACHE = {}
EMBEDDING_CACHE_MAX_SIZE = 1000

@timing_decorator
def get_embedding_optimized(text: str) -> np.ndarray:
    """Get embeddings with aggressive in-memory caching."""
    # Normalize text for consistent caching
    text_normalized = text.strip().lower()
    text_hash = hash_text(text_normalized)
    
    # Check in-memory cache first
    if text_hash in EMBEDDING_MEMORY_CACHE:
        return EMBEDDING_MEMORY_CACHE[text_hash]
    
    # Truncate very long text for performance
    if len(text.split()) > 500:  # Reduced from 8000 for speed
        text = " ".join(text.split()[:500])
    
    try:
        embeddings = embedding_model.encode([text], convert_to_numpy=True, show_progress_bar=False)
        result = embeddings[0]
        
        # Cache in memory
        if len(EMBEDDING_MEMORY_CACHE) >= EMBEDDING_CACHE_MAX_SIZE:
            # Remove oldest entries (simple FIFO)
            oldest_key = next(iter(EMBEDDING_MEMORY_CACHE))
            del EMBEDDING_MEMORY_CACHE[oldest_key]
        
        EMBEDDING_MEMORY_CACHE[text_hash] = result
        return result
        
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None

def detect_informational_query(query: str) -> bool:
    """Detect if this is a simple informational query that needs a concise response."""
    query_lower = query.lower()
    
    # Simple informational patterns
    informational_patterns = [
        "what is", "what are", "tell me about", "explain", "define",
        "definition of", "meaning of", "overview of", "introduction to"
    ]
    
    # Framework/standard specific patterns
    framework_patterns = [
        "iso 27001", "gdpr", "ccpa", "hipaa", "soc 2", "nist",
        "pci dss", "sox", "compliance framework"
    ]
    
    # Check if it's a simple "what is [framework]" type query
    is_informational = any(pattern in query_lower for pattern in informational_patterns)
    mentions_framework = any(pattern in query_lower for pattern in framework_patterns)
    
    # Look for list requests (top 10, main, key, primary)
    is_list_request = any(word in query_lower for word in [
        "top", "main", "key", "primary", "important", "rules", "requirements",
        "principles", "controls", "steps"
    ])
    
    return is_informational and mentions_framework and is_list_request

def generate_concise_informational_response(query: str) -> str:
    """Generate a concise, informational response for simple queries."""
    try:
        # Extract the framework/topic
        query_lower = query.lower()
        framework = "ISO 27001"  # Default
        
        if "gdpr" in query_lower:
            framework = "GDPR"
        elif "ccpa" in query_lower:
            framework = "CCPA"
        elif "hipaa" in query_lower:
            framework = "HIPAA"
        elif "soc 2" in query_lower or "soc2" in query_lower:
            framework = "SOC 2"
        elif "nist" in query_lower:
            framework = "NIST"
        elif "pci" in query_lower:
            framework = "PCI DSS"
        
        # Check if user wants concise response
        is_concise = detect_concise_request(query)
        max_tokens = 512 if is_concise else 800
        
        if is_concise:
            # Generate a very brief response
            prompt = f"""
Provide a CONCISE answer to: "{query}"

Format as:
**{framework} Compliance - Key Steps:**
• Step 1
• Step 2  
• Step 3
• Step 4
• Step 5

Keep under 100 words total. Focus only on essential actions.
"""
        else:
            # Generate a focused, concise response (original logic)
            prompt = f"""
Provide a clear, concise response to this query: "{query}"

Structure your response as follows:
1. **Brief Definition** (2-3 sentences about what {framework} is)
2. **Top 10 Key Points/Rules/Requirements** (numbered list with brief explanations)
3. **Quick Implementation Tip** (1-2 sentences)

Keep it informative but concise - aim for 300-500 words total.
Use clear, professional language that's accessible to both beginners and experts.
Focus on practical, actionable information.
"""
        
        return rate_limited_generate_content_optimized(prompt, max_tokens=max_tokens)
        
    except Exception as e:
        logger.error(f"Error generating concise response: {e}")
        return "I'd be happy to help with information about compliance frameworks. Could you please rephrase your question?"

def validate_query_input(query: str) -> Tuple[bool, str]:
    """
    Validate user query input to ensure it's meaningful and processable.
    Returns (is_valid, error_message)
    """
    if not query:
        return False, "Please enter a question or request."
    
    # Strip whitespace
    query_stripped = query.strip()
    
    if not query_stripped:
        return False, "Please enter a question or request."
    
    # Check minimum length
    if len(query_stripped) < 3:
        return False, "Please enter a more specific question."
    
    # Check if query contains only special characters or numbers
    import re
    if re.match(r'^[^a-zA-Z]*$', query_stripped):
        return False, "Please enter a question using words."
    
    # Check for only repeated characters
    if len(set(query_stripped.lower())) <= 2:
        return False, "Please enter a meaningful question."
    
    # Check for test inputs
    test_patterns = [
        r'^test+$', r'^hello+$', r'^hi+$', r'^\.+$', r'^\?+$', 
        r'^!+$', r'^@+$', r'^#+$', r'^\$+$', r'^%+$', r'^\^+$',
        r'^&+$', r'^\*+$', r'^\(+$', r'^\)+$', r'^-+$', r'^_+$',
        r'^=+$', r'^\++$', r'^\[+$', r'^\]+$', r'^\{+$', r'^\}+$',
        r'^\\+$', r'^\|+$', r'^;+$', r'^:+$', r'^"+$', r"^'+$",
        r'^<+$', r'^>+$', r'^,+$', r'^\.+$', r'^/+$', r'^\s*$'
    ]
    
    for pattern in test_patterns:
        if re.match(pattern, query_stripped.lower()):
            return False, "Please enter a meaningful compliance-related question."
    
    # Check for minimum word count
    words = query_stripped.split()
    if len(words) < 2:
        return False, "Please enter a more detailed question."
    
    return True, ""

def detect_conversation_history_query(query: str) -> bool:
    """Detect if user is asking about previous conversation."""
    # More specific patterns to avoid false positives
    specific_history_patterns = [
        "what did we talk about before",
        "what did we talk about earlier", 
        "what was our last conversation",
        "what was our previous conversation",
        "what did we discuss before",
        "what did we discuss earlier",
        "our chat history",
        "previous chat",
        "last conversation",
        "continue our conversation",
        "where did we leave off",
        "what were we discussing",
        "remind me what we talked about"
    ]
    
    query_lower = query.lower().strip()
    
    # Exact matches for specific patterns
    for pattern in specific_history_patterns:
        if pattern in query_lower:
            return True
    
    # Additional check for very short history queries
    if len(query_lower.split()) <= 6:  # Short queries only
        history_keywords = ["before", "earlier", "last time", "previous"]
        if any(keyword in query_lower for keyword in history_keywords):
            # Make sure it's actually about conversation
            conversation_words = ["talk", "discuss", "chat", "conversation", "said", "spoke"]
            if any(word in query_lower for word in conversation_words):
                return True
    
    return False

def handle_conversation_history_query(conversation: 'ConversationHistory') -> str:
    """Handle queries about conversation history."""
    if not conversation or not conversation.history:
        return """I don't have any record of previous conversations in this session. This appears to be a new conversation.

If you're looking for help with compliance topics, I'd be happy to assist with:
• GDPR, CCPA, HIPAA compliance
• Security frameworks (ISO 27001, SOC 2, NIST)
• Privacy policy development
• Risk assessments and audits

What specific compliance topic would you like to discuss?"""
    
    # If there is history, provide a summary
    context = conversation.get_context(compact=True)
    return f"""Here's a summary of our previous conversation:

{context}

What would you like to continue discussing or explore further?"""

def rate_limited_generate_content(prompt: str, temperature: float = 0.1, max_tokens: int = 3200, max_retries: int = 3) -> str:
    """Generate content with rate limiting and retries."""
    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens
                }
            )
            return response.text
        except Exception as e:
            if attempt == max_retries - 1:
                break
            time.sleep(1)  # Wait before retrying
    # Fallback to Ollama
    ollama_text = _generate_via_ollama(prompt, temperature=temperature, max_tokens=max_tokens)
    if ollama_text:
        return ollama_text
    return ""

def analyze_query_intent_with_ai(query: str) -> Dict[str, Any]:
    """Analyze query intent using AI."""
    try:
        prompt = f"""Analyze the following query and determine its intent:
        Query: {query}
        
        Return a JSON object with the following fields:
        - intent: The main intent of the query (e.g., 'GENERAL_COMPLIANCE', 'SPECIFIC_REQUIREMENT', 'DOCUMENT_ANALYSIS')
        - document_type: The type of document being referenced (if any)
        - framework: The compliance framework being discussed (if any)
        - urgency: The urgency level ('low', 'medium', 'high')
        - confidence: A float between 0 and 1 indicating confidence in the analysis
        - reasoning: Brief explanation of the analysis
        """
        
        response = rate_limited_generate_content(prompt)
        return json.loads(response)
    except Exception as e:
        logger.warning(f"AI classification failed: {str(e)}")
        return {
            'intent': 'GENERAL_COMPLIANCE',
            'document_type': 'unknown',
            'framework': 'general',
            'urgency': 'medium',
            'confidence': 0.0,
            'reasoning': f'Default classification due to error: {str(e)}'
        }

if __name__ == "__main__":
    main() 