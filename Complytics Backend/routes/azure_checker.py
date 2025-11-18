"""
Azure Compliance Checker API Routes
FastAPI endpoints for Azure best practices compliance checking
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import Optional
import os
import logging
import tempfile
from pathlib import Path
from datetime import datetime
import json
import numpy as np
import hashlib

from schemas.users import UserInDB
from routes.auth import get_current_user
from db import database
from azure_checker.utils.text_extraction import extract_text_from_file, clean_text, chunk_text
from azure_checker.utils.embedding_engine import AzureEmbeddingEngine
from azure_checker.utils.compliance_logic import AzureComplianceAnalyzer

# PDF generation
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/azure-checker", tags=["azure-checker"])

# Paths
BASE_DIR = Path(__file__).parent.parent / 'azure_checker'
EMBEDDINGS_BASE_DIR = BASE_DIR / 'embeddings'
INDEX_BASE_DIR = BASE_DIR / 'faiss_indexes'
REPORTS_DIR = BASE_DIR / 'reports'

# Ensure reports directory exists
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Initialize global engines (loaded once) - now supports multiple frameworks
_engines = {}
_frameworks = ['azure', 'gdpr', 'iso27001', 'iso27017', 'iso27018']

# File validation constants
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.json', '.doc'}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword',
    'text/plain',
    'application/json',
    'text/json'
}
# Image formats to explicitly reject
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg', '.ico', '.tiff', '.tif', '.heic', '.heif', '.avif'}
IMAGE_MIME_TYPES = {
    'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/bmp', 
    'image/webp', 'image/svg+xml', 'image/x-icon', 'image/tiff', 
    'image/vnd.microsoft.icon', 'image/heic', 'image/heif', 'image/avif'
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MIN_FILE_SIZE = 1  # 1 byte minimum


def load_framework_engine(framework_name: str):
    """Load a specific framework's embedding engine and index"""
    try:
        import numpy as np
        import faiss
        import json
        
        embeddings_dir = EMBEDDINGS_BASE_DIR / framework_name
        index_dir = INDEX_BASE_DIR / framework_name
        
        embeddings_file = embeddings_dir / f'{framework_name}_embeddings.npy'
        document_map_file = embeddings_dir / f'{framework_name}_document_map.json'
        index_file = index_dir / f'{framework_name}_index.faiss'
        
        # Check if files exist
        if not embeddings_file.exists() or not index_file.exists():
            logger.warning(f"{framework_name} embeddings not found, skipping")
            return None
        
        # Load embeddings
        embeddings = np.load(str(embeddings_file))
        
        # Load document map
        if document_map_file.exists():
            with open(document_map_file, 'r', encoding='utf-8') as f:
                doc_data = json.load(f)
            chunks = doc_data.get('segments', doc_data.get('chunks', []))
            metadata = doc_data.get('metadata', [])
        else:
            logger.warning(f"{framework_name} document map not found")
            return None
        
        # Load FAISS index
        faiss_index = faiss.read_index(str(index_file))
        
        # Initialize engine for encoding queries
        engine = AzureEmbeddingEngine()
        
        logger.info(f"Loaded {framework_name}: {len(chunks)} chunks, {faiss_index.ntotal} vectors")
        
        return {
            'engine': engine,
            'index': faiss_index,
            'chunks': chunks,
            'metadata': metadata,
            'framework': framework_name
        }
        
    except Exception as e:
        logger.error(f"Error loading {framework_name}: {e}")
        return None


def get_all_framework_engines():
    """Get or initialize all framework engines"""
    global _engines
    
    if not _engines:
        logger.info("Initializing Multi-Framework Compliance Checker...")
        
        for framework in _frameworks:
            engine_data = load_framework_engine(framework)
            if engine_data:
                _engines[framework] = engine_data
        
        if not _engines:
            raise HTTPException(
                status_code=500,
                detail="No framework embeddings found. Please run: python -m azure_checker.create_all_framework_embeddings"
            )
        
        logger.info(f"Loaded {len(_engines)} frameworks: {list(_engines.keys())}")
    
    return _engines


def get_azure_engine():
    """Get or initialize the Azure embedding engine (backward compatibility)"""
    engines = get_all_framework_engines()
    
    if 'azure' not in engines:
        raise HTTPException(
            status_code=500,
            detail="Azure embeddings not found. Please run: python -m azure_checker.create_all_framework_embeddings"
        )
    
    azure_data = engines['azure']
    return azure_data['engine'], azure_data['index'], azure_data['chunks'], azure_data['metadata']


def validate_uploaded_file(file: UploadFile) -> dict:
    """
    Comprehensive file validation for Azure compliance checker uploads.
    
    Validates:
    - File extension
    - Image format rejection
    - File size (min and max)
    - MIME type
    - Filename validity
    - Empty file check
    
    Returns:
        dict: Validation result with 'valid' (bool) and 'error' (str) keys
    """
    errors = []
    
    # Check if filename exists
    if not file.filename:
        return {
            'valid': False,
            'error': 'File name is missing. Please provide a valid file name.'
        }
    
    # Get file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    # 1. Explicitly reject image formats
    if file_ext in IMAGE_EXTENSIONS:
        image_format = file_ext.upper().replace('.', '')
        return {
            'valid': False,
            'error': f'Image files ({image_format}) are not supported. Please upload a document file (PDF, DOCX, TXT, or JSON) instead.'
        }
    
    # Check MIME type for images (even if extension is wrong)
    if file.content_type and file.content_type in IMAGE_MIME_TYPES:
        return {
            'valid': False,
            'error': f'Image files are not supported. The uploaded file appears to be an image ({file.content_type}). Please upload a document file (PDF, DOCX, TXT, or JSON) instead.'
        }
    
    # 2. Validate file extension
    if file_ext not in ALLOWED_EXTENSIONS:
        return {
            'valid': False,
            'error': f'Unsupported file type: {file_ext}. Allowed file types are: PDF, DOCX, DOC, TXT, and JSON. Please upload a supported document format.'
        }
    
    # 3. Validate MIME type (if provided)
    if file.content_type:
        # Normalize MIME type (remove charset, etc.)
        mime_type = file.content_type.split(';')[0].strip().lower()
        if mime_type not in [m.lower() for m in ALLOWED_MIME_TYPES]:
            # Don't reject if extension is valid but MIME type is slightly off
            # Some systems report different MIME types
            logger.warning(f"MIME type mismatch: {file.content_type} for extension {file_ext}")
    
    # 4. Validate filename (check for invalid characters)
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    if any(char in file.filename for char in invalid_chars):
        return {
            'valid': False,
            'error': f'Invalid file name. The file name contains invalid characters. Please rename the file and try again.'
        }
    
    # 5. Check filename length
    if len(file.filename) > 255:
        return {
            'valid': False,
            'error': 'File name is too long. Please use a file name with less than 255 characters.'
        }
    
    # Note: File size validation will be done after reading the file content
    # since we need to read it anyway for processing
    
    return {'valid': True, 'error': None}


def validate_file_size(file_content: bytes) -> dict:
    """
    Validate file size after reading content.
    
    Args:
        file_content: The file content as bytes
        
    Returns:
        dict: Validation result with 'valid' (bool) and 'error' (str) keys
    """
    file_size = len(file_content)
    
    # Check if file is empty
    if file_size < MIN_FILE_SIZE:
        return {
            'valid': False,
            'error': 'The uploaded file is empty. Please upload a file with content.'
        }
    
    # Check if file is too large
    if file_size > MAX_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        return {
            'valid': False,
            'error': f'File size ({size_mb:.2f} MB) exceeds the maximum allowed size of {max_mb} MB. Please upload a smaller file.'
        }
    
    return {'valid': True, 'error': None}


