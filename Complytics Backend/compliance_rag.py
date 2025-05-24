import os
import json
import logging
import time
import faiss
import google.generativeai as genai
import pdfplumber
import numpy as np
import pickle
import xml.etree.ElementTree as ET
import csv
import re
from bert_score import score as bert_score_fn
from transformers import pipeline, AutoTokenizer
from typing import List, Dict, Any, Tuple, Optional, AsyncIterator
import pandas as pd
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
GOOGLE_API_KEY = "AIzaSyAF5hhERrZXTudmLVJkjmTgMxPH2h5PWtI"
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize the embedding model
logger.info("Initializing embedding model...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Directory structure for embeddings and indexes
EMBEDDING_DIR = "embeddings"
INDEX_DIR = "faiss_indexes"
CACHE_DIR = "compliance_cache"
PDF_FOLDER = "compliance_frameworks"
TEST_DATA_FILE = "testingData.json"

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
    "max_output_tokens": 2048,
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

# Rate limiting configuration
CALLS_PER_MINUTE = 20  # Reduced from 30 to be safer
DELAY_BETWEEN_CALLS = 3  # Seconds between API calls
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

def wait_for_rate_limit():
    """Ensure we don't exceed API rate limits."""
    global last_call_time
    current_time = time.time()
    time_since_last_call = current_time - last_call_time
    if time_since_last_call < DELAY_BETWEEN_CALLS:
        sleep_time = DELAY_BETWEEN_CALLS - time_since_last_call
        time.sleep(sleep_time)
    last_call_time = time.time()

@sleep_and_retry
@limits(calls=CALLS_PER_MINUTE, period=60)
@timing_decorator
def rate_limited_generate_content(prompt: str, temperature: float = 0.1) -> str:
    """Rate-limited version of Gemini's generate_content with caching and error handling."""
    # Check cache first using hash of prompt
    prompt_hash = hash_text(prompt)
    cache_key = f"gemini:{prompt_hash}:{temperature}"
    
    if cache_key in QUERY_CACHE:
        logger.info("Cache hit for Gemini API call")
        return QUERY_CACHE[cache_key]
    
    wait_for_rate_limit()  # Ensure minimum delay between calls
    
    # Implement exponential backoff
    max_retries = 5
    base_delay = 3
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                prompt,
                generation_config={"temperature": temperature}
            )
            result = response.text.strip()
            
            # Cache the result
            QUERY_CACHE[cache_key] = result
            
            # Periodically save the cache (every 5 new entries)
            if len(QUERY_CACHE) % 5 == 0:
                save_query_cache()
                
            return result
        except Exception as e:
            if "429" in str(e):
                retry_delay = base_delay * (2 ** attempt)
                logger.info(f"Rate limit exceeded, retrying in {retry_delay} seconds... (Attempt {attempt+1}/{max_retries})")
                time.sleep(retry_delay)
                if attempt == max_retries - 1:
                    logger.info("Maximum retries reached. Returning empty string.")
                    return ""
            else:
                logger.error(f"Error generating content: {e}")
                return ""

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
    """Build and save FAISS index."""
    try:
        dimension = embeddings.shape[1]
        
        # For small datasets (under 1M vectors), use a combination of IVF and flat index
        # This provides a good balance between speed and accuracy
        n_vectors = embeddings.shape[0]
        n_clusters = min(int(np.sqrt(n_vectors) * 4), n_vectors // 10)  # Rule of thumb
        n_clusters = max(n_clusters, 8)  # Ensure minimum number of clusters
        
        logger.info(f"Building IVF index with {n_clusters} clusters")
        
        # Create quantizer and index
        quantizer = faiss.IndexFlatL2(dimension)
        index = faiss.IndexIVFFlat(quantizer, dimension, n_clusters)
        
        # Train the index
        # Set to True to enable faster (but potentially less accurate) search
        index.nprobe = min(n_clusters // 4, 4)  # Number of clusters to visit during search
        
        # Need to train the index before adding vectors
        logger.info("Training IVF index...")
        index.train(embeddings)
        
        # Add vectors to the index
        index.add(embeddings)
        
        faiss.write_index(index, FAISS_INDEX_FILE)
        logger.info(f"Saved FAISS IVF index with {index.ntotal} vectors")
        return index
    except Exception as e:
        logger.error(f"Error building FAISS index: {e}")
        # Fall back to simple flat index if IVF fails
        try:
            index = faiss.IndexFlatL2(embeddings.shape[1])
            index.add(embeddings)
            faiss.write_index(index, FAISS_INDEX_FILE)
            logger.info(f"Saved FAISS flat index with {index.ntotal} vectors")
            return index
        except Exception as e2:
            logger.error(f"Error building fallback index: {e2}")
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

@timing_decorator
def expert_security_controls(query: str, context: str, conversation_context: str = "") -> str:
    """Expert analysis for security controls."""
    prompt = (
        "As a security controls expert, analyze the following query:\n\n"
        f"{conversation_context}"
        f"Query: {query}\n"
        f"Context: {context}\n"
        "Focus on:\n"
        "1. Relevant security controls and requirements\n"
        "2. Implementation guidelines\n"
        "3. Control objectives and success criteria\n"
        "4. Monitoring and validation methods\n"
        "Chain-of-Thought Analysis:"
    )
    return rate_limited_generate_content(prompt)

@timing_decorator
def expert_privacy_regulations(query: str, context: str, conversation_context: str = "") -> str:
    """Expert analysis for privacy regulations."""
    prompt = (
        "As a privacy regulations expert, analyze the following query:\n\n"
        f"{conversation_context}"
        f"Query: {query}\n"
        f"Context: {context}\n"
        "Focus on:\n"
        "1. Privacy requirements and regulations\n"
        "2. Data protection measures\n"
        "3. User rights and consent\n"
        "4. Compliance documentation\n"
        "Chain-of-Thought Analysis:"
    )
    return rate_limited_generate_content(prompt)

@timing_decorator
def expert_audit_compliance(query: str, context: str, conversation_context: str = "") -> str:
    """Expert analysis for audit compliance."""
    prompt = (
        "As an audit compliance expert, analyze the following query:\n\n"
        f"{conversation_context}"
        f"Query: {query}\n" ##<query>what is gdpr? </query>
        f"Context: {context}\n"
        "Focus on:\n"
        "1. Audit requirements and procedures\n"
        "2. Evidence collection and documentation\n"
        "3. Compliance verification methods\n"
        "4. Risk assessment and mitigation\n"
        "Chain-of-Thought Analysis:"
    )
    return rate_limited_generate_content(prompt)

@timing_decorator
def aggregate_expert_outputs(outputs: List[str], query: str, context: str) -> str:
    """Aggregate and synthesize expert outputs."""
    prompt = (
        "Synthesize the following expert analyses into a comprehensive response:\n\n"
        f"Query: {query}\n"
        f"Context: {context}\n"
        "Expert Analyses:\n" + "\n---\n".join(outputs) + "\n\n"
        "Synthesized Response:"
    )
    return rate_limited_generate_content(prompt)

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
        self.history = []
        self.last_update_time = time.time()
        self.context_embedding = None
        self.last_compliance_status = True

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
    response = rate_limited_generate_content(prompt)
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

        response = rate_limited_generate_content(prompt, temperature=0.8)  # Higher temperature for more variety
        
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

# Add function to dynamically select relevant experts based on query content
@timing_decorator
def select_relevant_experts(query: str) -> List[str]:
    """Optimized expert selection with pre-filtering"""
    # Pre-filter using keyword matching
    keywords = {
        'security': [
            'security', 'protection', 'breach', 'risk', 'access', 'safeguard',
            'azure', 'azure ad', 'azure active directory', 'entra', 'active directory',
            'identity', 'authentication', 'authorization', 'access control',
            'identity management', 'sso', 'single sign-on', 'mfa', 'multi-factor',
            'conditional access', 'firewall', 'encryption', 'vulnerability',
            'threat', 'cybersecurity', 'information security', 'network security',
            'endpoint', 'certificate', 'ssl', 'tls', 'malware', 'antivirus'
        ],
        'privacy': [
            'privacy', 'data', 'personal', 'gdpr', 'ccpa', 'information',
            'data protection', 'data privacy', 'consent', 'data subject',
            'personal information', 'pii', 'phi', 'data processing',
            'data retention', 'data deletion', 'right to be forgotten'
        ],
        'audit': [
            'audit', 'certification', 'compliance', 'framework', 'financial', 'standard',
            'iso', 'soc', 'nist', 'pci', 'requirement', 'control', 'governance',
            'risk management', 'assessment', 'monitoring', 'reporting',
            'business continuity', 'vendor management', 'third party'
        ]
    }
    
    matched_experts = set()
    query_lower = query.lower()
    
    # First try keyword matching
    for expert, expert_keywords in keywords.items():
        if any(keyword in query_lower for keyword in expert_keywords):
            matched_experts.add(expert)
    
    # If keyword matching found experts, use them
    if matched_experts:
        logger.info(f"Selected experts based on keywords: {', '.join(matched_experts)}")
        return list(matched_experts)
    
    # Fall back to AI selection only if needed
    prompt = (
        "Based on this compliance query, select needed experts from ['security', 'privacy', 'audit']. Return ONLY a comma-separated list.\n\n"
        f"Query: {query}\n"
        "Experts:"
    )
    response = rate_limited_generate_content(prompt)
    selected = [expert.strip().lower() for expert in response.split(',') if expert.strip() in ['security', 'privacy', 'audit']]
    
    # Default to audit if no experts were selected
    if not selected:
        selected = ['audit']
    
    logger.info(f"Selected experts using AI: {', '.join(selected)}")
    return selected

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
def is_compliance_related(query: str, conversation_context: str = "") -> Tuple[bool, str]:
    """
    Intelligent compliance query classification using multiple analysis layers.
    
    Args:
        query (str): The user's query
        conversation_context (str): The conversation context to help determine relevance
        
    Returns:
        Tuple[bool, str]: (is_compliance_related, reason)
    """
    
    # Layer 1: Quick keyword screening for obviously non-compliant topics
    sensitive_topics = [
        "sex", "sexual", "porn", "pornography", "nude", "nudity",
        "drug", "drugs", "weapon", "weapons", "violence", "violent",
        "suicide", "self-harm", "personal health", "medical advice",
        "cooking", "recipe", "sports", "football", "cricket", "entertainment",
        "movie", "film", "music", "celebrity", "gossip", "dating", "relationship"
    ]
    
    query_lower = query.lower()
    for topic in sensitive_topics:
        if topic in query_lower:
            # Check if it's used in a professional/compliance context
            professional_context = [
                "compliance", "policy", "regulation", "standard", "framework",
                "business", "organization", "company", "workplace", "professional"
            ]
            if not any(context in query_lower for context in professional_context):
                return False, f"Query appears to be about non-compliance topic: {topic}"
    
    # Layer 2: Semantic similarity analysis using embeddings
    compliance_relevance_score = 0.0
    document_relevance_score = 0.0
    context_score = 0.0
    
    try:
        compliance_relevance_score = analyze_semantic_compliance_relevance(query, conversation_context)
        if compliance_relevance_score > 0.7:
            return True, f"High semantic similarity to compliance topics (score: {compliance_relevance_score:.2f})"
        elif compliance_relevance_score > 0.4:
            # Continue to next layers for borderline cases
            pass
        else:
            # Low similarity, but still check other layers
            pass
    except Exception as e:
        logger.warning(f"Semantic analysis failed: {e}")
    
    # Layer 3: Document relevance analysis
    try:
        document_relevance_score = analyze_document_relevance(query)
        if document_relevance_score > 0.6:
            return True, f"Query highly relevant to uploaded compliance documents (score: {document_relevance_score:.2f})"
    except Exception as e:
        logger.warning(f"Document relevance analysis failed: {e}")
    
    # Layer 4: Context-aware analysis
    context_score = analyze_conversation_context(query, conversation_context)
    if context_score > 0.6:
        return True, f"Query relevant in current conversation context (score: {context_score:.2f})"
    
    # Layer 4.5: Historical learning analysis
    try:
        historical_score, historical_reason = get_historical_classification_patterns(query)
        if historical_score > 0.7:
            return True, f"Historical patterns indicate compliance relevance: {historical_reason}"
    except Exception as e:
        logger.warning(f"Historical analysis failed: {e}")
    
    # Layer 5: AI-powered intent analysis with domain knowledge
    try:
        ai_classification, confidence = analyze_query_intent_with_ai(query, conversation_context)
        if ai_classification and confidence > 0.7:
            return True, f"AI analysis indicates compliance relevance (confidence: {confidence:.2f})"
        elif ai_classification and confidence > 0.4:
            # Borderline case - use combined score
            combined_score = (
                compliance_relevance_score * 0.3 + 
                document_relevance_score * 0.3 + 
                context_score * 0.2 + 
                confidence * 0.2
            )
            if combined_score > 0.5:
                return True, f"Combined analysis indicates compliance relevance (score: {combined_score:.2f})"
    except Exception as e:
        logger.warning(f"AI intent analysis failed: {e}")
    
    # Layer 6: Fallback keyword analysis (refined)
    business_technical_keywords = [
        "azure", "aws", "cloud", "security", "identity", "authentication",
        "database", "network", "infrastructure", "application", "system",
        "governance", "risk", "management", "process", "procedure",
        "organization", "business", "company", "enterprise", "corporate"
    ]
    
    if any(keyword in query_lower for keyword in business_technical_keywords):
        return True, f"Query contains business/technical terms relevant to compliance"
    
    return False, "Query does not appear to be compliance-related based on comprehensive analysis"

def analyze_semantic_compliance_relevance(query: str, conversation_context: str = "") -> float:
    """Analyze semantic similarity to known compliance topics using embeddings."""
    try:
        # Define compliance topic templates
        compliance_topics = [
            "data protection and privacy regulations",
            "security controls and risk management",
            "audit compliance and certification",
            "business process compliance",
            "regulatory requirements and standards",
            "information security management",
            "identity and access management",
            "cloud security and compliance",
            "vendor and third-party risk management",
            "incident response and business continuity"
        ]
        
        # Get query embedding
        query_embedding = get_embedding(query)
        if query_embedding is None:
            return 0.0
        
        # Get embeddings for compliance topics
        topic_embeddings = []
        for topic in compliance_topics:
            topic_embedding = get_embedding(topic)
            if topic_embedding is not None:
                topic_embeddings.append(topic_embedding)
        
        if not topic_embeddings:
            return 0.0
        
        # Calculate maximum similarity
        topic_embeddings = np.array(topic_embeddings)
        similarities = cosine_similarity([query_embedding], topic_embeddings)[0]
        max_similarity = np.max(similarities)
        
        # Consider conversation context
        if conversation_context:
            context_embedding = get_embedding(conversation_context)
            if context_embedding is not None:
                context_similarities = cosine_similarity([context_embedding], topic_embeddings)[0]
                context_boost = np.max(context_similarities) * 0.3
                max_similarity = min(1.0, max_similarity + context_boost)
        
        return float(max_similarity)
        
    except Exception as e:
        logger.error(f"Error in semantic analysis: {e}")
        return 0.0

def analyze_document_relevance(query: str) -> float:
    """Analyze how relevant the query is to uploaded compliance documents."""
    try:
        # Load existing embeddings and segments
        cached_embeddings, cached_doc_map = load_embeddings()
        if cached_embeddings is None or cached_doc_map is None:
            return 0.0
        
        # Get query embedding
        query_embedding = get_embedding(query)
        if query_embedding is None:
            return 0.0
        
        # Load FAISS index
        index = load_faiss_index()
        if index is None:
            return 0.0
        
        # Search for similar content in documents
        query_embedding = np.expand_dims(query_embedding, axis=0)
        distances, idxs = index.search(query_embedding, k=5)
        
        # Calculate relevance score based on similarity to document content
        # Convert distances to similarities (FAISS L2 distance)
        similarities = 1 / (1 + distances[0])  # Convert distance to similarity
        avg_similarity = np.mean(similarities)
        
        # Boost score if multiple relevant segments found
        consistency_boost = min(0.2, len([s for s in similarities if s > 0.3]) * 0.05)
        
        return min(1.0, avg_similarity + consistency_boost)
        
    except Exception as e:
        logger.error(f"Error in document relevance analysis: {e}")
        return 0.0

def analyze_conversation_context(query: str, conversation_context: str) -> float:
    """Analyze query relevance based on conversation context."""
    try:
        if not conversation_context:
            return 0.0
        
        # Check for document upload context
        upload_indicators = ["document", "upload", "file", "pdf", "docx"]
        if any(indicator in conversation_context.lower() for indicator in upload_indicators):
            document_query_indicators = [
                "what", "show", "tell", "explain", "describe", "summarize",
                "content", "contains", "about", "regarding", "concerning"
            ]
            if any(indicator in query.lower() for indicator in document_query_indicators):
                return 0.8
        
        # Check for compliance topic continuation
        compliance_context_indicators = [
            "compliance", "regulation", "framework", "standard", "policy",
            "security", "privacy", "audit", "risk", "governance"
        ]
        
        context_compliance_score = sum(1 for indicator in compliance_context_indicators 
                                     if indicator in conversation_context.lower()) / len(compliance_context_indicators)
        
        if context_compliance_score > 0.1:
            # Query likely continuing a compliance discussion
            return min(0.7, context_compliance_score * 2)
        
        return 0.0
        
    except Exception as e:
        logger.error(f"Error in context analysis: {e}")
        return 0.0

def analyze_query_intent_with_ai(query: str, conversation_context: str = "") -> Tuple[bool, float]:
    """Use AI to analyze query intent with domain knowledge."""
    try:
        prompt = f"""
Analyze if this query is related to business compliance, security, governance, or regulatory requirements.

Consider these aspects:
1. Is it about technology used in business/compliance contexts (like Azure AD, cloud services)?
2. Is it about business processes, policies, or procedures?
3. Is it about security, privacy, or risk management?
4. Is it about regulatory frameworks or standards?
5. Is it about organizational governance or management?
6. Could it be relevant to compliance professionals?

Query: "{query}"
Context: "{conversation_context}"

Think step by step:
1. What is the user asking about?
2. Is this topic relevant to business compliance or security?
3. Would a compliance professional need to know about this?

Respond with:
- "COMPLIANT" if it's compliance-related
- "NON_COMPLIANT" if it's clearly not compliance-related
- "BORDERLINE" if it could be either depending on context

Also provide a confidence score from 0.0 to 1.0.

Format: [CLASSIFICATION]|[CONFIDENCE_SCORE]|[BRIEF_REASON]
"""
        
        response = rate_limited_generate_content(prompt, temperature=0.1)
        
        # Parse response
        parts = response.split('|')
        if len(parts) >= 2:
            classification = parts[0].strip().upper()
            try:
                confidence = float(parts[1].strip())
            except:
                confidence = 0.5
            
            is_compliant = classification in ["COMPLIANT", "BORDERLINE"]
            
            # Adjust confidence for borderline cases
            if classification == "BORDERLINE":
                confidence *= 0.7  # Reduce confidence for uncertain cases
            
            return is_compliant, confidence
        
        return False, 0.0
        
    except Exception as e:
        logger.error(f"Error in AI intent analysis: {e}")
        return False, 0.0

@timing_decorator
def detect_query_type(query: str, conversation_context: str = "") -> Tuple[str, List[str]]:
    """
    Detect the type of compliance query and required experts.
    
    Args:
        query (str): The user's query
        conversation_context (str): The conversation context to help determine query type
        
    Returns:
        Tuple[str, List[str]]: (query_type, required_experts)
    """
    # Define query types and their associated keywords
    query_types = {
        'framework_selection': ['framework', 'standard', 'regulation', 'compliance', 'certification'],
        'security': ['security', 'protection', 'breach', 'risk', 'access', 'safeguard'],
        'privacy': ['privacy', 'data', 'personal', 'gdpr', 'ccpa', 'information'],
        'audit': ['audit', 'certification', 'compliance', 'framework', 'financial', 'standard']
    }
    
    # Check for framework selection queries first
    if any(keyword in query.lower() for keyword in query_types['framework_selection']):
        return 'framework_selection', ['audit']
    
    # Determine required experts based on query content
    required_experts = []
    for expert_type, keywords in query_types.items():
        if any(keyword in query.lower() for keyword in keywords):
            if expert_type == 'security':
                required_experts.append('security')
            elif expert_type == 'privacy':
                required_experts.append('privacy')
            elif expert_type == 'audit':
                required_experts.append('audit')
    
    # Check conversation context for additional context
    if conversation_context:
        context_lower = conversation_context.lower()
        # If context contains privacy-related terms and query is about implementation
        if any(term in context_lower for term in ['gdpr', 'privacy', 'data protection']):
            implementation_terms = ['implement', 'implementation', 'apply', 'use', 'adopt', 'deploy']
            if any(term in query.lower() for term in implementation_terms):
                if 'privacy' not in required_experts:
                    required_experts.append('privacy')
                if 'audit' not in required_experts:
                    required_experts.append('audit')
    
    # Default to audit if no specific experts identified
    if not required_experts:
        required_experts = ['audit']
    
    return 'general', required_experts

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

async def process_query(query: str, context: str, conversation_context: str) -> Tuple[str, float]:
    """Process a query with optimized response generation"""
    start_time = time.time()
    
    # First check if this is a compliance-related query
    is_compliance, reason = is_compliance_related(query, conversation_context)
    
    if not is_compliance:
        # For non-compliance queries, return a simple, direct response
        response = generate_non_compliance_response(query)
        end_time = time.time()
        return response, end_time - start_time
    
    # Only proceed with compliance-related queries
    query_type, required_experts = detect_query_type(query, conversation_context)
    
    # Check for cached similar response - only for compliance queries
    cache_key = f"compliance:{hash_text(query)}"
    if cache_key in QUERY_CACHE:
        cached_data = QUERY_CACHE[cache_key]
        if isinstance(cached_data, dict) and 'response' in cached_data:
            end_time = time.time()
            return cached_data['response'], end_time - start_time
    
    # For framework selection queries, use specialized handler
    if query_type == 'framework_selection':
        response, processing_time = get_framework_recommendation(query)
        return response, processing_time
    
    # For other queries, use progressive response generation
    responses = []
    async for partial_response in get_progressive_response(query, required_experts, context, conversation_context):
        responses.append(partial_response)
    
    # Get final aggregated response
    final_response = responses[-1] if responses else ""
    
    # Cache the response with query embedding - only for compliance queries
    if final_response:
        query_embedding = get_embedding(query)
        QUERY_CACHE[cache_key] = {
            'response': final_response,
            'embedding': query_embedding,
            'topic': query_type,
            'timestamp': datetime.now().isoformat(),
            'is_compliance': True
        }
        save_query_cache()
    
    end_time = time.time()
    return final_response, end_time - start_time

def clear_query_cache():
    """Clear all cache-related data"""
    global QUERY_CACHE
    QUERY_CACHE = {}
    
    # Clear the file-based cache
    if os.path.exists(QUERY_CACHE_FILE):
        try:
            os.remove(QUERY_CACHE_FILE)
            logger.info("Query cache file removed")
        except Exception as e:
            logger.error(f"Error removing query cache file: {e}")
    
    # Clear the embedding cache
    get_cached_embedding.cache_clear()
    logger.info("Embedding cache cleared")
    
    # Clear any other cache files that might exist
    cache_files = [
        os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR)
        if f.endswith('.json') or f.endswith('.npy') or f.endswith('.pkl')
    ]
    
    for cache_file in cache_files:
        try:
            os.remove(cache_file)
            logger.info(f"Removed cache file: {cache_file}")
        except Exception as e:
            logger.error(f"Error removing cache file {cache_file}: {e}")
    
    logger.info("All cache data cleared successfully")

def interactive_compliance_query(segments: List[str], index: Any) -> None:
    """Interactive query interface with optimized processing"""
    logger.info("\nCompliance Framework RAG System")
    logger.info("Type 'exit' to quit.")
    logger.info("Type 'upload' to analyze a privacy policy document.")
    logger.info("Type 'cache' to see cache stats.")
    logger.info("Type 'clear_cache' to clear the query cache.")
    conversation = ConversationHistory()

    while True:
        query = input("\nEnter your compliance query or command: ")
        
        if query.lower() == "exit":
            conversation.reset()
            save_query_cache()
            break
        elif query.lower() == "cache":
            logger.info(f"Query cache size: {len(QUERY_CACHE)} entries")
            logger.info(f"Embedding cache stats: {get_cached_embedding.cache_info()}")
            continue
        elif query.lower() == "clear_cache":
            clear_query_cache()
            continue
        elif query.lower() == "upload":
            file_path = input("Enter the path to your privacy policy document (PDF, TXT, or DOCX): ")
            policy_text = upload_privacy_policy(file_path)
            if policy_text.startswith("Error") or policy_text.startswith("Unsupported"):
                logger.info(policy_text)
                continue
            framework = input("Enter a specific framework to analyze against (or press Enter for all frameworks): ")
            logger.info("\nAnalyzing privacy policy...")
            analysis = analyze_privacy_policy(file_path, segments, index, framework)
            logger.info("\n=== Privacy Policy Analysis ===")
            logger.info(analysis)
            logger.info("\n--- End of Analysis ---\n")
            conversation.add_exchange("Uploaded privacy policy", analysis)
            continue

        total_start_time = time.time()
        
        try:
            logger.info("\nProcessing query...")
            
            # First check if this is a compliance-related query
            is_compliance, reason = is_compliance_related(query, conversation.get_context())
            
            if not is_compliance:
                logger.info("\n=== Response ===")
                response = generate_non_compliance_response(query)
                logger.info(response)
                logger.info("\n--- End of Response ---\n")
                conversation.add_exchange(query, response)
                continue
            
            # Get query embedding - use cached version
            query_text_hash = hash_text(query)
            query_embedding = get_cached_embedding(query_text_hash, query)
            
            if query_embedding is None:
                logger.info("Failed to generate query embedding.")
                continue
            
            # Get relevant context
            query_embedding = np.expand_dims(query_embedding, axis=0)
            distances, idxs = index.search(query_embedding, 3)
            retrieved_context = " ".join([segments[idx] for idx in idxs[0] if idx < len(segments)])
            
            # Process the query
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            final_response, processing_time = loop.run_until_complete(
                process_query(query, retrieved_context, conversation.get_context())
            )
            loop.close()
            
            logger.info(f"\nTotal processing time: {processing_time:.2f} seconds")
            
            logger.info("\n=== Compliance Analysis ===")
            logger.info(final_response)
            logger.info("\n--- End of Analysis ---\n")
            
            # Log timing information
            timing_log = {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "processing_time": processing_time,
                "is_compliance": is_compliance,
                "reason": reason
            }
            
            # Save timing log to file
            with open("response_timing_log.json", "a") as f:
                f.write(json.dumps(timing_log) + "\n")

            conversation.add_exchange(query, final_response)

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            logger.info("Please try again...")
            continue

def main():
    logger.info("Loading compliance framework system...")
    segments, embeddings, index = process_documents()
    
    if segments is None:
        logger.info("Failed to process documents.")
        return
    
    logger.info(f"Loaded {len(segments)} segments")
    interactive_compliance_query(segments, index)

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

def get_document_generation_questions(document_type: str, framework: str) -> Dict[str, Any]:
    """
    Get follow-up questions needed for document generation using LLM.
    Returns a structured response with questions, explanations, and examples.
    """
    prompt = (
        f"Generate a comprehensive guide for creating a {framework}-compliant {document_type} document.\n"
        f"Provide the following information in JSON format:\n"
        "1. A list of required information categories\n"
        "2. For each category:\n"
        "   - Specific questions to ask\n"
        "   - Why each question is important\n"
        "   - Example answers\n"
        "   - Relevant compliance requirements\n"
        "3. A step-by-step process for gathering the information\n"
        "4. Common pitfalls to avoid\n"
        "5. Best practices for implementation\n\n"
        f"Focus on {framework} requirements and ensure all questions are actionable and specific.\n"
        "Return the response as a JSON object with the following structure:\n"
        "{\n"
        "  'steps': [{'step_number': int, 'description': str}],\n"
        "  'categories': [\n"
        "    {\n"
        "      'category': str,\n"
        "      'questions': [\n"
        "        {\n"
        "          'question': str,\n"
        "          'key': str,\n"
        "          'importance': str,\n"
        "          'example': str,\n"
        "          'compliance_requirement': str\n"
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ],\n"
        "  'pitfalls': [str],\n"
        "  'best_practices': [str]\n"
        "}"
    )
    
    try:
        response = rate_limited_generate_content(prompt)
        guide = json.loads(response)
        return guide
    except Exception as e:
        logger.error(f"Error generating guide: {str(e)}")
        # Return basic structure as fallback
        return {
            'steps': [
                {'step_number': 1, 'description': 'Identify your organization type and data processing activities'},
                {'step_number': 2, 'description': 'Document your data collection and processing practices'}
            ],
            'categories': [
                {
                    'category': 'Organization Information',
                    'questions': [
                        {
                            'question': 'What type of organization are you?',
                            'key': 'organization_type',
                            'importance': 'Helps determine applicable regulations and requirements',
                            'example': 'Healthcare provider, E-commerce business, SaaS company',
                            'compliance_requirement': 'Organization classification under the framework'
                        }
                    ]
                }
            ],
            'pitfalls': ['Not documenting all data processing activities', 'Incomplete privacy notices'],
            'best_practices': ['Regular review and updates', 'Clear documentation of all processes']
        }

