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
import pdfplumber

def extract_text_from_pdf(pdf_file_buffer: io.BytesIO, method: str = "standard") -> str:
    """
    Extracts text content from PDF documents using PyMuPDF with layout options.
    
    Processes PDF files to extract plain text suitable for species name
    detection and data extraction. Supports different extraction methods
    for handling complex layouts like multi-column documents.
    
    Args:
        pdf_file_buffer: Binary PDF data stream
        method: Extraction method ("standard", "adaptive", "plumber")
        
    Returns:
        Concatenated text content from all PDF pages
        
    Technical Details:
    - Handles various PDF encodings and formats
    - Preserves page breaks for document structure
    - Robust error handling for corrupted or protected PDFs
    - Adaptive method handles any layout automatically
    - Plumber method excels at complex layouts and tables
    
    Extraction Methods:
    - "standard": Basic text extraction (fastest, good for simple layouts)
    - "adaptive": Automatic layout analysis and column detection (recommended for complex layouts)
    - "plumber": PDFplumber-based extraction (best for tables, forms, and structured documents)
    """
    if method == "adaptive":
        return _extract_text_adaptive(pdf_file_buffer)
    elif method == "plumber":
        return _extract_text_plumber(pdf_file_buffer)
    else:
        # Default to standard method
        return _extract_text_standard(pdf_file_buffer)


def _extract_text_standard(pdf_file_buffer: io.BytesIO) -> str:
    """Standard text extraction method (original implementation)."""
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


def _extract_text_plumber(pdf_file_buffer: io.BytesIO) -> str:
    """
    PDFplumber-based text extraction for complex layouts and structured documents.
    
    Uses PDFplumber's advanced layout analysis to handle:
    - Complex tables and forms
    - Mixed column layouts
    - Structured documents with precise positioning
    - Documents with heavy formatting
    
    PDFplumber excels at:
    - Table extraction and structure preservation
    - Handling overlapping text elements
    - Maintaining spatial relationships
    - Processing forms and structured data
    """
    full_text = ""
    try:
        pdf_file_buffer.seek(0)
        
        with pdfplumber.open(pdf_file_buffer) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    # Extract text using PDFplumber's layout analysis
                    page_text = page.extract_text()
                    
                    if page_text:
                        # Add page marker for context
                        full_text += f"\n=== PAGE {page_num + 1} ===\n"
                        full_text += page_text + "\n"
                        
                        # Check for tables on this page and extract them
                        tables = page.extract_tables()
                        if tables:
                            full_text += f"\n--- TABLES ON PAGE {page_num + 1} ---\n"
                            for table_idx, table in enumerate(tables):
                                full_text += f"\nTable {table_idx + 1}:\n"
                                for row in table:
                                    if row and any(cell for cell in row if cell):  # Skip empty rows
                                        row_text = " | ".join([str(cell) if cell else "" for cell in row])
                                        full_text += row_text + "\n"
                                full_text += "\n"
                    
                except Exception as e:
                    print(f"Error processing page {page_num + 1} with PDFplumber: {e}")
                    # Fallback to basic text extraction for this page
                    try:
                        basic_text = page.extract_text()
                        if basic_text:
                            full_text += f"\n=== PAGE {page_num + 1} (basic) ===\n"
                            full_text += basic_text + "\n"
                    except:
                        continue
        
        return full_text
        
    except Exception as e:
        print(f"Error in PDFplumber text extraction: {e}")
        return ""