def validate_document_relevance(document_text: str, filename: str = "") -> dict:
    """
    Validate that the uploaded document is relevant to Azure/compliance topics.
    Uses AI to detect irrelevant documents (games, CVs, personal documents, etc.)
    
    Args:
        document_text: Extracted text from the document
        filename: Original filename (optional, for context)
        
    Returns:
        dict: Validation result with 'valid' (bool), 'error' (str), and 'relevance_score' (float) keys
    """
    if not document_text or len(document_text.strip()) < 50:
        return {
            'valid': False,
            'error': 'Document content is too short to analyze. Please upload a document with sufficient content.',
            'relevance_score': 0.0
        }
    
    try:
        # Import AI function for content validation
        from compliance_rag import rate_limited_generate_content_optimized
        import json
        
        # Sample first 3000 characters for relevance check (to save tokens)
        sample_text = document_text[:3000]
        
        prompt = f"""You are a document relevance validator for an Azure Compliance Checker system.

DOCUMENT FILENAME: {filename if filename else "Unknown"}

DOCUMENT CONTENT SAMPLE:
{sample_text}

TASK: Determine if this document is relevant to Azure cloud compliance, security, or IT governance.

RELEVANT DOCUMENTS include:
- Azure configuration documents, policies, or architecture
- Cloud security policies, compliance frameworks (GDPR, ISO 27001, etc.)
- IT security documentation, access control policies
- Data protection policies, privacy policies
- Infrastructure as Code (IaC) files, Terraform, ARM templates
- Security audit reports, compliance assessments
- Cloud governance documents, best practices documentation

IRRELEVANT DOCUMENTS include:
- Personal CVs, resumes, job applications
- Game documentation, game guides, entertainment content
- Personal letters, emails, social media content
- Recipes, cooking instructions
- Fiction, novels, stories
- Academic papers unrelated to IT/compliance
- Marketing materials, advertisements
- Any content completely unrelated to Azure, cloud computing, compliance, or IT security

ANALYZE THE DOCUMENT and respond in this EXACT JSON format (no markdown, just JSON):
{{
  "is_relevant": true/false,
  "relevance_score": 0.0-1.0,
  "document_type": "brief description (e.g., 'Azure configuration', 'CV', 'Game guide', 'Privacy policy')",
  "reasoning": "brief explanation of why it is or isn't relevant",
  "confidence": 0.0-1.0
}}

Be strict: Only mark as relevant if the document is clearly related to Azure, cloud compliance, IT security, or governance.
If it's a personal document, game content, or completely unrelated topic, mark is_relevant as false.

CRITICAL: If the document is a CV, resume, game guide, recipe, fiction, or any personal/entertainment content, 
you MUST set is_relevant to false, regardless of the relevance_score."""

        response = rate_limited_generate_content_optimized(
            prompt,
            temperature=0.0,  # Set to 0.0 for deterministic, consistent responses
            max_tokens=500
        )
        
        # Extract JSON from response
        cleaned = response.strip()
        if '```' in cleaned:
            if '```json' in cleaned:
                cleaned = cleaned.split('```json')[1].split('```')[0].strip()
            elif '```' in cleaned:
                cleaned = cleaned.split('```')[1].split('```')[0].strip()
        
        # Find JSON object
        if '{' in cleaned and '}' in cleaned:
            start = cleaned.find('{')
            end = cleaned.rfind('}') + 1
            json_str = cleaned[start:end]
            result = json.loads(json_str)
            
            is_relevant = result.get('is_relevant', False)
            relevance_score = float(result.get('relevance_score', 0.0))
            document_type = result.get('document_type', 'Unknown').lower()
            reasoning = result.get('reasoning', '')
            confidence = float(result.get('confidence', 0.5))
            
            # List of document types that should always be rejected
            irrelevant_types = [
                'cv', 'resume', 'curriculum vitae', 'job application', 'application',
                'game', 'game guide', 'gaming', 'entertainment',
                'recipe', 'cooking', 'food',
                'fiction', 'novel', 'story', 'literature',
                'personal letter', 'email', 'social media',
                'marketing', 'advertisement', 'ad',
                'academic paper', 'essay', 'thesis', 'dissertation'
            ]
            
            # Check if document type is explicitly irrelevant
            is_irrelevant_type = any(irrelevant in document_type for irrelevant in irrelevant_types)
            
            # Primary check: If AI explicitly says it's not relevant, reject it
            if not is_relevant:
                error_msg = f"The uploaded document appears to be a {document_type}, which is not relevant to Azure compliance checking."
                if reasoning:
                    error_msg += f" {reasoning}"
                error_msg += " Please upload a document related to Azure configuration, cloud security, compliance frameworks (GDPR, ISO 27001, etc.), or IT governance."
                
                logger.warning(f"Document rejected as irrelevant: {filename} - Type: {document_type}, is_relevant: {is_relevant}, Reasoning: {reasoning}")
                
                return {
                    'valid': False,
                    'error': error_msg,
                    'relevance_score': relevance_score,
                    'document_type': document_type
                }
            
            # Secondary check: If document type is in our blacklist, reject it
            if is_irrelevant_type and confidence > 0.6:
                error_msg = f"The uploaded document appears to be a {document_type}, which is not relevant to Azure compliance checking."
                if reasoning:
                    error_msg += f" {reasoning}"
                error_msg += " Please upload a document related to Azure configuration, cloud security, compliance frameworks (GDPR, ISO 27001, etc.), or IT governance."
                
                logger.warning(f"Document rejected due to irrelevant type: {filename} - Type: {document_type}, Confidence: {confidence}")
                
                return {
                    'valid': False,
                    'error': error_msg,
                    'relevance_score': relevance_score,
                    'document_type': document_type
                }
            
            # Tertiary check: If relevance score is very low (< 0.4), reject it
            if relevance_score < 0.4 and confidence > 0.6:
                error_msg = f"The uploaded document does not appear to be relevant to Azure compliance or cloud security."
                if document_type and document_type.lower() != 'unknown':
                    error_msg += f" Detected document type: {document_type.lower()}."
                error_msg += " Please upload a document related to Azure configuration, cloud security policies, compliance frameworks, or IT governance."
                
                logger.warning(f"Document rejected due to low relevance score: {filename} - Score: {relevance_score}, Type: {document_type}, Confidence: {confidence}")
                
                return {
                    'valid': False,
                    'error': error_msg,
                    'relevance_score': relevance_score,
                    'document_type': document_type
                }
            
            # Document is relevant or AI is uncertain - allow it to proceed
            logger.info(f"Document relevance check passed: {filename} - Type: {document_type}, Score: {relevance_score}, Confidence: {confidence}")
            
            return {
                'valid': True,
                'error': None,
                'relevance_score': relevance_score,
                'document_type': document_type
            }
        else:
            # If we can't parse the response, log warning but allow document to proceed
            # (better to analyze potentially irrelevant doc than reject valid ones)
            logger.warning(f"Could not parse relevance validation response for {filename}, allowing document to proceed")
            return {
                'valid': True,
                'error': None,
                'relevance_score': 0.5,
                'document_type': 'Unknown'
            }
            
    except Exception as e:
        # If validation fails, log error but allow document to proceed
        # (better to analyze potentially irrelevant doc than reject valid ones due to technical errors)
        logger.error(f"Error validating document relevance for {filename}: {e}")
        return {
            'valid': True,
            'error': None,
            'relevance_score': 0.5,
            'document_type': 'Unknown'
        }


async def _perform_compliance_analysis(
    text: str,
    document_name: str,
    current_user: UserInDB,
    document_hash: str,
    source_type: str = "document",
    source_metadata: Optional[dict] = None,
    max_chunks: int = 10
) -> dict:
    """
    Shared helper to run the multi-framework compliance analysis pipeline.
    Handles caching, analysis, persistence, and response shaping.
    """
    db = database.db
    source_metadata = source_metadata or {}

    # Check cache (valid for 7 days)
    try:
        cached_result = await db.azure_compliance_results.find_one({
            'document_hash': document_hash,
            'user_id': current_user.id,
            'source_type': source_type
        })

        if cached_result:
            cache_age = (datetime.utcnow() - cached_result.get('created_at', datetime.utcnow())).days
            if cache_age < 7:
                logger.info(f"Returning cached {source_type} analysis result (age: {cache_age} days)")
                return {
                    'overall_score': cached_result.get('overall_score', 0),
                    'overall_status': cached_result.get('overall_status', 'Partial'),
                    'frameworks': cached_result.get('frameworks', {}),
                    'framework_scores': cached_result.get('framework_scores', {}),
                    'document_name': document_name,
                    'analyzed_at': cached_result.get('analyzed_at', datetime.utcnow().isoformat()),
                    'analyzed_by': cached_result.get('user_email', current_user.email),
                    'frameworks_analyzed': cached_result.get('frameworks_analyzed', 0),
                    'summary': cached_result.get('summary', ''),
                    'result_id': str(cached_result['_id']),
                    'cached': True,
                    'source_type': cached_result.get('source_type', source_type),
                    'source_metadata': cached_result.get('source_metadata', source_metadata)
                }
    except Exception as e:
        logger.warning(f"Error checking cached {source_type} result: {e}, proceeding with fresh analysis")

    chunks = chunk_text(text, chunk_size=1000, overlap=100)
    if len(chunks) == 0:
        raise HTTPException(
            status_code=400,
            detail="Content is too short or lacks analyzable text for compliance review."
        )

    framework_engines = get_all_framework_engines()
    analyzer = AzureComplianceAnalyzer()

    chunks_to_analyze = chunks[:max_chunks]
    framework_results = {}

    for framework_name, engine_data in framework_engines.items():
        logger.info(f"\nAnalyzing against {framework_name} for {source_type}...")
        try:
            framework_search_results = []
            for i, chunk in enumerate(chunks_to_analyze):
                try:
                    results = engine_data['engine'].search_similar(
                        chunk,
                        engine_data['index'],
                        engine_data['chunks'],
                        engine_data['metadata'],
                        top_k=3
                    )
                    framework_search_results.extend(results)
                except Exception as e:
                    logger.warning(f"Error searching {framework_name} chunk {i+1}: {e}")
                    continue

            framework_analysis = analyzer.analyze_framework(
                framework_name,
                framework_search_results,
                document_text=text
            )
            framework_results[framework_name] = framework_analysis
            logger.info(f"✓ {framework_name}: {framework_analysis.get('score', 0)}/100 ({framework_analysis.get('status', 'Unknown')})")
        except Exception as e:
            logger.error(f"Error analyzing {framework_name}: {e}")
            framework_results[framework_name] = {
                'framework': framework_name,
                'score': 0,
                'status': 'Error',
                'findings': [],
                'recommendation': f'Error analyzing against {framework_name}: {str(e)}'
            }

    all_scores = [fr.get('score', 0) for fr in framework_results.values()]
    overall_score = int(np.mean(all_scores)) if all_scores else 0

    if overall_score >= 80:
        overall_status = 'Compliant'
    elif overall_score >= 60:
        overall_status = 'Partial'
    else:
        overall_status = 'Non-Compliant'

    source_descriptor = "uploaded document" if source_type == "document" else "fetched Azure settings snapshot"
    framework_list = ', '.join(framework_results.keys())

    analysis = {
        'overall_score': overall_score,
        'overall_status': overall_status,
        'frameworks': framework_results,
        'framework_scores': {name: result.get('score', 0) for name, result in framework_results.items()},
        'document_name': document_name,
        'analyzed_at': datetime.utcnow().isoformat(),
        'analyzed_by': current_user.email,
        'frameworks_analyzed': len(framework_results),
        'summary': (
            f"Multi-framework compliance analysis of the {source_descriptor}. "
            f"Overall score: {overall_score}/100 ({overall_status}). "
            f"Analyzed frameworks: {framework_list or 'None'}."
        ),
        'source_type': source_type,
        'source_metadata': source_metadata,
        'cached': False
    }

    # Persist for future reference/caching
    try:
        organization_id = getattr(current_user, "organization_id", None)
        if not organization_id:
            user_doc = await db.users.find_one({"_id": current_user.id})
            if user_doc:
                organization_id = user_doc.get("organization_id")

        result_document = {
            'user_id': current_user.id,
            'user_email': current_user.email,
            'organization_id': organization_id,
            'document_name': document_name,
            'document_hash': document_hash,
            'overall_score': analysis['overall_score'],
            'overall_status': analysis['overall_status'],
            'frameworks': analysis['frameworks'],
            'framework_scores': analysis['framework_scores'],
            'frameworks_analyzed': analysis['frameworks_analyzed'],
            'summary': analysis['summary'],
            'created_at': datetime.utcnow(),
            'analyzed_at': analysis['analyzed_at'],
            'source_type': source_type,
            'source_metadata': source_metadata,
        }

        snapshot_id = source_metadata.get('snapshot_id')
        if snapshot_id:
            result_document['snapshot_id'] = snapshot_id

        result = await db.azure_compliance_results.insert_one(result_document)
        analysis['result_id'] = str(result.inserted_id)
        logger.info(f"Compliance result saved (source={source_type}) with ID: {analysis['result_id']}")
    except Exception as e:
        logger.error(f"Error saving compliance result to MongoDB: {e}")

    return analysis


