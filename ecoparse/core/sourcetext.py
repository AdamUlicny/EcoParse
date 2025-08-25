"""
PDF Text Processing and Context Extraction Module

This module handles PDF document processing, text extraction, and context
retrieval for species-specific information. It provides functions for
extracting readable text from PDFs and locating relevant passages
surrounding species mentions.

Scientific Purpose:
- Enables automated processing of biodiversity literature in PDF format
- Provides contextual text passages for species data extraction
- Supports both text-based and image-based analysis workflows

Key Features:
- Robust PDF text extraction using multiple libraries
- Context window extraction around species mentions
- Page image generation for visual analysis
- Text normalization for improved search accuracy
"""

import io
import re
from typing import Optional, Dict, List
import pandas as pd
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_file_buffer: io.BytesIO) -> str:
    """
    Extracts text content from PDF documents using PyMuPDF.
    
    Processes PDF files to extract plain text suitable for species name
    detection and data extraction. PyMuPDF (fitz) is used for its superior
    text extraction capabilities compared to other libraries.
    
    Args:
        pdf_file_buffer: Binary PDF data stream
        
    Returns:
        Concatenated text content from all PDF pages
        
    Technical Details:
    - Handles various PDF encodings and formats
    - Preserves page breaks for document structure
    - Robust error handling for corrupted or protected PDFs
    """
    full_text = ""
    try:
        pdf_file_buffer.seek(0)
        doc = fitz.open(stream=pdf_file_buffer.read(), filetype="pdf")
        for page in doc:
            full_text += page.get_text("text") + "\n"
        return full_text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def trim_pdf_pages(pdf_buffer: io.BytesIO, start_page: int, end_page: int) -> Optional[io.BytesIO]:
    """
    Extracts a page range from a PDF document.
    
    Creates a new PDF containing only the specified page range,
    useful for processing specific sections of large documents
    or reducing computational load.
    
    Args:
        pdf_buffer: Original PDF data stream
        start_page: First page to include (1-indexed)
        end_page: Last page to include (1-indexed, inclusive)
        
    Returns:
        New PDF buffer with selected pages, or None if invalid range
        
    Use Cases:
    - Processing specific chapters or sections
    - Excluding irrelevant front/back matter
    - Reducing memory usage for large documents
    """
    try:
        pdf_buffer.seek(0)
        reader = PdfReader(pdf_buffer)
        if not (1 <= start_page <= end_page <= len(reader.pages)):
            return None
        
        writer = PdfWriter()
        for i in range(start_page - 1, end_page):
            writer.add_page(reader.pages[i])

        trimmed_buffer = io.BytesIO()
        writer.write(trimmed_buffer)
        trimmed_buffer.seek(0)
        return trimmed_buffer
    except Exception as e:
        print(f"Failed to trim PDF: {e}")
        return None

