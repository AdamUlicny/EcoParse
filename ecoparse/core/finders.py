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
    """
    # ... (this function remains the same)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp_file:
        tmp_file.write(text)
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
    # ... (this function remains the same)
    if not gnfinder_json or "names" not in gnfinder_json:
        return pd.DataFrame()
    
    data = []
    for item in gnfinder_json["names"]:
        best_result = item.get("verification", {}).get("bestResult", {})
        data.append({
            "Verbatim": item.get("verbatim", ""),
            "Name": item.get("name", ""),
            "Start": item.get("start", 0),
            "End": item.get("end", 0),
            "MatchType": best_result.get("matchType", ""),
            "MatchedName": best_result.get("matchedName", ""),
            "MatchedCanonical": best_result.get("matchedCanonicalFull", ""),
            "ClassificationPath": best_result.get("classificationRanks", "")
        })
    return pd.DataFrame(data)

def filter_initial_species(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies quality filters to species name detection results.
    
    This function implements a multi-step filtering process to improve
    the accuracy of species identification by:
    1. Retaining only exact taxonomic matches
    2. Validating binomial/trinomial nomenclature format
    3. Resolving taxonomic nesting (removing species when subspecies present)
    4. Eliminating duplicate detections
    
    Scientific Rationale:
    - Reduces false positives from fuzzy matching algorithms
    - Ensures compliance with binomial nomenclature standards
    - Prevents double-counting of taxonomic entities at different ranks
    
    Args:
        df: DataFrame from parse_gnfinder_results()
        
    Returns:
        Filtered DataFrame with high-confidence species identifications
        
    Algorithm Details:
    - Uses regex validation for proper species name format
    - Implements lexicographic sorting to detect nested names
    - Applies word-boundary matching to avoid partial matches
    """
    if df.empty:
        return df
    
    # Step 1: Basic filtering for valid, exact, binomial/trinomial matches
    df_filtered = df[df["MatchType"] == "Exact"].copy()
    binomial_regex = r"^\s*([A-Z][a-z]+)\s+([a-z]+)(\s+[a-z]+)?\s*$"
    df_filtered['MatchedCanonical'] = df_filtered['MatchedCanonical'].astype(str)
    df_filtered = df_filtered[df_filtered["MatchedCanonical"].str.match(binomial_regex, na=False)]

    if df_filtered.empty:
        return df_filtered

    # Step 2: Get a unique, sorted list of all canonical names found.
    # Sorting is crucial as it places species names directly before their subspecies.
    canonical_names = sorted(df_filtered["MatchedCanonical"].unique())
    
    # Step 3: Identify names that are less-specific versions of others.
    names_to_remove = set()
    for i in range(len(canonical_names) - 1):
        current_name = canonical_names[i]
        next_name = canonical_names[i+1]
        
        # If the current name is a prefix of the next name (e.g., "A b" is a prefix of "A b c"),
        # then the current name is the less-specific one and should be removed.
        # We add a space to ensure we match whole words (e.g., "Genus species" not just "Genus").
        if next_name.startswith(current_name + ' '):
            names_to_remove.add(current_name)
            
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