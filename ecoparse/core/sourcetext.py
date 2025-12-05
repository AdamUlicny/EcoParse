"""
PDF Text Processing and Context Extraction Module
"""

import io
import re
from typing import Optional, Dict, List
import pandas as pd
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF
import pdfplumber
import unicodedata

def extract_text_from_pdf(pdf_file_buffer: io.BytesIO, method: str = "standard") -> str:
    """
    Extract text from PDF with layout-aware options.
    """
    if method == "adaptive":
        return _extract_text_adaptive(pdf_file_buffer)
    elif method == "plumber":
        return _extract_text_plumber(pdf_file_buffer)
    elif method == "reading-order":
        return _extract_text_reading_order(pdf_file_buffer)
    else:
        return _extract_text_standard(pdf_file_buffer)


def _extract_text_standard(pdf_file_buffer: io.BytesIO) -> str:
    """Standard text extraction with Unicode handling."""
    full_text = ""
    try:
        pdf_file_buffer.seek(0)
        pdf_data = pdf_file_buffer.read()
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        for page_num, page in enumerate(doc):
            try:
                # Try different extraction methods for better Unicode support
                # Method 1: Standard text extraction
                page_text = page.get_text()
                
                # Method 2: If that doesn't work, try extracting as bytes and decode
                if not page_text or page_text.count('`') > page_text.count('ž'):
                    # Likely encoding issue, try alternative
                    text_dict = page.get_text("dict")
                    page_text = ""
                    for block in text_dict.get("blocks", []):
                        if "lines" in block:
                            for line in block["lines"]:
                                for span in line["spans"]:
                                    span_text = span.get("text", "")
                                    # Handle potential encoding issues
                                    if isinstance(span_text, bytes):
                                        try:
                                            span_text = span_text.decode('utf-8')
                                        except:
                                            span_text = span_text.decode('utf-8', errors='replace')
                                    page_text += span_text
                                page_text += "\n"
                
                if page_text:
                    full_text += f"=== PAGE {page_num + 1} ===\n"
                    full_text += page_text + "\n"
                    
            except Exception as e:
                print(f"Error processing page {page_num + 1}: {e}")
                continue
                
        doc.close()
        
        return full_text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""


def _extract_text_plumber(pdf_file_buffer: io.BytesIO) -> str:
    """PDFplumber extraction for complex layouts and tables."""
    full_text = ""
    try:
        pdf_file_buffer.seek(0)
        
        with pdfplumber.open(pdf_file_buffer) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    # Extract text using PDFplumber's layout analysis
                    page_text = page.extract_text()
                    
                    if page_text:
                        # Ensure proper UTF-8 encoding
                        if isinstance(page_text, bytes):
                            page_text = page_text.decode('utf-8', errors='replace')
                        
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
                                        # Ensure proper UTF-8 encoding for table cells
                                        encoded_cells = []
                                        for cell in row:
                                            if cell:
                                                cell_text = str(cell)
                                                if isinstance(cell_text, bytes):
                                                    cell_text = cell_text.decode('utf-8', errors='replace')
                                                encoded_cells.append(cell_text)
                                            else:
                                                encoded_cells.append("")
                                        row_text = " | ".join(encoded_cells)
                                        full_text += row_text + "\n"
                                full_text += "\n"
                    
                except Exception as e:
                    print(f"Error processing page {page_num + 1} with PDFplumber: {e}")
                    # Fallback to basic text extraction for this page
                    try:
                        basic_text = page.extract_text()
                        if basic_text:
                            # Ensure proper UTF-8 encoding
                            if isinstance(basic_text, bytes):
                                basic_text = basic_text.decode('utf-8', errors='replace')
                            full_text += f"\n=== PAGE {page_num + 1} (basic) ===\n"
                            full_text += basic_text + "\n"
                    except:
                        continue
        
        return full_text
        
    except Exception as e:
        print(f"Error in PDFplumber text extraction: {e}")
        return ""


def _extract_text_adaptive(pdf_file_buffer: io.BytesIO) -> str:
    """Adaptive extraction with automatic layout detection."""
    full_text = ""
    try:
        pdf_file_buffer.seek(0)
        # Try to open with explicit encoding handling
        pdf_data = pdf_file_buffer.read()
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        for page_num, page in enumerate(doc):
            # Analyze page layout
            layout = _analyze_page_layout(page)
            
            # Try different text extraction methods for better encoding
            try:
                # Method 1: Use simple text extraction first (often better for encoding)
                simple_text = page.get_text()
                if simple_text and any(ord(c) > 127 for c in simple_text):  # Contains non-ASCII
                    # Add layout information as comment
                    full_text += f"\n<!-- Page {page_num + 1}: {layout['columns']} columns detected -->\n"
                    full_text += simple_text + "\n"
                    continue
            except:
                pass
            
            # Method 2: Fall back to dict-based extraction if simple fails
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
                            span_text = span.get("text", "")
                            # Ensure proper UTF-8 encoding
                            if isinstance(span_text, bytes):
                                span_text = span_text.decode('utf-8', errors='replace')
                            line_text += span_text
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
                                    span_text = span.get("text", "")
                                    # Ensure proper UTF-8 encoding
                                    if isinstance(span_text, bytes):
                                        span_text = span_text.decode('utf-8', errors='replace')
                                    line_text += span_text
                                if line_text.strip():
                                    full_text += line_text + "\n"
            
            full_text += "\n"  # Page break
        
        return full_text
    except Exception as e:
        print(f"Error in adaptive text extraction: {e}")
        return ""