@router.post("/analyze")
async def analyze_azure_document(
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Analyze uploaded Azure configuration/policy document against best practices
    
    Accepts: .pdf, .docx, .txt, .json
    Returns: Compliance score and findings
    """
    logger.info(f"Azure compliance check requested by user: {current_user.id}")
    
    # Comprehensive file validation
    validation_result = validate_uploaded_file(file)
    if not validation_result['valid']:
        logger.warning(f"File validation failed for {file.filename}: {validation_result['error']}")
        raise HTTPException(
            status_code=400,
            detail=validation_result['error']
        )
    
    try:
        # Read file content for size validation
        content = await file.read()
        
        # Validate file size
        size_validation = validate_file_size(content)
        if not size_validation['valid']:
            logger.warning(f"File size validation failed for {file.filename}: {size_validation['error']}")
            raise HTTPException(
                status_code=400,
                detail=size_validation['error']
            )
        
        # Get file extension for temp file
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        logger.info(f"Processing uploaded file: {file.filename}")
        
        # Extract text
        try:
            text = extract_text_from_file(tmp_file_path)
        except Exception as e:
            logger.error(f"Error extracting text from file: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to extract text from the uploaded file. The file may be corrupted, password-protected, or in an unsupported format. Error: {str(e)}"
            )
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_file_path)
            except:
                pass
        
        if not text or not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from the uploaded file. The file may be empty, corrupted, password-protected, or contain only images. Please ensure the file contains readable text content."
            )
        
        # Validate document relevance (check if it's related to Azure/compliance)
        logger.info(f"Validating document relevance for: {file.filename}")
        relevance_validation = validate_document_relevance(text, file.filename)
        
        if not relevance_validation['valid']:
            logger.warning(f"Document relevance validation failed: {relevance_validation['error']}")
            raise HTTPException(
                status_code=400,
                detail=relevance_validation['error']
            )
        
        logger.info(f"Document relevance check passed. Type: {relevance_validation.get('document_type', 'Unknown')}, Score: {relevance_validation.get('relevance_score', 0.0):.2f}")
        
        text = clean_text(text)
        max_text_length = 50000
        if len(text) > max_text_length:
            logger.info(f"Text length {len(text)} exceeds limit, using first {max_text_length} chars")
            text = text[:max_text_length]
        
        document_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        logger.info(f"Document fingerprint: {document_hash[:16]}...")

        analysis = await _perform_compliance_analysis(
            text=text,
            document_name=file.filename,
            current_user=current_user,
            document_hash=document_hash,
            source_type="document",
            source_metadata={
                "filename": file.filename,
                "uploaded_at": datetime.utcnow().isoformat()
            }
        )

        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing document: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing document: {str(e)}"
        )


@router.post("/analyze-snapshot")
async def analyze_azure_snapshot(current_user: UserInDB = Depends(get_current_user)):
    """
    Analyze the latest sanitized Azure configuration snapshot stored from Graph fetches.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=400,
            detail="User is not associated with an organization"
        )

    db = database.db
    snapshot = await db.azure_config_snapshots.find_one(
        {"organization_id": current_user.organization_id},
        sort=[("timestamp", -1)]
    )

    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail="No Azure configuration snapshot found. Please fetch Azure settings first."
        )

    settings = snapshot.get("settings")
    if not settings:
        raise HTTPException(
            status_code=400,
            detail="Snapshot does not contain sanitized settings."
        )

    settings_text = json.dumps(settings, indent=2)
    if not settings_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Snapshot settings are empty."
        )

    text = clean_text(settings_text)
    max_text_length = 60000
    if len(text) > max_text_length:
        logger.info(f"Snapshot text length {len(text)} exceeds limit, using first {max_text_length} chars")
        text = text[:max_text_length]

    snapshot_id = snapshot.get("_id")
    snapshot_timestamp = snapshot.get("timestamp")
    snapshot_iso = snapshot_timestamp.isoformat() if isinstance(snapshot_timestamp, datetime) else str(snapshot_timestamp)

    document_name = f"Azure Config Snapshot ({snapshot_iso})"
    document_hash = hashlib.sha256(f"{snapshot_id}-{text}".encode('utf-8')).hexdigest()

    analysis = await _perform_compliance_analysis(
        text=text,
        document_name=document_name,
        current_user=current_user,
        document_hash=document_hash,
        source_type="snapshot",
        source_metadata={
            "snapshot_id": str(snapshot_id),
            "snapshot_timestamp": snapshot_iso
        },
        max_chunks=12
    )

    return analysis


