"""
Text Extraction Utilities for Azure Compliance Checker
Reuses extraction logic from compliance_rag.py
"""

import os
import logging
import PyPDF2
import pdfplumber
import docx
import json
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using pdfplumber and PyPDF2 as fallback"""
    try:
        # Try pdfplumber first (better text extraction)
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            if text.strip():
                logger.info(f"Extracted {len(text)} characters from {file_path} using pdfplumber")
                return text
    except Exception as e:
        logger.warning(f"pdfplumber failed for {file_path}: {e}, trying PyPDF2...")
    
    # Fallback to PyPDF2
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            logger.info(f"Extracted {len(text)} characters from {file_path} using PyPDF2")
            return text
    except Exception as e:
        logger.error(f"Both PDF extraction methods failed for {file_path}: {e}")
        return ""


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX files"""
    try:
        doc = docx.Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        logger.info(f"Extracted {len(text)} characters from {file_path}")
        return text
    except Exception as e:
        logger.error(f"Error extracting text from DOCX {file_path}: {e}")
        return ""


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from plain text files"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            text = file.read()
        logger.info(f"Extracted {len(text)} characters from {file_path}")
        return text
    except Exception as e:
        logger.error(f"Error extracting text from TXT {file_path}: {e}")
        return ""


def extract_text_from_json(file_path: str) -> str:
    """Extract text from JSON configuration files"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Convert JSON to readable text format
        text = json.dumps(data, indent=2)
        logger.info(f"Extracted {len(text)} characters from {file_path}")
        return text
    except Exception as e:
        logger.error(f"Error extracting text from JSON {file_path}: {e}")
        return ""


def extract_text_from_file(file_path: str) -> str:
    """
    Main extraction function that routes to appropriate extractor based on file extension
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return ""
    
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.pdf':
        return extract_text_from_pdf(file_path)
    elif file_extension in ['.docx', '.doc']:
        return extract_text_from_docx(file_path)
    elif file_extension == '.txt':
        return extract_text_from_txt(file_path)
    elif file_extension == '.json':
        return extract_text_from_json(file_path)
    else:
        logger.warning(f"Unsupported file type: {file_extension}")
        return ""


def clean_text(text: str) -> str:
    """Clean and normalize extracted text"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = " ".join(text.split())
    
    # Remove special characters that might interfere with embedding
    text = text.replace('\x00', '')  # Remove null bytes
    text = text.replace('\ufeff', '')  # Remove BOM
    
    return text.strip()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list:
    """
    Split text into chunks efficiently - optimized for memory usage
    Uses simple splitting to avoid memory-intensive string operations
    """
    if not text:
        return []
    
    # Limit text size to prevent memory issues (max 100k chars for uploaded docs)
    max_text_length = 100000
    if len(text) > max_text_length:
        logger.warning(f"Text too long ({len(text)} chars), using first {max_text_length} chars")
        text = text[:max_text_length]
    
    chunks = []
    text_length = len(text)
    
    # Simple approach: split by paragraphs first, then combine into chunks
    paragraphs = text.split('\n\n')
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        # If adding this paragraph would exceed chunk size, save current chunk
        if current_chunk and len(current_chunk) + len(para) > chunk_size:
            chunks.append(current_chunk.strip())
            # Start new chunk with overlap (last 100 chars of previous chunk)
            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_text + "\n\n" + para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
    
    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Limit total chunks to prevent memory issues
    max_chunks = 50
    if len(chunks) > max_chunks:
        logger.warning(f"Too many chunks ({len(chunks)}), limiting to {max_chunks}")
        step = len(chunks) // max_chunks
        chunks = chunks[::step][:max_chunks]
    
    logger.info(f"Created {len(chunks)} chunks from text of length {text_length}")
    return chunks