def _extract_text_adaptive(pdf_file_buffer: io.BytesIO) -> str:
    """
    Adaptive text extraction that automatically detects and handles different layouts.
    
    Analyzes each page to determine the optimal extraction strategy:
    - Single column: Standard top-to-bottom extraction
    - Two columns: Extract left column first, then right
    - Multi-column: Extract columns in order, preserving relationships
    """
    full_text = ""
    try:
        pdf_file_buffer.seek(0)
        doc = fitz.open(stream=pdf_file_buffer.read(), filetype="pdf")
        
        for page_num, page in enumerate(doc):
            # Analyze page layout
            layout = _analyze_page_layout(page)
            
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])
            
            if not blocks:
                continue
            
            # Add layout information as comment
            full_text += f"\n<!-- Page {page_num + 1}: {layout['columns']} columns detected -->\n"
            
            if layout["strategy"] == "single_column":
                # Standard extraction for single column
                for block in blocks:
                    if "lines" not in block:
                        continue
                    for line in block.get("lines", []):
                        line_text = ""
                        for span in line.get("spans", []):
                            line_text += span.get("text", "")
                        if line_text.strip():
                            full_text += line_text + "\n"
            
            else:
                # Multi-column extraction
                boundaries = layout["boundaries"]
                columns = [[] for _ in range(layout["columns"])]
                
                # Assign blocks to columns based on position
                for block in blocks:
                    if "lines" not in block:
                        continue
                    
                    bbox = block.get("bbox", [0,0,0,0])
                    block_center_x = (bbox[0] + bbox[2]) / 2
                    
                    # Find which column this block belongs to
                    column_index = 0
                    for i, boundary in enumerate(boundaries):
                        if block_center_x <= boundary:
                            column_index = i
                            break
                    
                    columns[column_index].append(block)
                
                # Sort blocks within each column by y-position
                for column in columns:
                    column.sort(key=lambda b: b.get("bbox", [0,0,0,0])[1])
                
                # Extract text column by column
                for col_idx, column in enumerate(columns):
                    if column:  # Only add header if column has content
                        full_text += f"\n=== COLUMN {col_idx + 1} ===\n"
                        
                        for block in column:
                            for line in block.get("lines", []):
                                line_text = ""
                                for span in line.get("spans", []):
                                    line_text += span.get("text", "")
                                if line_text.strip():
                                    full_text += line_text + "\n"
            
            full_text += "\n"  # Page break
        
        return full_text
    except Exception as e:
        print(f"Error in adaptive text extraction: {e}")
        return ""


def _analyze_page_layout(page) -> Dict:
    """
    Analyzes page layout to detect columns and content structure.
    
    Uses text block positions to automatically detect column boundaries
    and content organization patterns.
    
    Returns:
        Dictionary with layout analysis including column boundaries,
        block distribution, and recommended extraction strategy
    """
    text_dict = page.get_text("dict")
    blocks = text_dict.get("blocks", [])
    
    if not blocks:
        return {"columns": 1, "strategy": "single_column"}
    
    # Extract block positions and dimensions
    block_positions = []
    for block in blocks:
        if "lines" in block:
            bbox = block.get("bbox", [0,0,0,0])
            if bbox[2] > bbox[0] and bbox[3] > bbox[1]:  # Valid bbox
                block_positions.append({
                    "left": bbox[0],
                    "top": bbox[1], 
                    "right": bbox[2],
                    "bottom": bbox[3],
                    "center_x": (bbox[0] + bbox[2]) / 2,
                    "center_y": (bbox[1] + bbox[3]) / 2,
                    "width": bbox[2] - bbox[0],
                    "height": bbox[3] - bbox[1],
                    "block": block
                })
    
    if not block_positions:
        return {"columns": 1, "strategy": "single_column"}
    
    # Analyze horizontal distribution to detect columns
    page_width = page.rect.width
    x_positions = [bp["center_x"] for bp in block_positions]
    
    # Use clustering to find column boundaries
    from collections import Counter
    
    # Bin x-positions into segments to find clusters
    segment_size = page_width / 20  # Divide page into 20 segments
    segments = [int(x / segment_size) for x in x_positions]
    segment_counts = Counter(segments)
    
    # Find peaks in distribution (column centers)
    peak_segments = []
    for segment, count in segment_counts.items():
        # A segment is a peak if it has more blocks than its neighbors
        left_count = segment_counts.get(segment - 1, 0)
        right_count = segment_counts.get(segment + 1, 0)
        if count > max(left_count, right_count) and count >= 2:
            peak_segments.append(segment)
    
    # Convert segments back to x-positions
    column_centers = [seg * segment_size + segment_size/2 for seg in peak_segments]
    column_centers.sort()
    
    # Determine column boundaries
    if len(column_centers) <= 1:
        return {
            "columns": 1,
            "strategy": "single_column", 
            "boundaries": [page_width]
        }
    elif len(column_centers) == 2:
        boundary = (column_centers[0] + column_centers[1]) / 2
        return {
            "columns": 2,
            "strategy": "two_column",
            "boundaries": [boundary, page_width],
            "column_centers": column_centers
        }
    else:
        # Multi-column layout - create boundaries between centers
        boundaries = []
        for i in range(len(column_centers) - 1):
            boundary = (column_centers[i] + column_centers[i + 1]) / 2
            boundaries.append(boundary)
        boundaries.append(page_width)
        
        return {
            "columns": len(column_centers),
            "strategy": "multi_column",
            "boundaries": boundaries,
            "column_centers": column_centers
        }


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