def _extract_text_reading_order(pdf_file_buffer: io.BytesIO) -> str:
    """
    Reading-order text extraction using PyPDF2's reading order method.
    This method focuses on extracting text in the proper reading order,
    which should correctly position headers and maintain document structure.
    """
    full_text = ""
    try:
        pdf_file_buffer.seek(0)
        reader = PdfReader(pdf_file_buffer)
        
        for page_num, page in enumerate(reader.pages):
            try:
                # Use PyPDF2's text extraction which follows reading order
                page_text = page.extract_text()
                
                if page_text and page_text.strip():
                    full_text += f"\n=== PAGE {page_num + 1} ===\n"
                    full_text += page_text + "\n"
                    
            except Exception as e:
                print(f"Error extracting text from page {page_num + 1}: {e}")
                continue
        
        return full_text
        
    except Exception as e:
        print(f"Error in reading-order text extraction: {e}")
        return ""


def _analyze_page_layout(page) -> Dict:
    """
    Analyzes page layout to detect columns and content structure.
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
    """Extract page range from PDF (1-indexed, inclusive)."""
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
    """
    # Apply NFKC normalization to decompose ligatures and other variants
    text = unicodedata.normalize('NFKC', text)
    
    # Original normalization
    text = re.sub(r'-\s*\n\s*', '', text)
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_text_for_llm(text: str) -> str:
    """
    Normalizes text for LLM processing while preserving helpful formatting.
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
    Creates a regex pattern that can match species names even when split across lines
    or surrounded by punctuation like parentheses.
    """
    # Split the species name into words
    words = species_name.split()
    
    if len(words) == 1:
        # Single word - use flexible boundary matching that handles punctuation
        return r'(?<!\w)' + re.escape(words[0]) + r'(?!\w)'
    
    # Multiple words - allow flexible spacing between them
    escaped_words = [re.escape(word) for word in words]
    
    # Create pattern with flexible boundaries
    pattern_parts = []
    
    for i, word in enumerate(escaped_words):
        if i == 0:
            # First word needs flexible boundary at start (handles parentheses, etc.)
            pattern_parts.append(r'(?<!\w)' + word)
        elif i == len(escaped_words) - 1:
            # Last word needs flexible boundary at end
            pattern_parts.append(word + r'(?!\w)')
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
    extracts surrounding text context.
    """
    species_chunks = {}
    if species_df.empty:
        return species_chunks

    # Create formatted version for LLM processing
    formatted_full_text = normalize_text_for_llm(full_text)

    for _, row in species_df.iterrows():
        search_name = row["Name"]
        if not search_name:
            continue

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

def get_species_partial_page_chunks(full_text: str, species_df: pd.DataFrame, chars_from_top: int = 500, chars_from_bottom: int = 500) -> Dict[str, List[str]]:
    """
    Extract partial page content (top + bottom) for each species mention.
    """
    species_chunks = {}
    if species_df.empty:
        return species_chunks

    # Split text by page markers
    pages = re.split(r'=== PAGE (\d+) ===', full_text)
    
    # Create a list of (page_number, page_text) tuples
    page_contents = []
    for i in range(1, len(pages), 2):
        if i + 1 < len(pages):
            page_num = int(pages[i])
            page_text = pages[i + 1]
            page_contents.append((page_num, page_text))
    
    # For each species, find all pages where it's mentioned
    for _, row in species_df.iterrows():
        search_name = row["Name"]
        if not search_name:
            continue
            
        species_chunks[search_name] = []
        
        # Check each page for this species
        for page_num, page_text in page_contents:
            # Case-insensitive search for species mentions
            if search_name.lower() in page_text.lower():
                # Create partial page chunk
                page_text_clean = page_text.strip()
                
                if len(page_text_clean) <= (chars_from_top + chars_from_bottom):
                    # Page is short enough, use full content
                    partial_chunk = f"=== PAGE {page_num} ===\n{page_text_clean}"
                else:
                    # Extract top and bottom portions
                    top_portion = page_text_clean[:chars_from_top].strip()
                    bottom_portion = page_text_clean[-chars_from_bottom:].strip()
                    
                    # Create formatted partial page chunk
                    partial_chunk = f"""=== PAGE {page_num} (Top {chars_from_top} + Bottom {chars_from_bottom} chars) ===
TOP SECTION:
{top_portion}

... [MIDDLE CONTENT OMITTED - {len(page_text_clean) - chars_from_top - chars_from_bottom} characters] ...

BOTTOM SECTION:
{bottom_portion}"""
                
                species_chunks[search_name].append(partial_chunk)
    
    return species_chunks

def get_species_full_page_chunks(full_text: str, species_df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Extract full page content for each species mention.
    """
    species_chunks = {}
    if species_df.empty:
        return species_chunks

    # Split text by page markers
    pages = re.split(r'=== PAGE (\d+) ===', full_text)
    
    # Create a list of (page_number, page_text) tuples
    page_contents = []
    for i in range(1, len(pages), 2):
        if i + 1 < len(pages):
            page_num = int(pages[i])
            page_text = pages[i + 1]
            page_contents.append((page_num, page_text))
    
    # For each species, find all pages where it's mentioned
    for _, row in species_df.iterrows():
        search_name = row["Name"]
        if not search_name:
            continue
            
        species_chunks[search_name] = []
        
        # Check each page for this species
        for page_num, page_text in page_contents:
            # Case-insensitive search for species mentions
            if search_name.lower() in page_text.lower():
                # Add full page content as a chunk
                full_page_chunk = f"=== PAGE {page_num} ===\n{page_text}"
                species_chunks[search_name].append(full_page_chunk)
    
    return species_chunks

def get_species_page_images(pdf_buffer: io.BytesIO, species_df: pd.DataFrame) -> Dict[str, List[bytes]]:
    """
    Generates page images for species mentions in PDF documents.
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