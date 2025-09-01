"""
Species Name Discovery and Taxonomic Filtering Module

This module provides functions for identifying species names in text documents
and filtering them based on taxonomic criteria. It integrates with external
services (GNfinder, GBIF) to ensure accurate species identification and 
taxonomic validation.

Scientific Purpose:
- Automated species name recognition in biodiversity literature
- Taxonomic validation using authoritative databases
- Quality filtering to reduce false positives in species identification

Key Dependencies:
- GNfinder: Species name finding service
- GBIF: Global Biodiversity Information Facility for taxonomic backbone
- pygbif: Python interface to GBIF API
"""

import pandas as pd
import requests
import json
import tempfile
from pathlib import Path
from typing import Dict, Optional
from pygbif import species as gbif_species
import time
import streamlit as st
import re

# --- GNfinder Integration Functions ---
# GNfinder is a service for finding scientific names in text

def send_text_to_gnfinder(text: str, gnfinder_url: str) -> Optional[Dict]:
    """
    Submits text to GNfinder service for species name detection.
    
    GNfinder uses machine learning and taxonomic databases to identify
    scientific names in unstructured text, providing verification
    against authoritative taxonomic sources.
    
    Args:
        text: Input text document for species name detection
        gnfinder_url: URL of the GNfinder service endpoint
        
    Returns:
        JSON response containing detected names and verification data,
        or None if the request fails
        
    Scientific Context:
    - Enables automated biodiversity data extraction from literature
    - Provides taxonomic verification through multiple databases
    - Supports both exact and fuzzy name matching
    
    Text Preprocessing:
    - Removes extraction method artifacts (column headers, page markers)
    - Preserves original text structure and formatting
    - Maintains species names in context for better detection
    """
    # Clean text of extraction artifacts that might confuse GnFinder
    cleaned_text = _clean_text_for_gnfinder(text)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp_file:
        tmp_file.write(cleaned_text)
        tmp_file_path = tmp_file.name

    try:
        with open(tmp_file_path, "rb") as f:
            files = {"file": (Path(tmp_file_path).name, f, "text/plain")}
            params = {"verification": "true", "uniqueNames": "true"}
            response = requests.post(gnfinder_url, files=files, params=params, timeout=120)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"GNfinder error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Could not connect to GNfinder at {gnfinder_url}. Error: {e}")
        return None
    finally:
        Path(tmp_file_path).unlink()


def _clean_text_for_gnfinder(text: str) -> str:
    """
    Removes extraction method artifacts and formatting that might interfere with GnFinder.
    
    Our extraction methods sometimes add formatting markers, and scientific texts
    often contain species names in parentheses or brackets which can confuse
    GnFinder's detection algorithms.
    
    Cleaning steps:
    1. Remove extraction artifacts (column headers, page markers, etc.)
    2. Remove parentheses and brackets while preserving content
    3. Clean up resulting formatting issues
    
    Args:
        text: Raw extracted text with potential artifacts
        
    Returns:
        Cleaned text suitable for GnFinder processing
        
    Examples:
    - "Zandhagedis (Lacerta agilis)" → "Zandhagedis Lacerta agilis"
    - "[Species list: Homo sapiens]" → "Species list: Homo sapiens"
    - "See (Fig. 1)" → "See Fig. 1"
    """
    # Remove extraction method artifacts first
    text = re.sub(r'=== COLUMN \d+ ===\n?', '', text)
    text = re.sub(r'=== PAGE \d+ ===\n?', '', text)
    text = re.sub(r'<!-- Page \d+: \d+ columns detected -->\n?', '', text)
    text = re.sub(r'--- TABLES ON PAGE \d+ ---\n?', '', text)
    text = re.sub(r'Table \d+:\n?', '', text)
    
    # Remove parentheses and brackets while preserving content
    # This helps GnFinder detect species names that are often enclosed
    
    # Handle nested parentheses by working from inside out
    # First pass: remove innermost parentheses
    while re.search(r'\([^()]*\)', text):
        text = re.sub(r'\(([^()]*)\)', r' \1 ', text)
    
    # Remove square brackets
    text = re.sub(r'\[([^\]]*)\]', r' \1 ', text)
    
    # Clean up empty spaces that might result from empty parentheses
    text = re.sub(r'\s*\(\s*\)\s*', ' ', text)  # Remove empty parentheses
    
    # Clean up spacing issues that might result from parentheses removal
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single space
    text = re.sub(r'\s*\.\s*', '. ', text)  # Fix spacing around periods
    text = re.sub(r'\s*,\s*', ', ', text)  # Fix spacing around commas
    text = re.sub(r'\s*:\s*', ': ', text)  # Fix spacing around colons
    text = re.sub(r'\s*;\s*', '; ', text)  # Fix spacing around semicolons
    
    # Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Clean up any leading/trailing whitespace
    text = text.strip()
    
    return text

def parse_gnfinder_results(gnfinder_json: Dict) -> pd.DataFrame:
    """
    Converts GNfinder JSON response into structured DataFrame.
    
    Extracts key information from GNfinder's complex nested JSON structure,
    focusing on taxonomic verification results and name matching quality.
    This standardizes the data format for downstream processing.
    
    Args:
        gnfinder_json: Raw JSON response from GNfinder service
        
    Returns:
        DataFrame with columns for name variants, positions, and taxonomic info
        
    Data Schema:
    - Verbatim: Original text string found in document
    - Name: Cleaned scientific name
    - Start/End: Character positions in source text
    - MatchType: Quality of taxonomic database match
    - MatchedName/MatchedCanonical: Standardized nomenclature
    - ClassificationPath: Taxonomic hierarchy information
    """
    if not gnfinder_json or "names" not in gnfinder_json:
        return pd.DataFrame()
    
    data = []
    for item in gnfinder_json["names"]:
        # Handle both verified and unverified responses
        verification = item.get("verification", {})
        best_result = verification.get("bestResult", {}) if verification else {}
        
        # If no verification data, use the name itself as canonical
        verbatim = item.get("verbatim", "")
        name = item.get("name", "")
        
        # Use verification data if available, otherwise fall back to detected name
        if best_result:
            match_type = best_result.get("matchType", "Unverified")
            matched_name = best_result.get("matchedName", name)
            matched_canonical = best_result.get("matchedCanonicalFull", name)
            classification = best_result.get("classificationRanks", "")
        else:
            # For unverified results, use detected name as canonical
            match_type = "Unverified"
            matched_name = name
            matched_canonical = name
            classification = ""
        
        data.append({
            "Verbatim": verbatim,
            "Name": name,
            "Start": item.get("start", 0),
            "End": item.get("end", 0),
            "MatchType": match_type,
            "MatchedName": matched_name,
            "MatchedCanonical": matched_canonical,
            "ClassificationPath": classification
        })
    return pd.DataFrame(data)

def filter_initial_species(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies quality filters to species name detection results.
    
    This function implements a multi-step filtering process to improve
    the accuracy of species identification by:
    1. Retaining valid taxonomic matches (exact and unverified)
    2. Validating binomial/trinomial nomenclature format (including taxonomic abbreviations)
    3. Prioritizing highest taxonomic detail (subspecies over species) for verified matches only
    4. Eliminating duplicate detections
    
    Scientific Rationale:
    - Accepts both verified and unverified matches to maintain sensitivity
    - Handles taxonomic abbreviations (ssp., subsp., var., f.) in subspecies names
    - Applies subspecies filtering conservatively (verified matches only)
    - Preserves unverified matches to avoid over-filtering legitimate species
    
    Args:
        df: DataFrame from parse_gnfinder_results()
        
    Returns:
        Filtered DataFrame with high-confidence species identifications
        
    Algorithm Details:
    - Uses enhanced regex for proper species name format validation
    - Supports taxonomic abbreviations like "Genus species ssp. subspecies"
    - Only removes redundant species when verified subspecies are present
    - Preserves all unverified matches to maintain detection sensitivity
    """
    if df.empty:
        return df
    
    # Step 1: Basic filtering for valid binomial/trinomial matches
    # Accept both "Exact" and "Unverified" matches (GnFinder sometimes returns unverified)
    valid_match_types = ["Exact", "Unverified"]
    df_filtered = df[df["MatchType"].isin(valid_match_types)].copy()
    
    # Filter for proper binomial/trinomial nomenclature (including taxonomic abbreviations)
    # Pattern matches: "Genus species" or "Genus species subspecies" or "Genus species ssp. subspecies"
    binomial_regex = r"^\s*([A-Z][a-z]+)\s+([a-z]+)(\s+(ssp\.|subsp\.|var\.|f\.)?\s*[a-z]+)?\s*$"
    df_filtered['MatchedCanonical'] = df_filtered['MatchedCanonical'].astype(str)
    df_filtered = df_filtered[df_filtered["MatchedCanonical"].str.match(binomial_regex, na=False)]

    if df_filtered.empty:
        return df_filtered

    # Step 2: Get a unique, sorted list of all canonical names found.
    # Sorting is crucial as it places species names directly before their subspecies.
    canonical_names = sorted(df_filtered["MatchedCanonical"].unique())
    
    # Step 3: Prioritize highest taxonomic detail - but only for verified matches
    # For unverified matches, keep everything as GnFinder detection alone is less reliable
    # This approach maintains the most specific taxonomic information for verified species
    # while being conservative with unverified detections
    names_to_remove = set()
    
    # Only apply subspecies filtering to verified/exact matches
    verified_df = df_filtered[df_filtered["MatchType"] == "Exact"]
    
    if not verified_df.empty:
        # Get canonical names from verified matches only
        verified_canonical_names = sorted(verified_df["MatchedCanonical"].unique())
        
        # Group verified names by species to identify subspecies relationships
        species_groups = {}
        for name in verified_canonical_names:
            parts = name.split()
            if len(parts) >= 2:
                species_key = f"{parts[0]} {parts[1]}"
                if species_key not in species_groups:
                    species_groups[species_key] = []
                species_groups[species_key].append(name)
        
        # For each species group, keep only the most detailed taxonomic level
        for species_key, variants in species_groups.items():
            if len(variants) > 1:
                # Sort by length (number of parts) - longer names are more specific
                variants_by_detail = sorted(variants, key=lambda x: len(x.split()), reverse=True)
                
                # Check if we have subspecies (3+ parts) vs species (2 parts)
                subspecies = [v for v in variants_by_detail if len(v.split()) >= 3]
                species_only = [v for v in variants_by_detail if len(v.split()) == 2]
                
                if subspecies and species_only:
                    # We have both subspecies and species - remove the less specific species
                    # Keep all subspecies as they represent different taxonomic entities
                    names_to_remove.update(species_only)
                # If we only have subspecies or only species, keep all (no conflict)
            
    # Step 4: Filter the DataFrame, keeping only the rows whose canonical names
    # are NOT in our set of less-specific names to remove.
    final_df = df_filtered[~df_filtered["MatchedCanonical"].isin(names_to_remove)]

    # Step 5: Final de-duplication on the original 'Name' to ensure one result per verbatim find.
    return final_df.drop_duplicates(subset=["Name"], keep="first").reset_index(drop=True)

# --- GBIF Taxonomic Validation Functions ---
# GBIF provides authoritative taxonomic backbone data

@st.cache_data(ttl="1d")
def get_higher_taxonomy(species_name: str) -> Optional[Dict]:
    """
    Retrieves taxonomic hierarchy from GBIF for a given species.
    
    Queries the Global Biodiversity Information Facility (GBIF) taxonomic
    backbone to obtain higher-level taxonomic classification. Results are
    cached for 24 hours to minimize API calls and improve performance.
    
    Args:
        species_name: Scientific name for taxonomic lookup
        
    Returns:
        Dictionary containing taxonomic ranks (kingdom through family),
        or None if species not found in GBIF
        
    Scientific Context:
    - GBIF maintains the most comprehensive taxonomic backbone
    - Enables filtering by taxonomic groups for focused studies
    - Supports quality control through authoritative classification
    
    Caching Strategy:
    - 24-hour TTL balances data freshness with performance
    - Reduces load on GBIF servers during batch processing
    """
    try:
        response = gbif_species.name_backbone(name=species_name, rank='SPECIES', strict=False)
        if response and response.get('matchType') != 'NONE':
            return {
                'kingdom': response.get('kingdom'),
                'phylum': response.get('phylum'),
                'class': response.get('class'),
                'order': response.get('order'),
                'family': response.get('family'),
            }
        return None
    except Exception as e:
        print(f"Error querying GBIF for {species_name}: {e}")
        return None

def filter_by_taxonomy(df: pd.DataFrame, rank: str, name: str) -> pd.DataFrame:
    """
    Filters species list by taxonomic group membership.
    
    Applies taxonomic filtering to focus extraction on specific biological
    groups (e.g., only birds, only flowering plants). This is essential
    for targeted biodiversity studies and reduces processing time for
    large documents.
    
    Args:
        df: DataFrame of detected species names
        rank: Taxonomic rank for filtering (kingdom, phylum, class, order, family)
        name: Name of the taxonomic group to retain
        
    Returns:
        Filtered DataFrame containing only species from specified taxonomic group
        
    Performance Considerations:
    - Includes progress bar for long-running operations
    - Implements rate limiting to respect GBIF API guidelines
    - Caches taxonomic lookups to minimize redundant queries
    
    Scientific Applications:
    - Taxonomic group-specific conservation assessments
    - Focused studies on particular lineages
    - Quality control by excluding unlikely taxonomic matches
    """
    if df.empty or not rank or not name or name.lower() == 'any':
        return df

    filtered_indices = []
    total = len(df)
    progress_bar = st.progress(0, text=f"Applying taxonomic filter... (0/{total})")

    for i, row in df.iterrows():
        species_name = row["Name"]
        taxonomy = get_higher_taxonomy(species_name)
        
        if not taxonomy:
            filtered_indices.append(i)
        else:
            actual_rank_value = taxonomy.get(rank)
            if isinstance(actual_rank_value, str) and actual_rank_value.lower() == name.lower():
                filtered_indices.append(i)
        
        time.sleep(0.05)
        progress_bar.progress((i + 1) / total, text=f"Applying taxonomic filter... ({i+1}/{total})")

    progress_bar.empty()
    return df.loc[filtered_indices].reset_index(drop=True)