def normalize_text_for_llm(text: str) -> str:
    """
    Normalizes text for LLM processing while preserving helpful formatting.
    
    Removes PDF artifacts but maintains document structure that helps
    LLMs understand context, including:
    - Paragraph boundaries (double line breaks)
    - List structures
    - Section breaks
    - Table-like formatting
    
    Args:
        text: Raw text from PDF extraction
        
    Returns:
        Cleaned text optimized for LLM comprehension
        
    Normalization Steps:
    1. Remove hyphenated line breaks (preserves words across lines)
    2. Preserve paragraph breaks (double newlines)
    3. Clean excessive whitespace within lines
    4. Maintain single line breaks that indicate structure
    """
    # Remove hyphenated line breaks (e.g., "Homo sapi-\nens" -> "Homo sapiens")
    text = re.sub(r'-\s*\n\s*', '', text)
    
    # Preserve paragraph breaks by temporarily marking them
    text = re.sub(r'\n\s*\n', '||PARAGRAPH_BREAK||', text)
    
    # Clean up excessive whitespace within lines but preserve single line breaks
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs to single space
    text = re.sub(r'[ \t]*\n[ \t]*', '\n', text)  # Clean around line breaks
    
    # Restore paragraph breaks
    text = text.replace('||PARAGRAPH_BREAK||', '\n\n')
    
    # Remove excessive consecutive line breaks (max 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def _create_flexible_species_pattern(species_name: str) -> str:
    """
    Creates a regex pattern that can match species names even when split across lines.
    
    Handles cases where long species names are broken across lines in formatted text,
    which is common in PDFs with narrow columns or justified text.
    
    Args:
        species_name: The species name to search for (e.g., "Rhinoceros unicornis")
        
    Returns:
        Regex pattern that allows for line breaks between words
        
    Examples:
    - "Homo sapiens" → matches "Homo sapiens" or "Homo\nsapiens"
    - "Tyrannosaurus rex" → matches "Tyrannosaurus rex" or "Tyrannosaurus\nrex"
    
    Pattern Strategy:
    - Allows 1-5 whitespace characters (including newlines) between words
    - Includes hyphens to handle hyphenated line breaks
    - Maintains word boundaries to prevent false matches
    - Limits whitespace to prevent matching across unrelated text
    """
    # Split the species name into words
    words = species_name.split()
    
    if len(words) == 1:
        # Single word - use standard word boundary matching
        return r'\b' + re.escape(words[0]) + r'\b'
    
    # Multiple words - allow flexible spacing between them
    escaped_words = [re.escape(word) for word in words]
    
    # Create pattern with word boundaries
    pattern_parts = []
    
    for i, word in enumerate(escaped_words):
        if i == 0:
            # First word needs word boundary at start
            pattern_parts.append(r'\b' + word)
        elif i == len(escaped_words) - 1:
            # Last word needs word boundary at end  
            pattern_parts.append(word + r'\b')
        else:
            # Middle words
            pattern_parts.append(word)
    
    # Flexible separator that allows:
    # - Regular spaces
    # - Newlines 
    # - Hyphens (for hyphenated line breaks)
    # - Combinations thereof
    # Limited to 1-5 characters to prevent false matches across paragraphs
    flexible_separator = r'[\s\-]{1,5}'
    
    return flexible_separator.join(pattern_parts)


def get_species_context_chunks(
    full_text: str, species_df: pd.DataFrame, context_before: int, context_after: int
) -> Dict[str, List[str]]:
    """
    Extracts contextual text passages surrounding species mentions.
    
    Locates all occurrences of each species name in the document and
    extracts surrounding text context. This provides the textual
    information needed for data extraction algorithms to identify
    species-specific attributes.
    
    **Updated for LLM Processing**: Now extracts chunks from formatting-preserved
    text while maintaining species matching accuracy through dual-text search.
    
    **Line-Break Handling**: Uses flexible pattern matching to find species names
    even when split across lines in formatted PDFs, common in narrow columns.
    
    Args:
        full_text: Complete document text from PDF extraction
        species_df: DataFrame containing detected species names
        context_before: Number of characters to include before species mention
        context_after: Number of characters to include after species mention
        
    Returns:
        Dictionary mapping species names to lists of context passages
        (now with preserved formatting for better LLM comprehension)
        
    Scientific Rationale:
    - Context windows capture relevant information about species
    - Multiple contexts per species enable comprehensive data extraction
    - Robust searching handles nomenclatural variations and formatting
    - Preserved formatting helps LLMs understand document structure
    - Line-break tolerance ensures long species names are not missed
    
    Algorithm Details:
    - Uses flexible regex patterns to handle line breaks within species names
    - Searches in formatted text with structure preservation
    - Implements word boundary matching to avoid false positives
    - Deduplicates identical context passages
    - Case-insensitive matching for robustness
    - Fallback to simple patterns if flexible matching fails
    
    Context Window Design:
    - Size should balance information content vs. noise
    - Typical values: 200-500 characters before/after
    - Longer contexts for complex ecological descriptions
    - Formatting preservation aids LLM comprehension
    
    Line-Break Examples:
    - "Rhinoceros unicornis" matches "Rhinoceros\nunicornis"
    - "Panthera tigris altaica" matches "Panthera\ntigris altaica"
    """
    species_chunks = {}
    if species_df.empty:
        return species_chunks

    # Create formatted version for LLM processing
    formatted_full_text = normalize_text_for_llm(full_text)

    for _, row in species_df.iterrows():
        # --- ROBUST SPECIES NAME MATCHING ---
        # Use cleaned canonical name rather than messy verbatim text
        # This improves matching accuracy for formatted documents
        search_name = row["Name"]
        if not search_name:
            continue
        # --- END ROBUST MATCHING ---

        try:
            # Create flexible pattern that handles line breaks within species names
            flexible_pattern = _create_flexible_species_pattern(search_name)
            pattern = re.compile(flexible_pattern, re.IGNORECASE | re.MULTILINE)
        except re.error:
            # Fallback to simple pattern if flexible pattern fails
            try:
                pattern = re.compile(r'\b' + re.escape(search_name) + r'\b', re.IGNORECASE)
            except re.error:
                continue

        for match in pattern.finditer(formatted_full_text):
            match_start = match.start()
            match_end = match.end()

            # Extract context from formatted text (preserves structure for LLM)
            chunk_start = max(0, match_start - context_before)
            chunk_end = min(len(formatted_full_text), match_end + context_after)
            
            chunk = formatted_full_text[chunk_start:chunk_end]
            
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