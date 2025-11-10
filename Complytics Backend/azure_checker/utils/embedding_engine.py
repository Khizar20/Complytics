"""
Embedding Engine for Azure Compliance Checker
Uses SentenceTransformer for generating embeddings
"""

import os
import logging
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AzureEmbeddingEngine:
    """Handles embedding generation and FAISS indexing for Azure documents"""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the embedding engine
        
        Args:
            model_name: Name of the SentenceTransformer model to use
        """
        logger.info(f"Initializing Azure Embedding Engine with model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = 384  # Dimension for all-MiniLM-L6-v2
        self.index = None
        self.chunks = []
        self.metadata = []
        
    def generate_embeddings(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for a list of texts with memory optimization
        
        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process at once (default 32)
            
        Returns:
            numpy array of embeddings
        """
        logger.info(f"Generating embeddings for {len(texts)} texts...")
        # Use smaller batch size to reduce memory usage
        embeddings = self.model.encode(
            texts, 
            show_progress_bar=True, 
            convert_to_numpy=True,
            batch_size=batch_size,
            normalize_embeddings=True  # Normalize for better similarity
        )
        logger.info(f"Generated embeddings with shape: {embeddings.shape}")
        return embeddings
    
    def create_faiss_index(self, embeddings: np.ndarray) -> faiss.IndexFlatL2:
        """
        Create a FAISS index from embeddings
        
        Args:
            embeddings: numpy array of embeddings
            
        Returns:
            FAISS index
        """
        logger.info("Creating FAISS index...")
        
        # Ensure embeddings are float32 (required by FAISS)
        embeddings = embeddings.astype('float32')
        
        # Create L2 (Euclidean distance) index
        index = faiss.IndexFlatL2(self.embedding_dim)
        
        # Add embeddings to index
        index.add(embeddings)
        
        logger.info(f"FAISS index created with {index.ntotal} vectors")
        return index
    
    def save_embeddings(self, save_dir: str, embeddings: np.ndarray, chunks: List[str], 
                       metadata: List[Dict[str, Any]]):
        """
        Save embeddings, chunks, and metadata to disk
        
        Args:
            save_dir: Directory to save embeddings
            embeddings: numpy array of embeddings
            chunks: List of text chunks
            metadata: List of metadata dictionaries for each chunk
        """
        import json
        os.makedirs(save_dir, exist_ok=True)
        
        # Save embeddings as numpy array
        embeddings_file = os.path.join(save_dir, 'azure_embeddings.npy')
        np.save(embeddings_file, embeddings)
        logger.info(f"Saved embeddings to {embeddings_file}")
        
        # Save chunks and metadata as JSON (not PKL)
        data_file = os.path.join(save_dir, 'document_map.json')
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump({
                'segments': chunks,
                'metadata': metadata
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved chunks and metadata to {data_file}")
    
    def load_embeddings(self, save_dir: str) -> Tuple[np.ndarray, List[str], List[Dict[str, Any]]]:
        """
        Load embeddings, chunks, and metadata from disk
        
        Args:
            save_dir: Directory containing saved embeddings
            
        Returns:
            Tuple of (embeddings, chunks, metadata)
        """
        import json
        
        # Load embeddings
        embeddings_file = os.path.join(save_dir, 'azure_embeddings.npy')
        embeddings = np.load(embeddings_file)
        logger.info(f"Loaded embeddings from {embeddings_file}, shape: {embeddings.shape}")
        
        # Load chunks and metadata from JSON (not PKL)
        data_file = os.path.join(save_dir, 'document_map.json')
        if not os.path.exists(data_file):
            raise FileNotFoundError(f"Document map not found: {data_file}")
        
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both 'segments' and 'chunks' keys
        chunks = data.get('segments', data.get('chunks', []))
        metadata = data.get('metadata', [])
        logger.info(f"Loaded {len(chunks)} chunks and metadata from {data_file}")
        
        return embeddings, chunks, metadata
    
    def save_faiss_index(self, index_dir: str, index: faiss.IndexFlatL2):
        """
        Save FAISS index to disk
        
        Args:
            index_dir: Directory to save index
            index: FAISS index to save
        """
        os.makedirs(index_dir, exist_ok=True)
        index_file = os.path.join(index_dir, 'azure_index.faiss')
        faiss.write_index(index, index_file)
        logger.info(f"Saved FAISS index to {index_file}")
    
    def load_faiss_index(self, index_dir: str) -> faiss.IndexFlatL2:
        """
        Load FAISS index from disk
        
        Args:
            index_dir: Directory containing saved index
            
        Returns:
            FAISS index
        """
        index_file = os.path.join(index_dir, 'azure_index.faiss')
        index = faiss.read_index(index_file)
        logger.info(f"Loaded FAISS index from {index_file}, contains {index.ntotal} vectors")
        return index
    
    def search_similar(self, query_text: str, index: faiss.IndexFlatL2, 
                      chunks: List[str], metadata: List[Dict[str, Any]], 
                      top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar chunks given a query text
        
        Args:
            query_text: Query text to search for
            index: FAISS index to search
            chunks: List of text chunks
            metadata: List of metadata for each chunk
            top_k: Number of top results to return
            
        Returns:
            List of dictionaries containing search results
        """
        # Generate query embedding
        query_embedding = self.model.encode([query_text], convert_to_numpy=True).astype('float32')
        
        # Search index
        distances, indices = index.search(query_embedding, top_k)
        
        # Prepare results
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(chunks):  # Ensure index is valid
                # Convert L2 distance to similarity score (0-1 range)
                # Lower distance = higher similarity
                similarity = 1 / (1 + distance)
                
                results.append({
                    'rank': i + 1,
                    'chunk': chunks[idx],
                    'metadata': metadata[idx],
                    'distance': float(distance),
                    'similarity': float(similarity),
                    'category': metadata[idx].get('category', 'General')
                })
        
        return results