def normalize_text_for_search(text: str) -> str:
    """
    Normalizes text for improved species name searching.
    
    Removes common PDF artifacts and formatting issues that can
    interfere with species name detection, including:
    - Hyphenated line breaks
    - Inconsistent whitespace
    - Line break artifacts
    
    Args:
        text: Raw text from PDF extraction
        
    Returns:
        Cleaned text optimized for species name matching
        
    Normalization Steps:
    1. Remove hyphenated line breaks (e.g., "Homo sapi-\nens" -> "Homo sapiens")
    2. Replace line breaks with spaces
    3. Normalize multiple whitespace characters
    4. Trim leading/trailing whitespace
    """
    text = re.sub(r'-\s*\n\s*', '', text)
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def get_species_context_chunks(
    full_text: str, species_df: pd.DataFrame, context_before: int, context_after: int
) -> Dict[str, List[str]]:
    """
    Extracts contextual text passages surrounding species mentions.
    
    Locates all occurrences of each species name in the document and
    extracts surrounding text context. This provides the textual
    information needed for data extraction algorithms to identify
    species-specific attributes.
    
    Args:
        full_text: Complete document text from PDF extraction
        species_df: DataFrame containing detected species names
        context_before: Number of characters to include before species mention
        context_after: Number of characters to include after species mention
        
    Returns:
        Dictionary mapping species names to lists of context passages
        
    Scientific Rationale:
    - Context windows capture relevant information about species
    - Multiple contexts per species enable comprehensive data extraction
    - Robust searching handles nomenclatural variations and formatting
    
    Algorithm Details:
    - Uses canonical names (not verbatim) for improved matching accuracy
    - Implements word boundary matching to avoid false positives
    - Deduplicates identical context passages
    - Case-insensitive matching for robustness
    
    Context Window Design:
    - Size should balance information content vs. noise
    - Typical values: 200-500 characters before/after
    - Longer contexts for complex ecological descriptions
    """
    species_chunks = {}
    if species_df.empty:
        return species_chunks

    normalized_full_text = normalize_text_for_search(full_text)

    for _, row in species_df.iterrows():
        # --- ROBUST SPECIES NAME MATCHING ---
        # Use cleaned canonical name rather than messy verbatim text
        # This improves matching accuracy for formatted documents
        search_name = row["Name"]
        if not search_name:
            continue
        # --- END ROBUST MATCHING ---

        try:
            # Use a case-insensitive regex pattern with word boundaries for accuracy.
            pattern = re.compile(r'\b' + re.escape(search_name) + r'\b', re.IGNORECASE)
        except re.error:
            continue

        for match in pattern.finditer(normalized_full_text):
            match_start = match.start()
            match_end = match.end()

            chunk_start = max(0, match_start - context_before)
            chunk_end = min(len(normalized_full_text), match_end + context_after)
            
            chunk = normalized_full_text[chunk_start:chunk_end]
            
            if search_name not in species_chunks:
                species_chunks[search_name] = []
            
            # Avoid adding duplicate chunks if the same context is found multiple times
            if chunk not in species_chunks[search_name]:
                species_chunks[search_name].append(chunk)

    return species_chunks

def get_species_page_images(pdf_buffer: io.BytesIO, species_df: pd.DataFrame) -> Dict[str, List[bytes]]:
    """
    Generates page images for species mentions in PDF documents.
    
    Creates high-resolution images of PDF pages containing species mentions,
    enabling visual analysis and image-based data extraction workflows.
    This is particularly useful for documents with tables, figures, or
    complex layouts that may not extract well as text.
    
    Args:
        pdf_buffer: PDF document data stream
        species_df: DataFrame of detected species names
        
    Returns:
        Dictionary mapping species names to lists of page images (PNG bytes)
        
    Technical Specifications:
    - 150 DPI resolution balances quality with file size
    - PNG format for lossless image quality
    - Processes only pages containing species mentions for efficiency
    
    Scientific Applications:
    - Extraction from tables and structured data
    - Analysis of figures and diagrams
    - Verification of text extraction accuracy
    - Multi-modal language model inputs
    
    Performance Optimization:
    - Deduplicates pages when multiple species appear together
    - Uses set operations to minimize redundant processing
    - Sorts page numbers for consistent output order
    """
    species_pages = {}
    species_images = {}
    
    pdf_buffer.seek(0)
    
    try:
        doc = fitz.open(stream=pdf_buffer.read(), filetype="pdf")

        for i, page in enumerate(doc):
            page_text = page.get_text("text") or ""
            normalized_page_text = normalize_text_for_search(page_text)
            
            for species_name in species_df["Name"].unique():
                if re.search(r'\b' + re.escape(species_name) + r'\b', normalized_page_text, re.IGNORECASE):
                    if species_name not in species_pages:
                        species_pages[species_name] = set()
                    species_pages[species_name].add(i)
        
        for species_name, page_indices in species_pages.items():
            images = []
            for page_num in sorted(list(page_indices)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(dpi=150)
                images.append(pix.tobytes("png"))
            species_images[species_name] = images
            
        return species_images
    except Exception as e:
        print(f"Error processing PDF for page images: {e}")
        return {}