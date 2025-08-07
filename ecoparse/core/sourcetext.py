import io
import re
from typing import Optional, Dict, List
import pandas as pd
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_file_buffer: io.BytesIO) -> str:
    # ... (this function is correct and unchanged)
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
    # ... (this function is correct and unchanged)
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
    # ... (this function is correct and unchanged)
    text = re.sub(r'-\s*\n\s*', '', text)
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_species_context_chunks(
    full_text: str, species_df: pd.DataFrame, context_before: int, context_after: int
) -> Dict[str, List[str]]:
    """
    Finds text chunks surrounding species mentions by searching within the
    normalized text, ignoring potentially invalid GNfinder offsets.
    """
    # --- START OF FIX ---
    species_chunks = {}
    if species_df.empty:
        return species_chunks

    normalized_full_text = normalize_text_for_search(full_text)

    # We iterate through the species DataFrame to get the names to search for.
    for _, row in species_df.iterrows():
        species_name = row["Name"]
        verbatim_name = row["Verbatim"]
        
        # Normalize the name we're searching for, just like the full text.
        normalized_verbatim = normalize_text_for_search(verbatim_name)
        if not normalized_verbatim:
            continue

        # Create a robust regex pattern. \b ensures we match whole words.
        # re.IGNORECASE makes the search case-insensitive.
        try:
            pattern = re.compile(r'\b' + re.escape(normalized_verbatim) + r'\b', re.IGNORECASE)
        except re.error:
            # Handle cases where the verbatim name creates an invalid regex
            continue

        # Use finditer to find ALL occurrences of the species name in the document.
        for match in pattern.finditer(normalized_full_text):
            # Get the start and end positions from THIS match, which are valid
            # for the normalized_full_text.
            match_start = match.start()
            match_end = match.end()

            # Calculate the slice boundaries for the context chunk.
            chunk_start = max(0, match_start - context_before)
            chunk_end = min(len(normalized_full_text), match_end + context_after)
            
            # Extract the chunk from the same normalized text we searched in.
            chunk = normalized_full_text[chunk_start:chunk_end]
            
            # Initialize the list for this species if it's the first time we've found it.
            if species_name not in species_chunks:
                species_chunks[species_name] = []
            
            species_chunks[species_name].append(chunk)

    return species_chunks
    # --- END OF FIX ---

def get_species_page_images(pdf_buffer: io.BytesIO, species_df: pd.DataFrame) -> Dict[str, List[bytes]]:
    # ... (this function is correct and unchanged)
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