"""
Multi-Framework Embeddings Generator
Generates embeddings for Azure, GDPR, ISO 27001, ISO 27017, and ISO 27018
Reuses existing code from compliance_rag.py
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add parent directory to path to import compliance_rag
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import existing working functions from compliance_rag.py
from compliance_rag import (
    extract_text_from_pdf,
    process_text_into_segments,
    embedding_model,
    logger
)

import numpy as np
import faiss

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_framework_embeddings(framework_name, docs_dir, embeddings_dir, index_dir):
    """
    Generate embeddings for a specific framework
    
    Args:
        framework_name: Name of the framework (e.g., 'azure', 'gdpr', 'iso27001')
        docs_dir: Directory containing framework PDFs
        embeddings_dir: Output directory for embeddings
        index_dir: Output directory for FAISS index
    """
    logger.info("\n" + "="*80)
    logger.info(f"Processing {framework_name.upper()} Framework")
    logger.info("="*80)
    
    # Create directories
    embeddings_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)
    
    # Get PDF files
    pdf_files = list(docs_dir.glob('*.pdf'))
    logger.info(f"\nFound {len(pdf_files)} {framework_name.upper()} PDF files:")
    for pdf in pdf_files:
        logger.info(f"  • {pdf.name}")
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {docs_dir}")
        return None
    
    all_segments = []
    document_map = []
    
    for idx, pdf_file in enumerate(pdf_files):
        logger.info(f"\nProcessing [{idx+1}/{len(pdf_files)}]: {pdf_file.name}")
        
        try:
            # Extract text using existing function
            text = extract_text_from_pdf(str(pdf_file))
            
            if not text:
                logger.warning(f"  No text extracted, skipping...")
                continue
            
            logger.info(f"  Extracted {len(text):,} characters")
            
            # Use compliance_rag function for segmentation
            segments = process_text_into_segments(text, max_segment_length=1000)
            logger.info(f"  Created {len(segments)} segments")
            
            # Add to all segments
            for chunk in segments:
                all_segments.append(chunk)
                document_map.append({
                    'source_file': pdf_file.name,
                    'framework': framework_name,
                    'chunk_index': len(all_segments) - 1
                })
            
            logger.info(f"  ✓ Added {len(segments)} chunks to collection")
            
        except Exception as e:
            logger.error(f"  Error processing {pdf_file.name}: {e}")
            continue
    
    if len(all_segments) == 0:
        logger.error(f"No chunks created for {framework_name}")
        return None
    
    logger.info(f"\nTotal chunks collected: {len(all_segments)}")
    
    # Generate embeddings using existing model
    logger.info(f"\nGenerating embeddings for {framework_name}...")
    
    batch_size = 32
    all_embeddings = []
    
    for i in range(0, len(all_segments), batch_size):
        batch = all_segments[i:i+batch_size]
        logger.info(f"  Batch {i//batch_size + 1}/{(len(all_segments)-1)//batch_size + 1}: {len(batch)} segments")
        
        try:
            batch_embeddings = embedding_model.encode(batch, convert_to_numpy=True)
            all_embeddings.append(batch_embeddings)
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            continue
    
    # Combine all batches
    embeddings_array = np.vstack(all_embeddings)
    logger.info(f"✓ Generated embeddings: {embeddings_array.shape}")
    
    # Create FAISS index
    logger.info(f"\nCreating FAISS index for {framework_name}...")
    embedding_dim = embeddings_array.shape[1]
    index = faiss.IndexFlatL2(embedding_dim)
    index.add(embeddings_array.astype('float32'))
    logger.info(f"✓ FAISS index created with {index.ntotal} vectors")
    
    # Save embeddings
    embeddings_file = embeddings_dir / f'{framework_name}_embeddings.npy'
    np.save(embeddings_file, embeddings_array)
    logger.info(f"✓ Saved embeddings to: {embeddings_file}")
    
    # Save document map as JSON
    doc_map_file = embeddings_dir / f'{framework_name}_document_map.json'
    with open(doc_map_file, 'w', encoding='utf-8') as f:
        json.dump({
            'segments': all_segments,
            'metadata': document_map,
            'framework': framework_name
        }, f, ensure_ascii=False, indent=2)
    logger.info(f"✓ Saved document map to: {doc_map_file}")
    
    # Save FAISS index
    index_file = index_dir / f'{framework_name}_index.faiss'
    faiss.write_index(index, str(index_file))
    logger.info(f"✓ Saved FAISS index to: {index_file}")
    
    return {
        'framework': framework_name,
        'documents': len(pdf_files),
        'chunks': len(all_segments),
        'embedding_dim': embedding_dim,
        'index_vectors': index.ntotal
    }


def main():
    """Generate embeddings for all frameworks"""
    
    logger.info("="*80)
    logger.info("MULTI-FRAMEWORK EMBEDDINGS GENERATOR")
    logger.info("="*80)
    
    base_dir = Path(__file__).parent
    
    # Define frameworks and their directories
    frameworks = [
        {
            'name': 'azure',
            'docs_dir': base_dir / 'azure_docs',
            'embeddings_dir': base_dir / 'embeddings' / 'azure',
            'index_dir': base_dir / 'faiss_indexes' / 'azure'
        },
        {
            'name': 'gdpr',
            'docs_dir': base_dir / 'compliance_docs',
            'embeddings_dir': base_dir / 'embeddings' / 'gdpr',
            'index_dir': base_dir / 'faiss_indexes' / 'gdpr',
            'filter_files': ['GDPR']  # Only process GDPR files
        },
        {
            'name': 'iso27001',
            'docs_dir': base_dir / 'compliance_docs',
            'embeddings_dir': base_dir / 'embeddings' / 'iso27001',
            'index_dir': base_dir / 'faiss_indexes' / 'iso27001',
            'filter_files': ['ISO 27001', 'ISO_27001']
        },
        {
            'name': 'iso27017',
            'docs_dir': base_dir / 'compliance_docs',
            'embeddings_dir': base_dir / 'embeddings' / 'iso27017',
            'index_dir': base_dir / 'faiss_indexes' / 'iso27017',
            'filter_files': ['27017']
        },
        {
            'name': 'iso27018',
            'docs_dir': base_dir / 'compliance_docs',
            'embeddings_dir': base_dir / 'embeddings' / 'iso27018',
            'index_dir': base_dir / 'faiss_indexes' / 'iso27018',
            'filter_files': ['27018']
        }
    ]
    
    results = []
    
    for framework_config in frameworks:
        framework_name = framework_config['name']
        docs_dir = framework_config['docs_dir']
        
        # If filter_files is specified, create temp dir with filtered files
        if 'filter_files' in framework_config:
            # Get all PDFs and filter
            all_pdfs = list(docs_dir.glob('*.pdf'))
            filtered_pdfs = [
                pdf for pdf in all_pdfs 
                if any(filter_str in pdf.name for filter_str in framework_config['filter_files'])
            ]
            
            if not filtered_pdfs:
                logger.warning(f"No files found for {framework_name} with filters: {framework_config['filter_files']}")
                continue
            
            # Create a temporary directory symlink or just process these files
            # For simplicity, we'll temporarily copy to embeddings logic
            logger.info(f"\nFiltered {len(filtered_pdfs)} files for {framework_name}:")
            for pdf in filtered_pdfs:
                logger.info(f"  • {pdf.name}")
            
            # Create temp processing
            result = generate_framework_embeddings_filtered(
                framework_name,
                filtered_pdfs,
                framework_config['embeddings_dir'],
                framework_config['index_dir']
            )
        else:
            result = generate_framework_embeddings(
                framework_name,
                docs_dir,
                framework_config['embeddings_dir'],
                framework_config['index_dir']
            )
        
        if result:
            results.append(result)
    
    # Print summary
    logger.info("\n" + "="*80)
    logger.info("✅ ALL FRAMEWORKS COMPLETE!")
    logger.info("="*80)
    logger.info("\nSummary:")
    for result in results:
        logger.info(f"\n{result['framework'].upper()}:")
        logger.info(f"  • Documents: {result['documents']}")
        logger.info(f"  • Total Chunks: {result['chunks']}")
        logger.info(f"  • Embedding Dimension: {result['embedding_dim']}")
        logger.info(f"  • FAISS Index Vectors: {result['index_vectors']}")
    
    logger.info("\n✅ Ready for Multi-Framework Compliance Checking!")


def generate_framework_embeddings_filtered(framework_name, pdf_files, embeddings_dir, index_dir):
    """Generate embeddings for filtered PDF files"""
    
    logger.info("\n" + "="*80)
    logger.info(f"Processing {framework_name.upper()} Framework")
    logger.info("="*80)
    
    # Create directories
    embeddings_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)
    
    all_segments = []
    document_map = []
    
    for idx, pdf_file in enumerate(pdf_files):
        logger.info(f"\nProcessing [{idx+1}/{len(pdf_files)}]: {pdf_file.name}")
        
        try:
            # Extract text using existing function
            text = extract_text_from_pdf(str(pdf_file))
            
            if not text:
                logger.warning(f"  No text extracted, skipping...")
                continue
            
            logger.info(f"  Extracted {len(text):,} characters")
            
            # Use compliance_rag function for segmentation
            segments = process_text_into_segments(text, max_segment_length=1000)
            logger.info(f"  Created {len(segments)} segments")
            
            # Add to all segments
            for chunk in segments:
                all_segments.append(chunk)
                document_map.append({
                    'source_file': pdf_file.name,
                    'framework': framework_name,
                    'chunk_index': len(all_segments) - 1
                })
            
            logger.info(f"  ✓ Added {len(segments)} chunks to collection")
            
        except Exception as e:
            logger.error(f"  Error processing {pdf_file.name}: {e}")
            continue
    
    if len(all_segments) == 0:
        logger.error(f"No chunks created for {framework_name}")
        return None
    
    logger.info(f"\nTotal chunks collected: {len(all_segments)}")
    
    # Generate embeddings using existing model
    logger.info(f"\nGenerating embeddings for {framework_name}...")
    
    batch_size = 32
    all_embeddings = []
    
    for i in range(0, len(all_segments), batch_size):
        batch = all_segments[i:i+batch_size]
        logger.info(f"  Batch {i//batch_size + 1}/{(len(all_segments)-1)//batch_size + 1}: {len(batch)} segments")
        
        try:
            batch_embeddings = embedding_model.encode(batch, convert_to_numpy=True)
            all_embeddings.append(batch_embeddings)
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            continue
    
    # Combine all batches
    embeddings_array = np.vstack(all_embeddings)
    logger.info(f"✓ Generated embeddings: {embeddings_array.shape}")
    
    # Create FAISS index
    logger.info(f"\nCreating FAISS index for {framework_name}...")
    embedding_dim = embeddings_array.shape[1]
    index = faiss.IndexFlatL2(embedding_dim)
    index.add(embeddings_array.astype('float32'))
    logger.info(f"✓ FAISS index created with {index.ntotal} vectors")
    
    # Save embeddings
    embeddings_file = embeddings_dir / f'{framework_name}_embeddings.npy'
    np.save(embeddings_file, embeddings_array)
    logger.info(f"✓ Saved embeddings to: {embeddings_file}")
    
    # Save document map as JSON
    doc_map_file = embeddings_dir / f'{framework_name}_document_map.json'
    with open(doc_map_file, 'w', encoding='utf-8') as f:
        json.dump({
            'segments': all_segments,
            'metadata': document_map,
            'framework': framework_name
        }, f, ensure_ascii=False, indent=2)
    logger.info(f"✓ Saved document map to: {doc_map_file}")
    
    # Save FAISS index
    index_file = index_dir / f'{framework_name}_index.faiss'
    faiss.write_index(index, str(index_file))
    logger.info(f"✓ Saved FAISS index to: {index_file}")
    
    return {
        'framework': framework_name,
        'documents': len(pdf_files),
        'chunks': len(all_segments),
        'embedding_dim': embedding_dim,
        'index_vectors': index.ntotal
    }


if __name__ == "__main__":
    main()