def generate_document_with_answers(document_type: str, framework: str, answers: Dict[str, str], format: str = "docx") -> str:
    """
    Generate a document using the provided answers with enhanced structure and guidance.
    """
    try:
        # Get framework requirements
        requirements = get_framework_requirements(framework)
        
        # Generate document structure using LLM
        structure_prompt = (
            f"Generate a comprehensive structure for a {framework}-compliant {document_type} document.\n"
            f"Based on the provided answers:\n{json.dumps(answers, indent=2)}\n"
            "Include:\n"
            "1. Executive summary\n"
            "2. Detailed sections for each compliance requirement\n"
            "3. Implementation guidelines\n"
            "4. Compliance verification steps\n"
            "5. Maintenance and update procedures\n\n"
            "Return a JSON array of section objects, each containing:\n"
            "- title: section title\n"
            "- content: section content\n"
            "- requirements: list of specific compliance requirements addressed\n"
            "- implementation_steps: list of steps to implement the section\n"
            "- verification_steps: list of steps to verify compliance"
        )
        
        structure_response = rate_limited_generate_content(structure_prompt)
        sections = json.loads(structure_response)
        
        # Create document
        doc = Document()
        
        # Add title
        doc.add_heading(f"{'Privacy Policy' if document_type == 'privacy' else 'Terms and Conditions'}", 0)
        
        # Add last updated date
        doc.add_paragraph(f"Last Updated: {datetime.now().strftime('%Y-%m-%d')}")
        
        # Add executive summary
        summary_prompt = (
            f"Generate an executive summary for a {framework}-compliant {document_type} document.\n"
            f"Organization context: {json.dumps(answers, indent=2)}\n"
            "The summary should:\n"
            "1. Highlight key compliance requirements\n"
            "2. Summarize implementation status\n"
            "3. Identify critical areas\n"
            "4. Provide an overview of the document structure"
        )
        summary = rate_limited_generate_content(summary_prompt)
        doc.add_heading("Executive Summary", level=1)
        doc.add_paragraph(summary)
        
        # Add sections
        for section in sections:
            # Add section title
            doc.add_heading(section['title'], level=1)
            
            # Add section content
            doc.add_paragraph(section['content'])
            
            # Add requirements
            if 'requirements' in section:
                doc.add_heading("Compliance Requirements", level=2)
                for req in section['requirements']:
                    doc.add_paragraph(f"• {req}", style='List Bullet')
            
            # Add implementation steps
            if 'implementation_steps' in section:
                doc.add_heading("Implementation Steps", level=2)
                for step in section['implementation_steps']:
                    doc.add_paragraph(f"• {step}", style='List Bullet')
            
            # Add verification steps
            if 'verification_steps' in section:
                doc.add_heading("Compliance Verification", level=2)
                for step in section['verification_steps']:
                    doc.add_paragraph(f"• {step}", style='List Bullet')
        
        # Add standard sections
        standard_sections = {
            "Contact Information": "For any questions or concerns regarding this document, please contact us at:\n\n[Company Name]\n[Address]\n[Email]\n[Phone]",
            "Changes to This Document": f"We may update this {document_type} from time to time to reflect changes in our practices or for other operational, legal, or regulatory reasons. The updated version will be indicated by an updated 'Last Updated' date.",
            "Compliance and Certification": f"We are committed to maintaining compliance with {framework} requirements and regularly review our practices to ensure they meet the highest standards.",
            "Implementation Timeline": "This document outlines our compliance implementation plan and timeline.",
            "Regular Review Process": "We conduct regular reviews of our compliance status and update this document accordingly."
        }
        
        for title, content in standard_sections.items():
            doc.add_heading(title, level=1)
            doc.add_paragraph(content)
        
        # Add appendix with framework requirements
        doc.add_heading("Appendix: Framework Requirements", level=1)
        for req in requirements:
            doc.add_heading(req['title'], level=2)
            doc.add_paragraph(req['description'])
        
        # Save the document
        filename = f"generated_{document_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format.lower()}"
        doc.save(filename)
        
        return f"Document generated and saved as {filename}"
            
    except Exception as e:
        logger.error(f"Error generating document: {str(e)}")
        return f"Error generating document: {str(e)}"

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

if __name__ == "__main__":
    main() 