@router.post("/generate-checklist/{result_id}")
async def generate_compliance_checklist(
    result_id: str,
    framework: Optional[str] = None,  # 'gdpr', 'iso27001', 'iso27018', or None for all
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db)
):
    """
    Generate a fully compliant checklist based on identified gaps from analysis.
    Creates actionable items for users to implement in Azure to become compliant.
    """
    try:
        from bson import ObjectId
        from bson.errors import InvalidId
        from compliance_rag import rate_limited_generate_content_optimized
        import json
        
        # Validate result_id
        try:
            result_obj_id = ObjectId(result_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid result ID format")
        
        # Fetch analysis result
        result = await db.azure_compliance_results.find_one({"_id": result_obj_id})
        if not result:
            raise HTTPException(status_code=404, detail="Analysis result not found")
        
        # Check user access
        if str(result.get('user_id')) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied to this analysis result")
        
        # Get frameworks to process
        frameworks_to_process = []
        if framework:
            if framework in result.get('frameworks', {}):
                frameworks_to_process = [framework]
            else:
                raise HTTPException(status_code=400, detail=f"Framework '{framework}' not found in analysis")
        else:
            # Process all frameworks that have gaps
            frameworks_to_process = [
                fw for fw, fw_data in result.get('frameworks', {}).items()
                if fw_data.get('gaps') and len(fw_data.get('gaps', [])) > 0
            ]
        
        if not frameworks_to_process:
            raise HTTPException(
                status_code=400,
                detail="No frameworks with identified gaps found. Cannot generate checklist."
            )
        
        # Framework display names
        framework_names = {
            'gdpr': 'GDPR',
            'iso27001': 'ISO 27001',
            'iso27018': 'ISO 27018',
            'iso27017': 'ISO 27017',
            'azure': 'Azure Best Practices'
        }
        
        # Generate checklist for each framework
        checklist_items = []
        
        for fw_name in frameworks_to_process:
            fw_data = result.get('frameworks', {}).get(fw_name, {})
            gaps = fw_data.get('gaps', [])
            compliant_areas = fw_data.get('compliant_areas', [])
            recommendation = fw_data.get('recommendation', '')
            key_requirements = fw_data.get('key_requirements', [])
            score = fw_data.get('score', 0)
            
            if not gaps:
                continue
            
            # Use AI to generate actionable checklist items from gaps
            prompt = f"""You are an Azure compliance expert creating a detailed, actionable checklist for Azure portal implementation to achieve full {framework_names.get(fw_name, fw_name)} compliance.

ANALYSIS RESULTS:
- Current Compliance Score: {score}/100
- Framework: {framework_names.get(fw_name, fw_name)}
- Identified Gaps: {json.dumps(gaps, indent=2)}
- Compliant Areas: {json.dumps(compliant_areas, indent=2)}
- Key Requirements: {json.dumps(key_requirements, indent=2)}
- Recommendation: {recommendation}

TASK:
Create a comprehensive, actionable checklist that addresses ALL identified gaps. Each checklist item MUST include:

1. **Exact Azure Portal Navigation Path**: Step-by-step portal navigation (e.g., "Azure Portal > Azure Active Directory > Security > Conditional Access > Policies")
2. **Specific Settings to Configure**: Exact setting names, values, and configurations
3. **Detailed Step-by-Step Instructions**: Precise clicks, selections, and configurations
4. **Azure Portal URLs/Paths**: Direct links or exact navigation paths where possible
5. **Screenshots Guidance**: What users should see at each step
6. **Verification Steps**: How to verify the setting was applied correctly

FORMAT YOUR RESPONSE AS JSON:
{{
  "framework": "{framework_names.get(fw_name, fw_name)}",
  "current_score": {score},
  "target_score": 100,
  "checklist_items": [
    {{
      "id": 1,
      "title": "Specific actionable item title",
      "description": "Detailed description of what needs to be done and why",
      "gap_addressed": "Which gap this item addresses",
      "priority": "CRITICAL|HIGH|MEDIUM|LOW",
      "effort": "Quick|Moderate|Complex",
      "azure_services": ["Azure Service 1", "Azure Service 2"],
      "azure_portal_path": "Exact navigation path in Azure Portal",
      "azure_portal_url": "Direct URL or portal path (if applicable)",
      "settings_to_configure": {{
        "setting_name": "Exact setting name",
        "current_value": "What it likely is now",
        "required_value": "What it should be",
        "location": "Where in the portal this setting is located"
      }},
      "implementation_steps": [
        {{
          "step_number": 1,
          "action": "Navigate to Azure Portal > Azure Active Directory",
          "details": "Click on 'Azure Active Directory' in the left navigation menu",
          "what_to_look_for": "You should see the Azure AD overview page"
        }},
        {{
          "step_number": 2,
          "action": "Go to Security > Conditional Access",
          "details": "In the left menu, expand 'Security' and click 'Conditional Access'",
          "what_to_look_for": "You should see the Conditional Access policies list"
        }},
        {{
          "step_number": 3,
          "action": "Configure specific setting",
          "details": "Exact configuration details with field names and values",
          "what_to_look_for": "What the user should see after configuration"
        }}
      ],
      "verification_steps": [
        "Step 1: How to verify the setting",
        "Step 2: What to check to confirm it's working"
      ],
      "expected_outcome": "What compliance requirement this achieves",
      "framework_reference": "Specific {framework_names.get(fw_name, fw_name)} requirement/control",
      "additional_notes": "Any important warnings or considerations"
    }}
  ],
  "summary": "Brief summary of checklist"
}}

CRITICAL REQUIREMENTS:
- Provide EXACT Azure Portal navigation paths (menu items, section names)
- Include specific setting names as they appear in Azure Portal
- Give precise configuration values (not generic descriptions)
- Include verification steps to confirm settings are applied
- Reference actual Azure features/services with their exact names
- Order by priority (CRITICAL first)
- Make every step actionable and specific to Azure Portal UI
- Include what users should see at each step for validation
"""
            
            try:
                ai_response = rate_limited_generate_content_optimized(prompt, temperature=0.0, max_tokens=8000)  # Set to 0.0 for deterministic responses
                logger.info(f"AI response received for {fw_name}, length: {len(ai_response)}")
                
                # Parse AI response
                try:
                    # Try to extract JSON from response
                    cleaned_response = ai_response.strip()
                    
                    # Remove markdown code blocks
                    if '```json' in cleaned_response:
                        json_start = cleaned_response.find('```json') + 7
                        json_end = cleaned_response.find('```', json_start)
                        if json_end > json_start:
                            cleaned_response = cleaned_response[json_start:json_end].strip()
                    elif '```' in cleaned_response:
                        json_start = cleaned_response.find('```') + 3
                        json_end = cleaned_response.find('```', json_start)
                        if json_end > json_start:
                            cleaned_response = cleaned_response[json_start:json_end].strip()
                    
                    # Try to find JSON object boundaries
                    if '{' in cleaned_response and '}' in cleaned_response:
                        first_brace = cleaned_response.find('{')
                        last_brace = cleaned_response.rfind('}')
                        if last_brace > first_brace:
                            cleaned_response = cleaned_response[first_brace:last_brace+1]
                    
                    checklist_data = json.loads(cleaned_response)
                    parsed_items = checklist_data.get('checklist_items', [])
                    
                    if parsed_items:
                        logger.info(f"Successfully parsed {len(parsed_items)} checklist items from AI for {fw_name}")
                        checklist_items.extend(parsed_items)
                    else:
                        raise ValueError("No checklist items found in AI response")
                except (json.JSONDecodeError, ValueError) as parse_error:
                    logger.error(f"Failed to parse AI response for {fw_name}: {parse_error}")
                    logger.debug(f"AI Response (first 500 chars): {ai_response[:500]}")
                    
                    # Smart fallback: Create gap-specific checklist items with intelligent mapping
                    for idx, gap in enumerate(gaps):
                        gap_lower = gap.lower()
                        
                        # Intelligent Azure service and path mapping based on gap content
                        azure_services = []
                        portal_path = 'Azure Portal'
                        setting_name = 'Configuration required'
                        
                        # Map gaps to specific Azure services and paths
                        if 'workstation' in gap_lower or 'administrator' in gap_lower or 'admin' in gap_lower:
                            azure_services = ['Azure AD', 'Privileged Identity Management (PIM)', 'Azure AD Identity Protection']
                            portal_path = 'Azure Portal > Azure Active Directory > Security > Privileged Identity Management'
                            setting_name = 'Privileged Access Workstation (PAW) Configuration'
                        elif 'certificate' in gap_lower or 'x.509' in gap_lower or 'x509' in gap_lower:
                            azure_services = ['Azure Key Vault', 'Azure AD', 'Certificate Management']
                            portal_path = 'Azure Portal > Azure Key Vault > Certificates'
                            setting_name = 'X.509 Certificate Management Configuration'
                        elif 'service model' in gap_lower or 'iaas' in gap_lower or 'paas' in gap_lower or 'saas' in gap_lower:
                            azure_services = ['Azure Policy', 'Azure Security Center', 'Azure Governance']
                            portal_path = 'Azure Portal > Azure Policy > Definitions'
                            setting_name = 'Cloud Service Model Security Configuration'
                        elif 'conditional access' in gap_lower or 'mfa' in gap_lower or 'multi-factor' in gap_lower:
                            azure_services = ['Azure AD', 'Conditional Access']
                            portal_path = 'Azure Portal > Azure Active Directory > Security > Conditional Access > Policies'
                            setting_name = 'Conditional Access Policy Configuration'
                        elif 'encryption' in gap_lower or 'data protection' in gap_lower:
                            azure_services = ['Azure Key Vault', 'Azure Storage', 'Azure Disk Encryption']
                            portal_path = 'Azure Portal > Azure Key Vault > Keys'
                            setting_name = 'Encryption Configuration'
                        elif 'monitoring' in gap_lower or 'logging' in gap_lower or 'audit' in gap_lower:
                            azure_services = ['Azure Monitor', 'Azure Log Analytics', 'Azure Sentinel']
                            portal_path = 'Azure Portal > Azure Monitor > Logs'
                            setting_name = 'Monitoring and Logging Configuration'
                        elif 'network' in gap_lower or 'firewall' in gap_lower or 'nsg' in gap_lower:
                            azure_services = ['Azure Network Security Groups', 'Azure Firewall', 'Virtual Network']
                            portal_path = 'Azure Portal > Network Security Groups'
                            setting_name = 'Network Security Configuration'
                        else:
                            azure_services = ['Azure AD', 'Azure Policy', 'Azure Security Center']
                            portal_path = 'Azure Portal > Azure Active Directory > Overview'
                            setting_name = 'Security Configuration'
                        
                        # Create detailed implementation steps based on gap
                        implementation_steps = [
                            {
                                'step_number': 1,
                                'action': f"Navigate to {portal_path}",
                                'details': f"Open Azure Portal (portal.azure.com) and navigate to the specified path in the left navigation menu",
                                'what_to_look_for': f"You should see the {setting_name} configuration page"
                            },
                            {
                                'step_number': 2,
                                'action': f"Review current {setting_name} settings",
                                'details': f"Examine the current configuration for {gap[:60]}",
                                'what_to_look_for': 'Current settings and configuration options'
                            },
                            {
                                'step_number': 3,
                                'action': f"Configure {setting_name} to address the gap",
                                'details': f"Update the settings to ensure compliance with {framework_names.get(fw_name, fw_name)} requirements for: {gap[:80]}",
                                'what_to_look_for': 'Configuration saved confirmation message'
                            },
                            {
                                'step_number': 4,
                                'action': 'Save and apply the configuration',
                                'details': 'Click Save/Apply button to commit the changes',
                                'what_to_look_for': 'Success notification confirming the configuration was saved'
                            }
                        ]
                        
                        checklist_items.append({
                            'id': len(checklist_items) + 1,
                            'title': f"Configure {setting_name} for {gap[:70]}",
                            'description': f"Implement {setting_name} to address the compliance gap: {gap}. This configuration ensures adherence to {framework_names.get(fw_name, fw_name)} requirements.",
                            'gap_addressed': gap,
                            'priority': 'HIGH' if 'critical' in gap_lower or 'security' in gap_lower else 'MEDIUM',
                            'effort': 'Complex' if 'certificate' in gap_lower or 'workstation' in gap_lower else 'Moderate',
                            'azure_services': azure_services,
                            'azure_portal_path': portal_path,
                            'azure_portal_url': None,
                            'settings_to_configure': {
                                'setting_name': setting_name,
                                'current_value': 'Needs to be reviewed and configured',
                                'required_value': f"Compliant {setting_name} per {framework_names.get(fw_name, fw_name)} requirements",
                                'location': portal_path
                            },
                            'implementation_steps': implementation_steps,
                            'verification_steps': [
                                f"Verify {setting_name} is configured correctly in {portal_path}",
                                f"Confirm the configuration addresses: {gap[:80]}",
                                'Test the configuration to ensure it works as expected',
                                'Document the configuration changes for audit purposes'
                            ],
                            'expected_outcome': f"Successfully configured {setting_name} to address: {gap[:100]}",
                            'framework_reference': f"{framework_names.get(fw_name, fw_name)} compliance requirement",
                            'additional_notes': f"Refer to Azure documentation for {setting_name} and {framework_names.get(fw_name, fw_name)} best practices. Consider testing in a non-production environment first."
                        })
            except Exception as e:
                logger.error(f"Error generating checklist for {fw_name}: {e}")
                # Use smart fallback with gap-specific mapping
                for idx, gap in enumerate(gaps):
                    gap_lower = gap.lower()
                    
                    # Intelligent Azure service and path mapping
                    azure_services = []
                    portal_path = 'Azure Portal'
                    setting_name = 'Configuration required'
                    
                    if 'workstation' in gap_lower or 'administrator' in gap_lower or 'admin' in gap_lower:
                        azure_services = ['Azure AD', 'Privileged Identity Management (PIM)', 'Azure AD Identity Protection']
                        portal_path = 'Azure Portal > Azure Active Directory > Security > Privileged Identity Management'
                        setting_name = 'Privileged Access Workstation (PAW) Configuration'
                    elif 'certificate' in gap_lower or 'x.509' in gap_lower or 'x509' in gap_lower:
                        azure_services = ['Azure Key Vault', 'Azure AD', 'Certificate Management']
                        portal_path = 'Azure Portal > Azure Key Vault > Certificates'
                        setting_name = 'X.509 Certificate Management Configuration'
                    elif 'service model' in gap_lower or 'iaas' in gap_lower or 'paas' in gap_lower or 'saas' in gap_lower:
                        azure_services = ['Azure Policy', 'Azure Security Center', 'Azure Governance']
                        portal_path = 'Azure Portal > Azure Policy > Definitions'
                        setting_name = 'Cloud Service Model Security Configuration'
                    else:
                        azure_services = ['Azure AD', 'Azure Policy', 'Azure Security Center']
                        portal_path = 'Azure Portal > Azure Active Directory > Overview'
                        setting_name = 'Security Configuration'
                    
                    implementation_steps = [
                        {
                            'step_number': 1,
                            'action': f"Navigate to {portal_path}",
                            'details': f"Open Azure Portal (portal.azure.com) and navigate to the specified path",
                            'what_to_look_for': f"You should see the {setting_name} configuration page"
                        },
                        {
                            'step_number': 2,
                            'action': f"Configure {setting_name}",
                            'details': f"Update settings to address: {gap[:80]}",
                            'what_to_look_for': 'Configuration options and save button'
                        },
                        {
                            'step_number': 3,
                            'action': 'Save and verify',
                            'details': 'Save the configuration and verify it was applied',
                            'what_to_look_for': 'Success confirmation message'
                        }
                    ]
                    
                    checklist_items.append({
                        'id': len(checklist_items) + 1,
                        'title': f"Configure {setting_name} for {gap[:70]}",
                        'description': f"Implement {setting_name} to address: {gap}",
                        'gap_addressed': gap,
                        'priority': 'HIGH',
                        'effort': 'Moderate',
                        'azure_services': azure_services,
                        'azure_portal_path': portal_path,
                        'settings_to_configure': {
                            'setting_name': setting_name,
                            'current_value': 'Needs configuration',
                            'required_value': f"Compliant {setting_name} per {framework_names.get(fw_name, fw_name)}",
                            'location': portal_path
                        },
                        'implementation_steps': implementation_steps,
                        'verification_steps': [
                            f"Verify {setting_name} is configured in {portal_path}",
                            f"Confirm it addresses: {gap[:80]}"
                        ],
                        'expected_outcome': f"Resolve gap: {gap}",
                        'framework_reference': framework_names.get(fw_name, fw_name),
                        'additional_notes': f"Refer to Azure documentation for {setting_name}"
                    })
        
        # Sort by priority
        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        checklist_items.sort(key=lambda x: priority_order.get(x.get('priority', 'MEDIUM'), 3))
        
        # Add IDs if missing
        for idx, item in enumerate(checklist_items):
            if 'id' not in item:
                item['id'] = idx + 1
        
        # Get user's organization_id if available
        user_doc = await db.users.find_one({"_id": current_user.id})
        organization_id = user_doc.get('organization_id') if user_doc else None
        
        # Save checklist to MongoDB
        checklist_document = {
            'user_id': current_user.id,
            'user_email': current_user.email,
            'organization_id': organization_id,
            'result_id': result_id,
            'analysis_result_id': result_obj_id,
            'document_name': result.get('document_name', 'Unknown'),
            'framework': framework if framework else 'all',
            'frameworks': frameworks_to_process,
            'checklist_items': checklist_items,
            'total_items': len(checklist_items),
            'generated_at': datetime.utcnow(),
            'summary': f"Generated {len(checklist_items)} actionable checklist items to achieve full compliance"
        }
        
        try:
            checklist_result = await db.compliance_checklists.insert_one(checklist_document)
            checklist_id = str(checklist_result.inserted_id)
            logger.info(f"Compliance checklist saved to MongoDB with ID: {checklist_id}")
        except Exception as e:
            logger.error(f"Error saving compliance checklist to MongoDB: {e}")
            checklist_id = None
        
        # Create activity log entry for checklist generation
        try:
            activity_log = {
                'user_id': current_user.id,
                'user_email': current_user.email,
                'organization_id': organization_id,
                'activity_type': 'checklist_generation',
                'activity_label': 'Compliance Checklist Generated',
                'description': f"Generated compliance checklist for {result.get('document_name', 'Unknown')} - {len(checklist_items)} items for {', '.join([fw.upper() if fw != 'gdpr' else 'GDPR' for fw in frameworks_to_process])}",
                'status': 'success',
                'details': {
                    'checklist_id': checklist_id,
                    'result_id': result_id,
                    'document_name': result.get('document_name', 'Unknown'),
                    'framework': framework if framework else 'all',
                    'frameworks': frameworks_to_process,
                    'total_items': len(checklist_items)
                },
                'timestamp': datetime.utcnow(),
                'icon': '✅'
            }
            await db.activity_logs.insert_one(activity_log)
            logger.info(f"Activity log created for checklist generation: {checklist_id}")
        except Exception as e:
            logger.error(f"Error creating activity log for checklist generation: {e}")
        
        # Create response
        response = {
            'checklist_id': checklist_id,
            'result_id': result_id,
            'document_name': result.get('document_name', 'Unknown'),
            'frameworks': frameworks_to_process,
            'checklist_items': checklist_items,
            'total_items': len(checklist_items),
            'generated_at': datetime.utcnow().isoformat(),
            'summary': f"Generated {len(checklist_items)} actionable checklist items to achieve full compliance"
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating compliance checklist: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating checklist: {str(e)}"
        )


@router.post("/export-checklist-pdf/{result_id}")
async def export_checklist_pdf(
    result_id: str,
    framework: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db)
):
    """
    Export compliance checklist as a detailed PDF with Azure portal navigation instructions
    """
    try:
        from bson import ObjectId
        from bson.errors import InvalidId
        
        # Validate result_id
        try:
            result_obj_id = ObjectId(result_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid result ID format")
        
        # Fetch analysis result
        result = await db.azure_compliance_results.find_one({"_id": result_obj_id})
        if not result:
            raise HTTPException(status_code=404, detail="Analysis result not found")
        
        # Check user access
        if str(result.get('user_id')) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied to this analysis result")
        
        # Generate checklist first - call the function directly
        # Get frameworks to process
        frameworks_to_process = []
        if framework:
            if framework in result.get('frameworks', {}):
                frameworks_to_process = [framework]
            else:
                raise HTTPException(status_code=400, detail=f"Framework '{framework}' not found in analysis")
        else:
            frameworks_to_process = [
                fw for fw, fw_data in result.get('frameworks', {}).items()
                if fw_data.get('gaps') and len(fw_data.get('gaps', [])) > 0
            ]
        
        if not frameworks_to_process:
            raise HTTPException(
                status_code=400,
                detail="No frameworks with identified gaps found. Cannot generate checklist."
            )
        
        # Framework display names
        framework_names = {
            'gdpr': 'GDPR',
            'iso27001': 'ISO 27001',
            'iso27018': 'ISO 27018',
            'iso27017': 'ISO 27017',
            'azure': 'Azure Best Practices'
        }
        
        # Generate full checklist using the same logic as the main endpoint
        # We'll call the generate_compliance_checklist function logic inline
        checklist_items = []
        
        for fw_name in frameworks_to_process:
            fw_data = result.get('frameworks', {}).get(fw_name, {})
            gaps = fw_data.get('gaps', [])
            compliant_areas = fw_data.get('compliant_areas', [])
            recommendation = fw_data.get('recommendation', '')
            key_requirements = fw_data.get('key_requirements', [])
            score = fw_data.get('score', 0)
            
            if not gaps:
                continue
            
            # Use AI to generate detailed checklist (same prompt as main endpoint)
            from compliance_rag import rate_limited_generate_content_optimized
            prompt = f"""You are an Azure compliance expert creating a detailed, actionable checklist for Azure portal implementation to achieve full {framework_names.get(fw_name, fw_name)} compliance.

ANALYSIS RESULTS:
- Current Compliance Score: {score}/100
- Framework: {framework_names.get(fw_name, fw_name)}
- Identified Gaps: {json.dumps(gaps, indent=2)}
- Compliant Areas: {json.dumps(compliant_areas, indent=2)}
- Key Requirements: {json.dumps(key_requirements, indent=2)}
- Recommendation: {recommendation}

TASK:
Create a comprehensive, actionable checklist that addresses ALL identified gaps. Each checklist item MUST include:

1. **Exact Azure Portal Navigation Path**: Step-by-step portal navigation (e.g., "Azure Portal > Azure Active Directory > Security > Conditional Access > Policies")
2. **Specific Settings to Configure**: Exact setting names, values, and configurations
3. **Detailed Step-by-Step Instructions**: Precise clicks, selections, and configurations
4. **Azure Portal URLs/Paths**: Direct links or exact navigation paths where possible
5. **Screenshots Guidance**: What users should see at each step
6. **Verification Steps**: How to verify the setting was applied correctly

FORMAT YOUR RESPONSE AS JSON:
{{
  "framework": "{framework_names.get(fw_name, fw_name)}",
  "current_score": {score},
  "target_score": 100,
  "checklist_items": [
    {{
      "id": 1,
      "title": "Specific actionable item title",
      "description": "Detailed description of what needs to be done and why",
      "gap_addressed": "Which gap this item addresses",
      "priority": "CRITICAL|HIGH|MEDIUM|LOW",
      "effort": "Quick|Moderate|Complex",
      "azure_services": ["Azure Service 1", "Azure Service 2"],
      "azure_portal_path": "Exact navigation path in Azure Portal",
      "azure_portal_url": "Direct URL or portal path (if applicable)",
      "settings_to_configure": {{
        "setting_name": "Exact setting name",
        "current_value": "What it likely is now",
        "required_value": "What it should be",
        "location": "Where in the portal this setting is located"
      }},
      "implementation_steps": [
        {{
          "step_number": 1,
          "action": "Navigate to Azure Portal > Azure Active Directory",
          "details": "Click on 'Azure Active Directory' in the left navigation menu",
          "what_to_look_for": "You should see the Azure AD overview page"
        }},
        {{
          "step_number": 2,
          "action": "Go to Security > Conditional Access",
          "details": "In the left menu, expand 'Security' and click 'Conditional Access'",
          "what_to_look_for": "You should see the Conditional Access policies list"
        }},
        {{
          "step_number": 3,
          "action": "Configure specific setting",
          "details": "Exact configuration details with field names and values",
          "what_to_look_for": "What the user should see after configuration"
        }}
      ],
      "verification_steps": [
        "Step 1: How to verify the setting",
        "Step 2: What to check to confirm it's working"
      ],
      "expected_outcome": "What compliance requirement this achieves",
      "framework_reference": "Specific {framework_names.get(fw_name, fw_name)} requirement/control",
      "additional_notes": "Any important warnings or considerations"
    }}
  ],
  "summary": "Brief summary of checklist"
}}

CRITICAL REQUIREMENTS:
- Provide EXACT Azure Portal navigation paths (menu items, section names)
- Include specific setting names as they appear in Azure Portal
- Give precise configuration values (not generic descriptions)
- Include verification steps to confirm settings are applied
- Reference actual Azure features/services with their exact names
- Order by priority (CRITICAL first)
- Make every step actionable and specific to Azure Portal UI
- Include what users should see at each step for validation
"""
            
            try:
                ai_response = rate_limited_generate_content_optimized(prompt, temperature=0.0, max_tokens=8000)  # Set to 0.0 for deterministic responses
                logger.info(f"AI response received for {fw_name} (PDF), length: {len(ai_response)}")
                
                # Parse AI response
                try:
                    if '```json' in ai_response:
                        json_start = ai_response.find('```json') + 7
                        json_end = ai_response.find('```', json_start)
                        ai_response = ai_response[json_start:json_end].strip()
                    elif '```' in ai_response:
                        json_start = ai_response.find('```') + 3
                        json_end = ai_response.find('```', json_start)
                        ai_response = ai_response[json_start:json_end].strip()
                    
                    checklist_data = json.loads(ai_response)
                    checklist_items.extend(checklist_data.get('checklist_items', []))
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse AI response for {fw_name} in PDF export")
                    # Use smart fallback with gap-specific mapping (same as main endpoint)
                    for idx, gap in enumerate(gaps):
                        gap_lower = gap.lower()
                        
                        if 'workstation' in gap_lower or 'administrator' in gap_lower or 'admin' in gap_lower:
                            azure_services = ['Azure AD', 'Privileged Identity Management (PIM)', 'Azure AD Identity Protection']
                            portal_path = 'Azure Portal > Azure Active Directory > Security > Privileged Identity Management'
                            setting_name = 'Privileged Access Workstation (PAW) Configuration'
                        elif 'certificate' in gap_lower or 'x.509' in gap_lower or 'x509' in gap_lower:
                            azure_services = ['Azure Key Vault', 'Azure AD', 'Certificate Management']
                            portal_path = 'Azure Portal > Azure Key Vault > Certificates'
                            setting_name = 'X.509 Certificate Management Configuration'
                        elif 'service model' in gap_lower or 'iaas' in gap_lower or 'paas' in gap_lower or 'saas' in gap_lower:
                            azure_services = ['Azure Policy', 'Azure Security Center', 'Azure Governance']
                            portal_path = 'Azure Portal > Azure Policy > Definitions'
                            setting_name = 'Cloud Service Model Security Configuration'
                        else:
                            azure_services = ['Azure AD', 'Azure Policy', 'Azure Security Center']
                            portal_path = 'Azure Portal > Azure Active Directory > Overview'
                            setting_name = 'Security Configuration'
                        
                        checklist_items.append({
                            'id': len(checklist_items) + 1,
                            'title': f"Configure {setting_name} for {gap[:70]}",
                            'description': f"Implement {setting_name} to address: {gap}",
                            'gap_addressed': gap,
                            'priority': 'HIGH',
                            'effort': 'Moderate',
                            'azure_services': azure_services,
                            'azure_portal_path': portal_path,
                            'settings_to_configure': {
                                'setting_name': setting_name,
                                'current_value': 'Needs configuration',
                                'required_value': f"Compliant {setting_name} per {framework_names.get(fw_name, fw_name)}",
                                'location': portal_path
                            },
                            'implementation_steps': [
                                {
                                    'step_number': 1,
                                    'action': f"Navigate to {portal_path}",
                                    'details': f"Open Azure Portal (portal.azure.com) and navigate to the specified path",
                                    'what_to_look_for': f"You should see the {setting_name} configuration page"
                                },
                                {
                                    'step_number': 2,
                                    'action': f"Configure {setting_name}",
                                    'details': f"Update settings to address: {gap[:80]}",
                                    'what_to_look_for': 'Configuration options and save button'
                                },
                                {
                                    'step_number': 3,
                                    'action': 'Save and verify',
                                    'details': 'Save the configuration and verify it was applied',
                                    'what_to_look_for': 'Success confirmation message'
                                }
                            ],
                            'verification_steps': [
                                f"Verify {setting_name} is configured in {portal_path}",
                                f"Confirm it addresses: {gap[:80]}"
                            ],
                            'expected_outcome': f"Resolve gap: {gap}",
                            'framework_reference': framework_names.get(fw_name, fw_name),
                            'additional_notes': f"Refer to Azure documentation for {setting_name}"
                        })
            except Exception as e:
                logger.error(f"Error generating checklist for {fw_name} in PDF: {e}")
                # Fallback
                for idx, gap in enumerate(gaps):
                    checklist_items.append({
                        'id': len(checklist_items) + 1,
                        'title': f"Address: {gap[:100]}",
                        'description': gap,
                        'gap_addressed': gap,
                        'priority': 'HIGH',
                        'effort': 'Moderate',
                        'azure_services': ['Azure AD', 'Azure Policy'],
                        'azure_portal_path': 'Azure Portal > Azure Active Directory > [Configure based on gap]',
                        'settings_to_configure': {
                            'setting_name': 'Configuration required',
                            'current_value': 'To be determined',
                            'required_value': 'Compliant configuration',
                            'location': 'Azure Portal'
                        },
                        'implementation_steps': [
                            {
                                'step_number': 1,
                                'action': f"Navigate to Azure Portal to address: {gap[:50]}",
                                'details': 'Review the gap and identify the appropriate Azure service',
                                'what_to_look_for': 'Azure Portal dashboard'
                            }
                        ],
                        'verification_steps': ['Verify the setting has been applied'],
                        'expected_outcome': f"Resolve gap: {gap}",
                        'framework_reference': framework_names.get(fw_name, fw_name)
                    })
        
        # Sort by priority
        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        checklist_items.sort(key=lambda x: priority_order.get(x.get('priority', 'MEDIUM'), 3))
        
        # Add IDs if missing
        for idx, item in enumerate(checklist_items):
            if 'id' not in item:
                item['id'] = idx + 1
        
        checklist = {
            'frameworks': frameworks_to_process,
            'checklist_items': checklist_items,
            'total_items': len(checklist_items)
        }
        
        # Create PDF
        from io import BytesIO
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=12,
            alignment=TA_CENTER
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=8,
            spaceBefore=12
        )
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#374151'),
            spaceAfter=6,
            spaceBefore=8
        )
        
        # Title
        story.append(Paragraph("Azure Compliance Implementation Checklist", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Document info
        info_data = [
            ['Document:', result.get('document_name', 'Unknown')],
            ['Frameworks:', ', '.join([fw.upper() if fw != 'gdpr' else 'GDPR' for fw in checklist.get('frameworks', [])])],
            ['Total Items:', str(checklist.get('total_items', 0))],
            ['Generated:', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')]
        ]
        info_table = Table(info_data, colWidths=[1.5*inch, 4.5*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Checklist items
        for idx, item in enumerate(checklist.get('checklist_items', []), 1):
            # Item header
            priority_colors = {
                'CRITICAL': colors.HexColor('#dc2626'),
                'HIGH': colors.HexColor('#ea580c'),
                'MEDIUM': colors.HexColor('#ca8a04'),
                'LOW': colors.HexColor('#2563eb')
            }
            
            item_title = f"Item #{item.get('id', idx)}: {item.get('title', 'Untitled')}"
            story.append(Paragraph(item_title, heading_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Priority and Effort badges
            priority = item.get('priority', 'MEDIUM')
            effort = item.get('effort', 'Moderate')
            badge_data = [
                ['Priority:', priority, 'Effort:', effort]
            ]
            badge_table = Table(badge_data, colWidths=[0.8*inch, 1.2*inch, 0.8*inch, 1.2*inch])
            badge_table.setStyle(TableStyle([
                ('BACKGROUND', (1, 0), (1, 0), priority_colors.get(priority, colors.grey)),
                ('BACKGROUND', (3, 0), (3, 0), colors.HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('TEXTCOLOR', (1, 0), (1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (3, 0), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(badge_table)
            story.append(Spacer(1, 0.15*inch))
            
            # Description
            story.append(Paragraph("<b>Description:</b>", subheading_style))
            story.append(Paragraph(item.get('description', 'No description'), styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
            
            # Gap Addressed
            story.append(Paragraph(f"<b>Gap Addressed:</b> {item.get('gap_addressed', 'N/A')}", styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
            
            # Azure Portal Path
            portal_path = item.get('azure_portal_path', 'N/A')
            if portal_path:
                story.append(Paragraph(f"<b>Azure Portal Navigation:</b> {portal_path}", styles['Normal']))
                story.append(Spacer(1, 0.1*inch))
            
            # Settings to Configure
            settings = item.get('settings_to_configure', {})
            if settings and isinstance(settings, dict):
                story.append(Paragraph("<b>Settings to Configure:</b>", subheading_style))
                settings_data = [
                    ['Setting Name:', settings.get('setting_name', 'N/A')],
                    ['Current Value:', settings.get('current_value', 'N/A')],
                    ['Required Value:', settings.get('required_value', 'N/A')],
                    ['Location:', settings.get('location', 'N/A')]
                ]
                settings_table = Table(settings_data, colWidths=[1.5*inch, 4.5*inch])
                settings_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
                ]))
                story.append(settings_table)
                story.append(Spacer(1, 0.15*inch))
            
            # Implementation Steps
            steps = item.get('implementation_steps', [])
            if steps:
                story.append(Paragraph("<b>Step-by-Step Implementation Guide:</b>", subheading_style))
                for step in steps:
                    if isinstance(step, dict):
                        step_num = step.get('step_number', '')
                        action = step.get('action', '')
                        details = step.get('details', '')
                        look_for = step.get('what_to_look_for', '')
                        
                        step_text = f"<b>Step {step_num}: {action}</b><br/>"
                        if details:
                            step_text += f"{details}<br/>"
                        if look_for:
                            step_text += f"<i>What to look for: {look_for}</i>"
                        
                        story.append(Paragraph(step_text, styles['Normal']))
                        story.append(Spacer(1, 0.08*inch))
                    else:
                        # Fallback for string steps
                        story.append(Paragraph(f"• {step}", styles['Normal']))
                        story.append(Spacer(1, 0.05*inch))
                story.append(Spacer(1, 0.1*inch))
            
            # Verification Steps
            verification = item.get('verification_steps', [])
            if verification:
                story.append(Paragraph("<b>Verification Steps:</b>", subheading_style))
                for v_step in verification:
                    story.append(Paragraph(f"• {v_step}", styles['Normal']))
                story.append(Spacer(1, 0.1*inch))
            
            # Azure Services
            services = item.get('azure_services', [])
            if services:
                story.append(Paragraph(f"<b>Azure Services Required:</b> {', '.join(services)}", styles['Normal']))
                story.append(Spacer(1, 0.1*inch))
            
            # Expected Outcome
            outcome = item.get('expected_outcome', '')
            if outcome:
                story.append(Paragraph(f"<b>Expected Outcome:</b> {outcome}", styles['Normal']))
                story.append(Spacer(1, 0.1*inch))
            
            # Framework Reference
            framework_ref = item.get('framework_reference', '')
            if framework_ref:
                story.append(Paragraph(f"<b>Framework Reference:</b> {framework_ref}", styles['Normal']))
                story.append(Spacer(1, 0.1*inch))
            
            # Additional Notes
            notes = item.get('additional_notes', '')
            if notes:
                story.append(Paragraph(f"<b>Additional Notes:</b> {notes}", styles['Normal']))
                story.append(Spacer(1, 0.1*inch))
            
            # Page break between items (except last)
            if idx < len(checklist.get('checklist_items', [])):
                story.append(PageBreak())
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Generate filename
        frameworks_str = '_'.join(checklist.get('frameworks', []))
        filename = f"compliance_checklist_{frameworks_str}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = REPORTS_DIR / filename
        
        # Save to file
        with open(filepath, 'wb') as f:
            f.write(buffer.getvalue())
        
        logger.info(f"Checklist PDF generated: {filepath}")
        
        return FileResponse(
            path=str(filepath),
            filename=filename,
            media_type='application/pdf'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating checklist PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating checklist PDF: {str(e)}"
        )


@router.get("/generate-report/{result_id}")
async def generate_report_from_saved(
    result_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db)
):
    """
    Generate PDF report from a saved analysis result
    """
    try:
        from bson import ObjectId
        from bson.errors import InvalidId
        
        # Validate result_id format
        if not result_id or not result_id.strip():
            raise HTTPException(
                status_code=400,
                detail="Invalid result ID. Please provide a valid analysis result ID."
            )
        
        # Validate ObjectId format
        try:
            object_id = ObjectId(result_id)
        except (InvalidId, Exception) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid result ID format: {result_id}. Please provide a valid MongoDB ObjectId."
            )
        
        # Get saved result from database
        # For management_team, allow access to any report
        # For others, only allow access to their own reports
        if current_user.role == 'management_team':
            result = await db.azure_compliance_results.find_one({
                "_id": object_id
            })
        else:
            result = await db.azure_compliance_results.find_one({
                "_id": object_id,
                "user_id": current_user.id
            })
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Analysis result not found. The result may have been deleted or you may not have permission to access it."
            )
        
        # Convert to analysis_data format - include all comprehensive details
        # Check if this is a multi-framework result (new format) or legacy single-framework
        frameworks = result.get('frameworks', {})
        framework_scores = result.get('framework_scores', {})
        
        # Use overall_score if available, otherwise fall back to score
        overall_score = result.get('overall_score', result.get('score', 0))
        
        analysis_data = {
            'document_name': result.get('document_name', 'N/A'),
            'analyzed_at': result.get('analyzed_at', result.get('created_at', datetime.utcnow())),
            'analyzed_by': result.get('user_email', current_user.email),
            'overall_score': overall_score,
            'score': overall_score,  # For backward compatibility
            'overall_status': result.get('overall_status', 'Unknown'),
            'frameworks': frameworks,  # Detailed framework analysis
            'framework_scores': framework_scores,  # Framework scores summary
            'frameworks_analyzed': result.get('frameworks_analyzed', len(frameworks) if frameworks else 1),
            'summary': result.get('summary', 'No summary available.'),
            # Legacy fields for backward compatibility
            'categories_analyzed': result.get('categories_analyzed', 0),
            'total_checks': result.get('total_checks', 0),
            'findings': result.get('findings', [])  # Legacy findings format
        }
        
        # Convert datetime to string if needed
        if isinstance(analysis_data['analyzed_at'], datetime):
            analysis_data['analyzed_at'] = analysis_data['analyzed_at'].isoformat()
        elif not isinstance(analysis_data['analyzed_at'], str):
            analysis_data['analyzed_at'] = datetime.utcnow().isoformat()
        
        # Generate PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"azure_compliance_report_{timestamp}.pdf"
        filepath = REPORTS_DIR / filename
        
        # Create PDF
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        # Determine if this is a multi-framework report or legacy single-framework
        frameworks = analysis_data.get('frameworks', {})
        is_multi_framework = bool(frameworks and len(frameworks) > 0)
        
        if is_multi_framework:
            # Use the comprehensive multi-framework report format
            story.append(Paragraph("Multi-Framework Compliance Report", title_style))
        else:
            story.append(Paragraph("Azure Compliance Report", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Document Info
        analyzed_at_str = analysis_data['analyzed_at']
        if isinstance(analyzed_at_str, str) and len(analyzed_at_str) > 10:
            analyzed_at_str = analyzed_at_str[:10]
        elif analyzed_at_str == 'N/A':
            analyzed_at_str = 'N/A'
        else:
            analyzed_at_str = 'N/A'
        
        info_data = [
            ['Document:', analysis_data['document_name']],
            ['Analyzed By:', analysis_data['analyzed_by']],
            ['Analysis Date:', analyzed_at_str],
            ['Overall Score:', f"{analysis_data['overall_score']}/100"],
            ['Status:', analysis_data['overall_status']]
        ]
        
        if is_multi_framework:
            info_data.append(['Frameworks Analyzed:', str(analysis_data.get('frameworks_analyzed', len(frameworks)))])
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#dbeafe')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Framework Scores Summary Table (for multi-framework reports)
        if is_multi_framework and analysis_data.get('framework_scores'):
            story.append(Paragraph("Framework Compliance Scores", heading_style))
            
            framework_scores = analysis_data.get('framework_scores', {})
            framework_data = [['Framework', 'Score', 'Status']]
            
            for framework, score in framework_scores.items():
                status = 'Compliant' if score >= 80 else 'Partial' if score >= 60 else 'Non-Compliant'
                framework_name = {
                    'gdpr': 'GDPR',
                    'iso27001': 'ISO 27001',
                    'iso27017': 'ISO 27017',
                    'iso27018': 'ISO 27018',
                    'azure': 'Azure Best Practices'
                }.get(framework, framework.upper())
                
                framework_data.append([framework_name, f"{score}/100", status])
            
            framework_table = Table(framework_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
            framework_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ]))
            story.append(framework_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Summary
        story.append(Paragraph("Executive Summary", heading_style))
        summary_text = analysis_data.get('summary', 'No summary available.')
        story.append(Paragraph(summary_text.replace('\n', '<br/>'), styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Detailed Framework Analysis (for multi-framework reports)
        if is_multi_framework:
            story.append(PageBreak())
            story.append(Paragraph("Detailed Framework Analysis", heading_style))
            
            subheading_style = ParagraphStyle(
                'SubHeading',
                parent=styles['Heading3'],
                fontSize=14,
                textColor=colors.HexColor('#374151'),
                spaceAfter=10,
                spaceBefore=10,
                fontName='Helvetica-Bold'
            )
            
            for framework_name, framework_data in frameworks.items():
                # Framework header
                framework_display_name = {
                    'gdpr': 'GDPR (General Data Protection Regulation)',
                    'iso27001': 'ISO 27001:2022',
                    'iso27017': 'ISO 27017:2015',
                    'iso27018': 'ISO 27018:2019',
                    'azure': 'Azure Best Practices'
                }.get(framework_name, framework_name.upper())
                
                story.append(Spacer(1, 0.2*inch))
                story.append(Paragraph(framework_display_name, subheading_style))
                
                # Framework score and status
                framework_info = [
                    ['Score:', f"{framework_data.get('score', 0)}/100"],
                    ['Status:', framework_data.get('status', 'Unknown')],
                ]
                
                info_table = Table(framework_info, colWidths=[1*inch, 5*inch])
                info_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('PADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
                ]))
                story.append(info_table)
                story.append(Spacer(1, 0.1*inch))
                
                # Recommendation
                if framework_data.get('recommendation'):
                    story.append(Paragraph("<b>Recommendation:</b>", styles['Normal']))
                    story.append(Paragraph(framework_data.get('recommendation', '').replace('\n', '<br/>'), styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                
                # Gaps
                gaps = framework_data.get('gaps', [])
                if gaps:
                    story.append(Paragraph("<b>Gaps Identified:</b>", styles['Normal']))
                    for gap in gaps:
                        story.append(Paragraph(f"• {gap}", styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                
                # Compliant Areas
                compliant_areas = framework_data.get('compliant_areas', [])
                if compliant_areas:
                    story.append(Paragraph("<b>Compliant Areas:</b>", styles['Normal']))
                    for area in compliant_areas:
                        story.append(Paragraph(f"• {area}", styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                
                # Key Requirements
                key_requirements = framework_data.get('key_requirements', [])
                if key_requirements:
                    story.append(Paragraph("<b>Key Requirements:</b>", styles['Normal']))
                    for req in key_requirements:
                        story.append(Paragraph(f"• {req}", styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                
                # Priority Actions
                priority_actions = framework_data.get('priority_actions', [])
                if priority_actions:
                    story.append(Paragraph("<b>Priority Actions:</b>", styles['Normal']))
                    for idx, action in enumerate(priority_actions, 1):
                        story.append(Paragraph(f"{idx}. {action}", styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                
                story.append(Spacer(1, 0.2*inch))
        else:
            # Legacy single-framework findings
            story.append(Paragraph("Detailed Findings", heading_style))
            findings = analysis_data.get('findings', [])
            
            if findings:
                findings_data = [['Category', 'Status', 'Confidence', 'Recommendation']]
                for finding in findings:
                    recommendation = finding.get('recommendation', 'N/A')
                    rec_para = Paragraph(recommendation.replace('\n', '<br/>'), styles['Normal'])
                    
                    findings_data.append([
                        finding.get('category', 'N/A'),
                        finding.get('status', 'Unknown'),
                        f"{finding.get('confidence', 0):.1f}%",
                        rec_para
                    ])
                
                findings_table = Table(findings_data, colWidths=[1.2*inch, 0.9*inch, 0.8*inch, 3.6*inch])
                findings_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (2, -1), 'CENTER'),
                    ('ALIGN', (3, 0), (3, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('WORDWRAP', (3, 1), (3, -1)),
                ]))
                story.append(findings_table)
            else:
                story.append(Paragraph("No findings available.", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"PDF report generated: {filepath}")
        
        return FileResponse(
            path=str(filepath),
            filename=filename,
            media_type='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating report: {str(e)}"
        )


@router.post("/generate-report")
async def generate_compliance_report(
    analysis_data: dict,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Generate a PDF report from multi-framework analysis results
    """
    try:
        # Validate analysis_data
        if not analysis_data:
            raise HTTPException(
                status_code=400,
                detail="Analysis data is required. Please provide valid analysis results."
            )
        
        if not isinstance(analysis_data, dict):
            raise HTTPException(
                status_code=400,
                detail="Invalid analysis data format. Expected a dictionary/object."
            )
        
        # Validate required fields
        if 'overall_score' not in analysis_data and 'score' not in analysis_data:
            raise HTTPException(
                status_code=400,
                detail="Analysis data must contain 'overall_score' or 'score' field."
            )
        
        logger.info(f"Generating multi-framework PDF report for user: {current_user.email}")
        
        # Create unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"multi_framework_compliance_report_{timestamp}.pdf"
        filepath = REPORTS_DIR / filename
        
        # Create PDF
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Container for PDF elements
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=26,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        subheading_style = ParagraphStyle(
            'SubHeading',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#374151'),
            spaceAfter=10,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        )
        
        # Title
        story.append(Paragraph("Multi-Framework Compliance Report", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Document Info
        doc_name = analysis_data.get('document_name', 'N/A')
        analyzed_at = analysis_data.get('analyzed_at', 'N/A')
        analyzed_by = analysis_data.get('analyzed_by', current_user.email)
        overall_score = analysis_data.get('overall_score', analysis_data.get('score', 0))
        
        info_data = [
            ['Document:', doc_name],
            ['Analyzed By:', analyzed_by],
            ['Analysis Date:', analyzed_at[:10] if analyzed_at != 'N/A' else 'N/A'],
            ['Overall Score:', f"{overall_score}/100"],
            ['Status:', analysis_data.get('overall_status', 'Unknown')],
            ['Frameworks Analyzed:', str(analysis_data.get('frameworks_analyzed', 1))]
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#dbeafe')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Framework Scores Summary Table
        if analysis_data.get('framework_scores'):
            story.append(Paragraph("Framework Compliance Scores", heading_style))
            
            framework_scores = analysis_data.get('framework_scores', {})
            framework_data = [['Framework', 'Score', 'Status']]
            
            for framework, score in framework_scores.items():
                status = 'Compliant' if score >= 80 else 'Partial' if score >= 60 else 'Non-Compliant'
                framework_name = {
                    'gdpr': 'GDPR',
                    'iso27001': 'ISO 27001',
                    'iso27017': 'ISO 27017',
                    'iso27018': 'ISO 27018',
                    'azure': 'Azure Best Practices'
                }.get(framework, framework.upper())
                
                framework_data.append([framework_name, f"{score}/100", status])
            
            framework_table = Table(framework_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
            framework_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ]))
            story.append(framework_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Summary
        story.append(Paragraph("Executive Summary", heading_style))
        summary_text = analysis_data.get('summary', 'No summary available')
        story.append(Paragraph(summary_text.replace('\n', '<br/>'), styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Detailed Framework-Specific Findings
        story.append(PageBreak())
        story.append(Paragraph("Detailed Framework Analysis", heading_style))
        
        # Check if multi-framework results
        frameworks = analysis_data.get('frameworks', {})
        
        if frameworks:
            # Multi-framework detailed findings
            for framework_name, framework_data in frameworks.items():
                # Framework header
                framework_display_name = {
                    'gdpr': 'GDPR (General Data Protection Regulation)',
                    'iso27001': 'ISO 27001:2022',
                    'iso27017': 'ISO 27017:2015',
                    'iso27018': 'ISO 27018:2019',
                    'azure': 'Azure Best Practices'
                }.get(framework_name, framework_name.upper())
                
                story.append(Spacer(1, 0.2*inch))
                story.append(Paragraph(framework_display_name, subheading_style))
                
                # Framework score and status
                framework_info = [
                    ['Score:', f"{framework_data.get('score', 0)}/100"],
                    ['Status:', framework_data.get('status', 'Unknown')],
                ]
                
                info_table = Table(framework_info, colWidths=[1*inch, 5*inch])
                info_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('PADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
                ]))
                story.append(info_table)
                story.append(Spacer(1, 0.1*inch))
                
                # Recommendation
                if framework_data.get('recommendation'):
                    story.append(Paragraph("<b>Recommendation:</b>", styles['Normal']))
                    story.append(Paragraph(framework_data.get('recommendation', '').replace('\n', '<br/>'), styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                
                # Gaps
                gaps = framework_data.get('gaps', [])
                if gaps:
                    story.append(Paragraph("<b>Gaps Identified:</b>", styles['Normal']))
                    for gap in gaps:
                        story.append(Paragraph(f"• {gap}", styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                
                # Compliant Areas
                compliant_areas = framework_data.get('compliant_areas', [])
                if compliant_areas:
                    story.append(Paragraph("<b>Compliant Areas:</b>", styles['Normal']))
                    for area in compliant_areas:
                        story.append(Paragraph(f"• {area}", styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                
                # Key Requirements
                key_requirements = framework_data.get('key_requirements', [])
                if key_requirements:
                    story.append(Paragraph("<b>Key Requirements:</b>", styles['Normal']))
                    for req in key_requirements:
                        story.append(Paragraph(f"• {req}", styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                
                # Priority Actions
                priority_actions = framework_data.get('priority_actions', [])
                if priority_actions:
                    story.append(Paragraph("<b>Priority Actions:</b>", styles['Normal']))
                    for idx, action in enumerate(priority_actions, 1):
                        story.append(Paragraph(f"{idx}. {action}", styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                
                story.append(Spacer(1, 0.2*inch))
        else:
            # Legacy single-framework findings
            findings = analysis_data.get('findings', [])
            if findings:
                findings_data = [['Category', 'Status', 'Confidence', 'Recommendation']]
                
                for finding in findings:
                    category = finding.get('category', 'N/A')
                    status = finding.get('status', 'N/A')
                    confidence = f"{finding.get('confidence', 0):.1f}%"
                    recommendation = finding.get('recommendation', 'N/A')
                    rec_para = Paragraph(recommendation.replace('\n', '<br/>'), styles['Normal'])
                    
                    findings_data.append([category, status, confidence, rec_para])
                
                findings_table = Table(findings_data, colWidths=[1.2*inch, 0.9*inch, 0.8*inch, 3.6*inch])
                findings_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (2, -1), 'CENTER'),
                    ('ALIGN', (3, 0), (3, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('WORDWRAP', (3, 1), (3, -1)),
                ]))
                story.append(findings_table)
            else:
                story.append(Paragraph("No findings available.", styles['Normal']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"PDF report generated: {filename}")
        
        return FileResponse(
            path=str(filepath),
            filename=filename,
            media_type='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Error generating PDF report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating report: {str(e)}"
        )


@router.get("/latest-result")
async def get_latest_result(
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db)
):
    """
    Get the latest Azure compliance analysis result.
    - For compliance_team: returns their own latest result
    - For management_team and it_team: returns the latest result from all users
    """
    try:
        db = database.db
        
        # For management_team and it_team, get the latest result from all users
        # For compliance_team, get their own latest result
        if current_user.role in ['management_team', 'it_team']:
            # Get the latest result from any user (most recent overall)
            latest_result = await db.azure_compliance_results.find_one(
                {},
                sort=[("created_at", -1)]
            )
        else:
            # Get latest result for this user (compliance_team or others)
            latest_result = await db.azure_compliance_results.find_one(
                {"user_id": current_user.id},
                sort=[("created_at", -1)]
            )
        
        if not latest_result:
            return {
                'status': 'no_results',
                'message': 'No Azure compliance analysis results found'
            }
        
        # Convert ObjectId to string
        latest_result['_id'] = str(latest_result['_id'])
        latest_result['id'] = latest_result['_id']
        
        return {
            'status': 'success',
            'result': latest_result
        }
    except Exception as e:
        logger.error(f"Error fetching latest Azure compliance result: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching latest result: {str(e)}"
        )


@router.get("/results")
async def get_all_results(
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db),
    limit: int = 50
):
    """
    Get all Azure compliance analysis results.
    - For compliance_team: returns their own results
    - For management_team: returns all results from all users
    - For it_team: returns empty (they shouldn't access this endpoint)
    """
    try:
        # Validate limit parameter
        if limit < 1:
            raise HTTPException(
                status_code=400,
                detail="Limit must be greater than 0. Please provide a valid limit value."
            )
        if limit > 1000:
            raise HTTPException(
                status_code=400,
                detail="Limit cannot exceed 1000. Please provide a limit value between 1 and 1000."
            )
        
        db = database.db
        
        # For management_team, get all results from all users
        # For compliance_team and others, get only their own results
        if current_user.role == 'management_team':
            # Get all results from all users, sorted by most recent first
            cursor = db.azure_compliance_results.find({}).sort("created_at", -1).limit(limit)
        else:
            # Get all results for this user, sorted by most recent first
            cursor = db.azure_compliance_results.find(
                {"user_id": current_user.id}
            ).sort("created_at", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            # Convert ObjectId to string
            doc['_id'] = str(doc['_id'])
            doc['id'] = doc['_id']
            
            # Return summary information for list view
            # Use overall_score (new format) or score (legacy format) for backward compatibility
            score = doc.get('overall_score', doc.get('score', 0))
            
            results.append({
                '_id': doc['_id'],
                'id': doc['_id'],
                'document_name': doc.get('document_name', 'Unknown'),
                'score': score,
                'overall_score': score,  # Include both for compatibility
                'overall_status': doc.get('overall_status', 'Unknown'),
                'created_at': doc.get('created_at', doc.get('analyzed_at')),
                'analyzed_at': doc.get('analyzed_at', doc.get('created_at')),
                'user_email': doc.get('user_email', current_user.email),
                'frameworks_analyzed': doc.get('frameworks_analyzed', []),
                'categories_analyzed': doc.get('categories_analyzed', 0),
                'total_checks': doc.get('total_checks', 0)
            })
        
        return {
            'status': 'success',
            'results': results,
            'count': len(results)
        }
    except Exception as e:
        logger.error(f"Error fetching Azure compliance results: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching results: {str(e)}"
        )


@router.get("/status")
async def get_checker_status():
    """
    Check if Multi-Framework Compliance Checker is ready
    """
    try:
        # Check all frameworks
        framework_status = {}
        total_chunks = 0
        total_vectors = 0
        
        for framework in _frameworks:
            embeddings_dir = EMBEDDINGS_BASE_DIR / framework
            index_dir = INDEX_BASE_DIR / framework
            
            embeddings_file = embeddings_dir / f'{framework}_embeddings.npy'
            index_file = index_dir / f'{framework}_index.faiss'
            
            if embeddings_file.exists() and index_file.exists():
                try:
                    import numpy as np
                    import faiss
                    import json
                    
                    embeddings = np.load(str(embeddings_file))
                    faiss_index = faiss.read_index(str(index_file))
                    
                    doc_map_file = embeddings_dir / f'{framework}_document_map.json'
                    if doc_map_file.exists():
                        with open(doc_map_file, 'r', encoding='utf-8') as f:
                            doc_data = json.load(f)
                        chunks_count = len(doc_data.get('segments', doc_data.get('chunks', [])))
                    else:
                        chunks_count = embeddings.shape[0]
                    
                    framework_status[framework] = {
                        'ready': True,
                        'chunks': chunks_count,
                        'vectors': faiss_index.ntotal
                    }
                    total_chunks += chunks_count
                    total_vectors += faiss_index.ntotal
                except Exception as e:
                    framework_status[framework] = {
                        'ready': False,
                        'error': str(e)
                    }
            else:
                framework_status[framework] = {
                    'ready': False,
                    'message': 'Embeddings not found'
                }
        
        # Check if at least one framework is ready
        ready_frameworks = [f for f, status in framework_status.items() if status.get('ready')]
        
        if ready_frameworks:
            return {
                'status': 'ready',
                'frameworks': framework_status,
                'frameworks_ready': len(ready_frameworks),
                'total_frameworks': len(_frameworks),
                'total_chunks': total_chunks,
                'total_vectors': total_vectors,
                'message': f'Multi-Framework Compliance Checker ready with {len(ready_frameworks)}/{len(_frameworks)} frameworks'
            }
        else:
            return {
                'status': 'not_ready',
                'frameworks': framework_status,
                'message': 'No framework embeddings found. Run: python -m azure_checker.create_all_framework_embeddings'
            }
    except Exception as e:
        logger.error(f"Error checking status: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }

