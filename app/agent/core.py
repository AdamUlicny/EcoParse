import os
import json
import yaml
import time
import io
import tempfile
import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
from openai import OpenAI
from google import genai
from google.genai import types

from ecoparse.core.sourcetext import trim_pdf_pages, extract_text_from_pdf
from ecoparse.core.finders import send_text_to_gnfinder, parse_gnfinder_results, filter_initial_species, filter_by_taxonomy
from ecoparse.core.extractor import Extractor


TETRAPOD_GROUPS = [
    ("class", "Amphibia"),
    ("class", "Mammalia"),
    ("class", "Aves"),
    ("class", "Reptilia"), # Just in case
    ("order", "Testudines"),
    ("order", "Squamata"),
    ("order", "Rhynchocephalia"),
    ("order", "Crocodilia")
]

def analyze_pdf_page_range_with_gemini(pdf_buffer: bytes, api_key: str) -> tuple[int, int]:
    """Uses Gemini 2.5 Flash to identify the start and end pages of the assessment, trimming biblio."""
    if not api_key:
        raise ValueError("Gemini API key not configured")
        
    client = genai.Client(api_key=api_key)
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_buffer)
        tmp_path = tmp.name
        
    try:
        # We upload the file using the files API for larger documents
        gemini_file = client.files.upload(file=tmp_path, config={'mime_type': 'application/pdf'})
        
        while gemini_file.state.name == "PROCESSING":
            time.sleep(2)
            gemini_file = client.files.get(name=gemini_file.name)
            
        prompt = (
            "Analyze this document. Identify the start and end page numbers of the main assessment content. "
            "Tables with species and threats are often at the end of a document, but before or after the bibliography. "
            "Please exclude the bibliography/references section if it occurs at the end. "
            "Return ONLY a JSON object with 'start_page' and 'end_page' as integers. Note: these are actual page numbers, starting from 1."
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[gemini_file, prompt],
            config={"response_mime_type": "application/json"}
        )
        
        result = json.loads(response.text)
        client.files.delete(name=gemini_file.name)
        
        num_pages = len(PdfReader(io.BytesIO(pdf_buffer)).pages)
        start_page = max(1, result.get("start_page", 1))
        end_page = min(num_pages, result.get("end_page", num_pages))
        
        return start_page, end_page
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def generate_config_with_openrouter(context: str, api_key: str) -> dict:
    """Uses OpenRouter to generate data_fields config.yml based on user context."""
    if not api_key:
        raise ValueError("OpenRouter API key not configured")
        
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    prompt = f"""
You are an expert at configuring ecological data extraction pipelines.
The user wants to extract specific categories or assessments from documents.
User context: '{context}'

Generate a YAML configuration matching the `data_fields` format.
Only return valid YAML, with no markdown formatting or backticks around it, just the YAML string. Make sure to accurately capture the specific fields the user wants as well as generic notes/context.
Format example:
data_fields:
  - name: "IUCN Status"
    description: "The conservation status of the species."
    type: "string"
    required: true
"""
    
    response = client.chat.completions.create(
        model="anthropic/claude-3.5-sonnet",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    
    yaml_text = response.choices[0].message.content
    if yaml_text.startswith("```yaml"):
        yaml_text = yaml_text.split("\n", 1)[1]
    if yaml_text.startswith("```"):
        yaml_text = yaml_text.split("\n", 1)[1]
    if yaml_text.endswith("```"):
        yaml_text = yaml_text.rsplit("\n", 1)[0]
        
    return yaml.safe_load(yaml_text)


def run_agent_pipeline(pdf_buffer: bytes, context: str, openrouter_key: str, gemini_key: str, gnfinder_url: str, progress_callback=None) -> tuple[dict, list]:
    """Executes the full automated agent pipeline."""
    
    # 1. Page Range Analysis
    if progress_callback: progress_callback("Analyzing PDF structure with Gemini 2.5 Flash...", 10)
    start_page, end_page = analyze_pdf_page_range_with_gemini(pdf_buffer, gemini_key)
    
    # Trim the PDF
    if progress_callback: progress_callback(f"Trimming PDF (Pages {start_page}-{end_page}) and Extracting Text...", 20)
    trimmed_buffer = trim_pdf_pages(io.BytesIO(pdf_buffer), start_page, end_page)
    full_text = extract_text_from_pdf(trimmed_buffer, method="PyMuPDF")
    
    # 2. Config Generation
    if progress_callback: progress_callback("Generating extraction config via OpenRouter...", 30)
    config = generate_config_with_openrouter(context, openrouter_key)
    
    # 3. Species ID
    if progress_callback: progress_callback("Discovering Species with GNfinder...", 40)
    gnfinder_res = send_text_to_gnfinder(full_text, gnfinder_url, offline_mode=False)
    if not gnfinder_res:
        raise ValueError("GNfinder request failed.")
    
    df_raw = parse_gnfinder_results(gnfinder_res)
    species_df = filter_initial_species(df_raw)
    
    # 4. Taxonomic Filtering (Tetrapods)
    if progress_callback: progress_callback("Filtering for Tetrapod species...", 50)
    filtered_dfs = []
    
    for rank, name in TETRAPOD_GROUPS:
        # Keep it simple, fuzzy off, unverified off
        df_filtered = filter_by_taxonomy(species_df, rank, name, include_fuzzy=False, include_higherrank=False, include_unverified=False)
        if not df_filtered.empty:
            filtered_dfs.append(df_filtered)
            
    if filtered_dfs:
        final_species_df = pd.concat(filtered_dfs, ignore_index=True).drop_duplicates(subset=["Name"]).reset_index(drop=True)
    else:
        final_species_df = pd.DataFrame(columns=species_df.columns if not species_df.empty else ["Name"])
        
    if final_species_df.empty:
        if progress_callback: progress_callback("No Tetrapod species found. Halting.", 100)
        return config, []
        
    species_list = final_species_df["Name"].tolist()
    
    # 5. Extraction
    if progress_callback: progress_callback(f"Extracting data for {len(species_list)} species using Gemini 2.5 Flash...", 70)
    
    llm_config = {
        "provider": "Google Gemini",
        "model": "gemini-2.5-flash",
        "api_key": gemini_key,
        "concurrent_requests": 5
    }
    
    extractor = Extractor(project_config=config, llm_config=llm_config)
    
    source_context = {
        "extraction_method": "Image-based",
        "pdf_buffer": trimmed_buffer.getvalue(),
        "species_df": final_species_df,
        "full_text": full_text # For fallback if needed
    }
    
    results, runtime, in_tokens, out_tokens = extractor.run_extraction(species_list, source_context)
    
    if progress_callback: progress_callback("Extraction complete!", 100)
    
    return config, results
