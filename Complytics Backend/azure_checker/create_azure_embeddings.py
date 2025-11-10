"""
Azure Best Practices Embedding Generation Script
Creates embeddings and FAISS index for Azure documentation

Usage:
    python -m azure_checker.create_azure_embeddings
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from azure_checker.utils.text_extraction import extract_text_from_file, clean_text, chunk_text
from azure_checker.utils.embedding_engine import AzureEmbeddingEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Main function to create Azure embeddings and FAISS index"""
    
    # Define paths
    base_dir = Path(__file__).parent
    docs_dir = base_dir / 'azure_docs'
    embeddings_dir = base_dir / 'embeddings' / 'azure'
    index_dir = base_dir / 'faiss_index_azure'
    
    logger.info("="*80)
    logger.info("Azure Best Practices Embedding Generation")
    logger.info("="*80)
    
    # Check if documents exist
    if not docs_dir.exists():
        logger.error(f"Documents directory not found: {docs_dir}")
        return
    
    # Get all PDF files
    pdf_files = list(docs_dir.glob('*.pdf'))
    if not pdf_files:
        logger.error(f"No PDF files found in {docs_dir}")
        return
    
    logger.info(f"\nFound {len(pdf_files)} Azure documentation files:")
    for pdf_file in pdf_files:
        logger.info(f"  • {pdf_file.name}")
    
    # Initialize embedding engine
    logger.info("\n" + "="*80)
    logger.info("Initializing Embedding Engine...")
    logger.info("="*80)
    engine = AzureEmbeddingEngine(model_name='all-MiniLM-L6-v2')
    
    # Process each document
    all_chunks = []
    all_metadata = []
    
    logger.info("\n" + "="*80)
    logger.info("Extracting and Processing Documents...")
    logger.info("="*80)
    
    for pdf_file in pdf_files:
        logger.info(f"\nProcessing: {pdf_file.name}")
        
        # Extract text
        text = extract_text_from_file(str(pdf_file))
        if not text:
            logger.warning(f"  ⚠️ No text extracted from {pdf_file.name}, skipping...")
            continue
        
        # Clean text
        text = clean_text(text)
        logger.info(f"  ✓ Extracted {len(text)} characters")
        
        # Chunk text (800 characters with 100 overlap for fewer chunks)
        chunks = chunk_text(text, chunk_size=800, overlap=100)
        logger.info(f"  ✓ Created {len(chunks)} chunks")
        
        # Limit chunks per document to prevent memory issues
        max_chunks_per_doc = 500
        if len(chunks) > max_chunks_per_doc:
            logger.info(f"  ⚠️ Too many chunks ({len(chunks)}), sampling {max_chunks_per_doc} most relevant ones")
            # Keep every Nth chunk to get a representative sample
            step = len(chunks) // max_chunks_per_doc
            chunks = chunks[::step][:max_chunks_per_doc]
            logger.info(f"  ✓ Sampled to {len(chunks)} chunks")
        
        # Categorize chunks
        from azure_checker.utils.compliance_logic import AzureComplianceAnalyzer
        analyzer = AzureComplianceAnalyzer()
        
        for chunk in chunks:
            category = analyzer.categorize_chunk(chunk)
            all_chunks.append(chunk)
            all_metadata.append({
                'source_file': pdf_file.name,
                'category': category,
                'chunk_length': len(chunk)
            })
        
        logger.info(f"  ✓ Categorized {len(chunks)} chunks")
    
    if not all_chunks:
        logger.error("No chunks created. Exiting.")
        return
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Total chunks created: {len(all_chunks)}")
    logger.info(f"{'='*80}")
    
    # Count chunks by category
    category_counts = {}
    for meta in all_metadata:
        cat = meta['category']
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    logger.info("\nChunks by Category:")
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  • {category}: {count} chunks")
    
    # Generate embeddings in batches to save memory
    logger.info("\n" + "="*80)
    logger.info("Generating Embeddings (in batches to save memory)...")
    logger.info("="*80)
    
    # Process in smaller batches of 500 chunks at a time
    batch_size = 500
    all_embeddings = []
    
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(all_chunks)-1)//batch_size + 1} ({len(batch)} chunks)")
        batch_embeddings = engine.generate_embeddings(batch)
        all_embeddings.append(batch_embeddings)
    
    # Combine all batches
    import numpy as np
    embeddings = np.vstack(all_embeddings)
    logger.info(f"✓ Generated embeddings with shape: {embeddings.shape}")
    
    # Create FAISS index
    logger.info("\n" + "="*80)
    logger.info("Creating FAISS Index...")
    logger.info("="*80)
    faiss_index = engine.create_faiss_index(embeddings)
    logger.info(f"✓ FAISS index created with {faiss_index.ntotal} vectors")
    
    # Save everything
    logger.info("\n" + "="*80)
    logger.info("Saving to Disk...")
    logger.info("="*80)
    
    # Save embeddings and data
    engine.save_embeddings(str(embeddings_dir), embeddings, all_chunks, all_metadata)
    logger.info(f"✓ Saved embeddings to: {embeddings_dir}")
    
    # Save FAISS index
    engine.save_faiss_index(str(index_dir), faiss_index)
    logger.info(f"✓ Saved FAISS index to: {index_dir}")
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("✅ EMBEDDING GENERATION COMPLETE!")
    logger.info("="*80)
    logger.info(f"""
Summary:
  • Documents Processed: {len(pdf_files)}
  • Total Chunks: {len(all_chunks)}
  • Embedding Dimension: {embeddings.shape[1]}
  • FAISS Index Vectors: {faiss_index.ntotal}
  • Categories: {len(category_counts)}
  
Files Created:
  • {embeddings_dir / 'azure_embeddings.npy'}
  • {embeddings_dir / 'azure_data.pkl'}
  • {index_dir / 'azure_index.faiss'}
  
✅ Ready for Azure Compliance Checking!
    """)


if __name__ == "__main__":
    main()

