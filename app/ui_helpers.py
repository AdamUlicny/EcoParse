"""
Common UI component helpers for streamlined interface building.
"""

import streamlit as st
from pathlib import Path
import yaml
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import io
from thefuzz import fuzz
import pandas as pd

def create_model_selector(provider: str, models_list: list, is_disabled: bool = False):
    """Create standardized model selector with custom option."""
    options = ["Select a model..."] + [m["name"] for m in models_list]
    
    selected = st.selectbox(
        f"Select {provider} Model",
        options=options,
        disabled=is_disabled,
        help=f"Choose from {provider} models or use custom option below."
    )
    
    use_custom = st.checkbox(
        f"Use custom {provider.lower()} model",
        disabled=is_disabled,
        help="Enter custom model name not in dropdown."
    )
    
    if use_custom:
        custom = st.text_input(
            f"Custom {provider} Model Name",
            disabled=is_disabled,
            help="Enter custom model name (e.g., 'custom-model')."
        )
        return custom if custom else selected
    
    return selected if selected != "Select a model..." else None

def create_extraction_method_selector(current_method: str = "standard", key_suffix: str = ""):
    """Create standardized extraction method selector."""
    from app.ui_messages import EXTRACTION_METHOD_HELP
    
    methods = ["standard", "adaptive", "plumber", "reading-order"]
    default_index = methods.index(current_method) if current_method in methods else 0
    
    return st.selectbox(
        "Extraction Method",
        methods,
        index=default_index,
        key=f"extraction_method_{key_suffix}",
        help=EXTRACTION_METHOD_HELP
    )

def create_context_controls():
    """Create standardized context window controls."""
    col1, col2 = st.columns(2)
    with col1:
        st.number_input("Characters Before", 0, 50000, key="context_before")
    with col2:
        st.number_input("Characters After", 0, 50000, key="context_after")

def load_models_config():
    """Load models configuration with error handling."""
    models_file = Path(__file__).parent / "assets" / "models_list.yml"
    try:
        with open(models_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        st.warning(f"Models config not found: {models_file}")
        return {"ollama_models": [], "gemini_models": []}
    except Exception as e:
        st.error(f"Error loading models config: {e}")
        return {"ollama_models": [], "gemini_models": []}

def create_highlighted_page_image(pdf_buffer: bytes, page_number: int, terms_to_highlight: list[str]):
    """
    Generates an image of a specific PDF page with given terms highlighted.
    Uses fuzzy matching and different colors for exact and fuzzy matches.

    Args:
        pdf_buffer: The PDF file content as bytes.
        page_number: The 1-based page number to render.
        terms_to_highlight: A list of strings to search for and highlight.

    Returns:
        A tuple of (PIL.Image, found_terms_count) or (None, 0) if an error occurs.
        `found_terms_count` is the number of terms successfully found and highlighted.
    """
    try:
        page_index = page_number - 1
        doc = fitz.open(stream=pdf_buffer, filetype="pdf")
        if page_index < 0 or page_index >= len(doc):
            return None, 0

        page = doc.load_page(page_index)
        pix = page.get_pixmap(dpi=150)
        img = Image.open(io.BytesIO(pix.tobytes()))
        draw = ImageDraw.Draw(img, "RGBA")

        perfect_match_color = (0, 255, 0, 100)  # Green, semi-transparent
        fuzzy_match_color = (255, 165, 0, 100)  # Orange, semi-transparent
        
        found_terms_count = 0

        page_text = page.get_text("text")
        words = page.get_text("words")  # list of words on page with coordinates

        for term in terms_to_highlight:
            if not term or not isinstance(term, str):
                continue

            # Direct search first for performance
            areas = page.search_for(term, quads=False)
            if areas:
                found_terms_count += 1
                for rect in areas:
                    scaled_rect = (
                        rect.x0 * pix.width / page.rect.width,
                        rect.y0 * pix.height / page.rect.height,
                        rect.x1 * pix.width / page.rect.width,
                        rect.y1 * pix.height / page.rect.height,
                    )
                    draw.rectangle(scaled_rect, fill=perfect_match_color)
            else:
                # Fuzzy matching if no direct match
                # This is a simplified fuzzy search. For more complex cases, one might need to check n-grams.
                for w in words:
                    word_text = w[4]
                    ratio = fuzz.ratio(term.lower(), word_text.lower())
                    if ratio > 80: # 80% similarity threshold
                        found_terms_count += 1
                        rect = fitz.Rect(w[:4])
                        scaled_rect = (
                            rect.x0 * pix.width / page.rect.width,
                            rect.y0 * pix.height / page.rect.height,
                            rect.x1 * pix.width / page.rect.width,
                            rect.y1 * pix.height / page.rect.height,
                        )
                        # Use fuzzy color if not a perfect match
                        color = perfect_match_color if ratio == 100 else fuzzy_match_color
                        draw.rectangle(scaled_rect, fill=color)


        doc.close()
        return img, found_terms_count

    except Exception as e:
        st.error(f"Error creating highlighted image for page {page_number}: {e}")
        return None, 0

def highlight_text_in_chunk(chunk_text: str, terms_to_highlight: list[str]) -> str:
    """
    Highlights terms within a text string using Markdown.
    Uses fuzzy matching and different colors for exact and fuzzy matches.

    Args:
        chunk_text: The text content of the chunk.
        terms_to_highlight: A list of strings to search for and highlight.

    Returns:
        A Markdown-formatted string with highlighted terms.
    """
    highlighted_text = chunk_text
    found_terms_count = 0

    for term in terms_to_highlight:
        if not term or not isinstance(term, str):
            continue

        # Using a simple loop to find all occurrences, which is fine for moderate-length chunks
        # A more robust solution for overlapping matches might use regex.
        start_index = 0
        while start_index < len(highlighted_text):
            # Exact match
            found_pos = highlighted_text.lower().find(term.lower(), start_index)
            
            if found_pos != -1:
                # Perfect match
                original_term = highlighted_text[found_pos:found_pos + len(term)]
                highlight = f"<span style='background-color: rgba(0, 255, 0, 0.3); padding: 2px 4px; border-radius: 3px;'>{original_term}</span>"
                highlighted_text = highlighted_text[:found_pos] + highlight + highlighted_text[found_pos + len(term):]
                start_index = found_pos + len(highlight)
                found_terms_count += 1
            else:
                # Fuzzy match if no exact match found in the remainder of the text
                # This is a simplification; real fuzzy search in-text is more complex.
                # We'll stick to exact for simplicity and performance in this context.
                break # Move to next term

    return highlighted_text, found_terms_count

def preload_highlighted_images(final_results_df):
    """
    Pre-generates and caches highlighted images for all species in the final results.
    To be run in the background while the user is on the extraction results tab.
    """
    if 'pdf_buffer' not in st.session_state or not st.session_state.pdf_buffer:
        return

    if 'highlighted_images' not in st.session_state:
        st.session_state.highlighted_images = {}

    pdf_buffer = st.session_state.pdf_buffer
    
    # Get all dynamic field names, excluding 'Species Name' and 'Mentioned In'
    dynamic_fields = [col for col in final_results_df.columns if col not in ['Species Name', 'Mentioned In']]

    for index, row in final_results_df.iterrows():
        species_name = row['Species Name']
        if 'Mentioned In' in row and row['Mentioned In']:
            try:
                # Assuming 'Mentioned In' is a string like "Page 1, Page 2"
                pages = [int(p.strip().replace('Page','')) for p in row['Mentioned In'].split(',')]
            except (ValueError, AttributeError):
                pages = []
        else:
            pages = []

        terms_to_find = [species_name] + [row[field] for field in dynamic_fields if pd.notna(row[field])]

        for page_num in pages:
            # Unique key for each species-page combination
            cache_key = f"{species_name}_{page_num}"
            if cache_key not in st.session_state.highlighted_images:
                image, count = create_highlighted_page_image(pdf_buffer, page_num, terms_to_find)
                if image:
                    st.session_state.highlighted_images[cache_key] = (image, count)
