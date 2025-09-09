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
import subprocess
import csv
import io
from pathlib import Path
from typing import Dict, Optional
from pygbif import species as gbif_species
import time
import streamlit as st
import re
import os

# --- GNfinder Integration Functions ---
# GNfinder is a service for finding scientific names in text

def send_text_to_gnfinder(text: str, gnfinder_url: str, offline_mode: bool = False) -> Optional[Dict]:
    """
    Submits text to GNfinder service for species name detection.
    
    GNfinder uses machine learning and taxonomic databases to identify
    scientific names in unstructured text, providing verification
    against authoritative taxonomic sources.
    
    Args:
        text: Input text document for species name detection
        gnfinder_url: URL of the GNfinder service endpoint
        offline_mode: If True, skips Apache Tika service (equivalent to -U flag)
        
    Returns:
        JSON response containing detected names and verification data,
        or None if the request fails
        
    Scientific Context:
    - Enables automated biodiversity data extraction from literature
    - Provides taxonomic verification through multiple databases
    - Supports both exact and fuzzy name matching
    - Offline mode skips Tika service, useful when Tika is down or causing errors
    
    Text Preprocessing:
    - Removes extraction method artifacts (column headers, page markers)
    - Preserves original text structure and formatting
    - Maintains species names in context for better detection
    """
    # Clean text of extraction artifacts that might confuse GnFinder
    cleaned_text = _clean_text_for_gnfinder(text)
    
    # Route to CLI if offline mode is enabled (workaround for broken API)
    if offline_mode:
        print("Using GNfinder CLI (offline mode)")
        return _send_text_to_gnfinder_cli(cleaned_text)
    
    print("Using GNfinder API (online mode)")
    # Otherwise use API (original method)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp_file:
        tmp_file.write(cleaned_text)
        tmp_file_path = tmp_file.name

    try:
        with open(tmp_file_path, "rb") as f:
            files = {"file": (Path(tmp_file_path).name, f, "text/plain")}
            
            # Configure parameters based on offline mode
            # offline_mode=True: equivalent to gnfinder -U flag (--utf8-input)
            # This skips Apache Tika service and treats input as plain UTF8
            if offline_mode:
                params = {
                    "WithPlainInput": "true",    # -U, --utf8-input flag - skip Tika service
                    "WithVerification": "true",  # Keep verification
                    "WithUniqueNames": "true"
                }
            else:
                params = {
                    "WithVerification": "true",
                    "WithUniqueNames": "true"
                    # Uses Tika service by default
                }
            
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


def _send_text_to_gnfinder_cli(text: str) -> Optional[Dict]:
    """
    Sends text to GNfinder via command line interface (fallback when API is broken).
    
    This function bypasses the GNfinder web API and calls the command-line version directly.
    Useful when the API service is down but the core GNfinder engine works.
    
    Args:
        text: Cleaned text for species name detection
        
    Returns:
        JSON response in the same format as the API, or None if command fails
    """
    import subprocess
    import csv
    import io
    
    # Create temporary file for CLI processing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp_file:
        tmp_file.write(text)
        tmp_file_path = tmp_file.name
    
    try:
        # Run gnfinder CLI with -U flag (skip Tika) and -f csv for easier parsing
        result = subprocess.run(
            ['gnfinder', tmp_file_path, '-U', '-f', 'csv'],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            print(f"GNfinder CLI error: {result.stderr}")
            return None
            
        # Parse CSV output to match API format
        csv_output = result.stdout.strip()
        if not csv_output:
            print("No species found by GNfinder CLI")
            return None
        
        # Convert CSV to JSON format matching the API response
        return _convert_cli_output_to_json(csv_output)
        
    except subprocess.TimeoutExpired:
        print("GNfinder CLI timeout - try with shorter text")
        return None
    except Exception as e:
        print(f"CLI execution error: {e}")
        return None
    finally:
        Path(tmp_file_path).unlink()


def _convert_cli_output_to_json(csv_output: str) -> Optional[Dict]:
    """
    Converts GNfinder CLI CSV output to JSON format matching the API response.
    
    Args:
        csv_output: Raw CSV output from gnfinder CLI
        
    Returns:
        Dictionary in the same format as the API JSON response
    """
    try:
        csv_reader = csv.DictReader(io.StringIO(csv_output))
        names = []
        
        for row in csv_reader:
            # Map CLI CSV columns to API JSON format (use lowercase keys to match API)
            name_entry = {
                "verbatim": row.get("Verbatim", ""),
                "name": row.get("Name", ""),
                "start": int(row.get("Start", 0)),
                "end": int(row.get("End", 0)),
                "oddsLog10": float(row.get("OddsLog10", 0.0)) if row.get("OddsLog10") else None,
                "cardinality": int(row.get("Cardinality", 0)),
                "annotNomenType": row.get("AnnotNomenType", ""),
                "wordsBefore": row.get("WordsBefore", ""),
                "wordsAfter": row.get("WordsAfter", "")
                # Note: CLI doesn't provide verification data, so parse_gnfinder_results
                # will treat these as "Unverified" matches, which is correct
            }
            names.append(name_entry)
        
        # Return in API-compatible format
        return {
            "names": names,
            "total": len(names),
            "source": "cli"  # Mark as CLI source for debugging
        }
        
    except Exception as e:
        print(f"Error converting CLI output: {e}")
        return None

def _clean_text_for_gnfinder(text: str) -> str:
    """
    Clean extracted text to improve GNfinder species detection accuracy.
    
    Removes common extraction artifacts and formatting issues that
    can interfere with species name recognition while preserving
    the scientific content and context.
    """
    if not text:
        return ""
    
    # Remove common extraction artifacts
    text = re.sub(r'^\s*(?:Page \d+|CONTENT|TABLES?|FIGURES?|APPENDIX|REFERENCES)\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^\s*(?:Table|Figure|Fig\.)\s+\d+[^\n]*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'\b(?:PDF|DOI|URL|HTTP|WWW)\b[^\s]*', '', text, flags=re.IGNORECASE)
    
    # Clean up excessive whitespace and special characters
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single space
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Multiple newlines to double newline
    
    # Remove problematic characters that might cause encoding issues
    text = re.sub(r'[^\w\s\.\,\;\:\!\?\(\)\[\]\-\'\"]', ' ', text)
    
    # Clean up parentheses and brackets content that might confuse parsing
    text = re.sub(r'\([^)]{50,}\)', '', text)  # Remove very long parenthetical content
    text = re.sub(r'\[[^\]]{50,}\]', '', text)  # Remove very long bracketed content
    
    return text.strip()

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
def get_higher_taxonomy(species_name: str, include_fuzzy: bool = True, include_higherrank: bool = False) -> Optional[Dict]:
    """
    Retrieves taxonomic hierarchy from GBIF for a given species.
    
    Queries the Global Biodiversity Information Facility (GBIF) taxonomic
    backbone to obtain higher-level taxonomic classification. Results are
    cached for 24 hours to minimize API calls and improve performance.
    
    Args:
        species_name: Scientific name for taxonomic lookup
        include_fuzzy: Whether to accept fuzzy/approximate matches
        include_higherrank: Whether to accept higher rank matches (genus/family level)
        
    Returns:
        Dictionary containing taxonomic ranks and match information,
        or None if species not found or doesn't meet criteria
        
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
        
        if not response or response.get('matchType') == 'NONE':
            return None
            
        match_type = response.get('matchType')
        rank = response.get('rank')
        status = response.get('status')
        
        # Determine if we should accept this match based on user preferences
        accept_match = False
        
        if match_type == 'EXACT':
            accept_match = True
        elif match_type == 'FUZZY' and include_fuzzy:
            accept_match = True
        elif match_type == 'HIGHERRANK' and include_higherrank:
            accept_match = True
            
        # Additional checks for accepted taxonomic status
        if accept_match and status not in ['ACCEPTED', 'SYNONYM']:
            accept_match = False
            
        if accept_match:
            return {
                'kingdom': response.get('kingdom'),
                'phylum': response.get('phylum'),
                'class': response.get('class'),
                'order': response.get('order'),
                'family': response.get('family'),
                'genus': response.get('genus'),
                'species': response.get('species'),
                'match_type': match_type,
                'rank': rank,
                'status': status,
                'confidence': response.get('confidence', 0)
            }
        return None
    except Exception as e:
        print(f"Error querying GBIF for {species_name}: {e}")
        return None

def filter_by_taxonomy(df: pd.DataFrame, rank: str, name: str, include_fuzzy: bool = True, include_higherrank: bool = False, include_unverified: bool = False) -> pd.DataFrame:
    """
    Filters species list by taxonomic group membership with configurable strictness.
    
    Applies taxonomic filtering to focus extraction on specific biological
    groups (e.g., only birds, only flowering plants). This is essential
    for targeted biodiversity studies and reduces processing time for
    large documents.
    
    Args:
        df: DataFrame of detected species names
        rank: Taxonomic rank for filtering (kingdom, phylum, class, order, family)
        name: Name of the taxonomic group to retain (use 'any' for no taxonomic constraint)
        include_fuzzy: Include species with fuzzy GBIF matches
        include_higherrank: Include species with higher rank matches
        include_unverified: Include species with no GBIF verification
        
    Returns:
        Filtered DataFrame containing species meeting the specified criteria
        
    Performance Considerations:
    - Includes progress bar for long-running operations
    - Implements rate limiting to respect GBIF API guidelines
    - Caches taxonomic lookups to minimize redundant queries
    
    Scientific Applications:
    - Taxonomic group-specific conservation assessments
    - Focused studies on particular lineages
    - Quality control by excluding unlikely taxonomic matches
    - General quality filtering using GBIF verification criteria
    """
    if df.empty:
        return df

    # Check if this is general quality filtering (no taxonomic constraint)
    is_quality_filter_only = (not rank or not name or name.lower() == 'any')

    filtered_indices = []
    total = len(df)
    filter_type = "quality filter" if is_quality_filter_only else f"taxonomic filter ({rank}: {name})"
    progress_bar = st.progress(0, text=f"Applying {filter_type}... (0/{total})")

    for i, row in df.iterrows():
        species_name = row["Name"]
        taxonomy = get_higher_taxonomy(species_name, include_fuzzy=include_fuzzy, include_higherrank=include_higherrank)
        
        # Check if we should include this species
        include_species = False
        
        if taxonomy:
            # Species has GBIF verification
            if is_quality_filter_only:
                # No taxonomic constraint - just apply quality criteria
                include_species = True
            else:
                # Check taxonomic match
                actual_rank_value = taxonomy.get(rank)
                if isinstance(actual_rank_value, str) and actual_rank_value.lower() == name.lower():
                    include_species = True
        elif include_unverified:
            # Species has no GBIF verification but user wants to include unverified
            include_species = True
            
        if include_species:
            filtered_indices.append(i)
        
        time.sleep(0.05)
        progress_bar.progress((i + 1) / total, text=f"Applying {filter_type}... ({i+1}/{total})")

    progress_bar.empty()
    return df.loc[filtered_indices].reset_index(drop=True)


def filter_by_gbif_verification(df: pd.DataFrame, include_fuzzy: bool = True, include_higherrank: bool = False, min_confidence: int = 80) -> pd.DataFrame:
    """
    Filters species list to only include GBIF-verified species names with configurable criteria.
    
    NOTE: This function is currently unused in the main workflow as the taxonomic filter
    provides the same functionality with more flexibility. Kept for potential future use
    or specialized filtering scenarios.
    
    This function provides flexible quality control by removing species names
    that cannot be verified against the GBIF taxonomic backbone, while allowing
    users to configure the strictness of verification.
    
    Args:
        df: DataFrame of detected species names
        include_fuzzy: Include species with fuzzy/approximate GBIF matches
        include_higherrank: Include species with higher rank matches (genus/family level)
        min_confidence: Minimum confidence score required (0-100)
        
    Returns:
        Filtered DataFrame containing species meeting verification criteria
        
    Verification Options:
    - EXACT matches: Always included (highest confidence)
    - FUZZY matches: Included if include_fuzzy=True (good for variant spellings)
    - HIGHERRANK matches: Included if include_higherrank=True (less specific)
    - Confidence threshold: Additional quality control based on GBIF confidence
    
    Scientific Benefits:
    - Configurable balance between precision and recall
    - Maintains legitimate species while removing obvious false positives
    - Allows for different strictness levels based on study requirements
    
    Use Cases:
    - Conservative filtering: Only exact matches, high confidence
    - Moderate filtering: Include fuzzy matches for variant spellings
    - Permissive filtering: Include higher rank matches for broader coverage
    """
    if df.empty:
        return df

    filtered_indices = []
    verification_stats = {'exact': 0, 'fuzzy': 0, 'higherrank': 0, 'rejected': 0}
    total = len(df)
    progress_bar = st.progress(0, text=f"Verifying species with GBIF... (0/{total})")

    for i, row in df.iterrows():
        species_name = row["Name"]
        taxonomy = get_higher_taxonomy(species_name, include_fuzzy=include_fuzzy, include_higherrank=include_higherrank)
        
        if taxonomy and taxonomy.get('confidence', 0) >= min_confidence:
            filtered_indices.append(i)
            match_type = taxonomy.get('match_type', 'unknown')
            verification_stats[match_type.lower()] = verification_stats.get(match_type.lower(), 0) + 1
        else:
            verification_stats['rejected'] += 1
        
        time.sleep(0.05)
        progress_bar.progress((i + 1) / total, text=f"Verifying species with GBIF... ({i+1}/{total})")

    progress_bar.empty()
    
    # Display verification statistics
    if st.session_state.get('show_gbif_stats', True):
        st.info(f"📊 GBIF Verification Results: "
                f"Exact: {verification_stats['exact']}, "
                f"Fuzzy: {verification_stats['fuzzy']}, "
                f"Higher Rank: {verification_stats['higherrank']}, "
                f"Rejected: {verification_stats['rejected']}")
    
    return df.loc[filtered_indices].reset_index(drop=True)


def get_gbif_match_type_explanation() -> Dict[str, str]:
    """
    Returns explanations for different GBIF match types to help users understand filtering options.
    
    NOTE: This function is kept for potential future use or educational purposes
    in case GBIF verification filtering is re-implemented.
    
    Returns:
        Dictionary mapping match types to user-friendly explanations
    """
    return {
        'EXACT': 'Perfect match to a species name in GBIF (highest confidence)',
        'FUZZY': 'Approximate match due to spelling variants or minor differences',
        'HIGHERRANK': 'Match to a genus or family name rather than species level',
        'NONE': 'No match found in GBIF database'
    }


def analyze_species_gbif_quality(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyzes the GBIF match quality of species in a DataFrame for diagnostic purposes.
    
    NOTE: This function is kept for potential future use in diagnostic workflows
    or detailed quality analysis features.
    
    Args:
        df: DataFrame of species names to analyze
        
    Returns:
        DataFrame with GBIF verification details for each species
    """
    if df.empty:
        return pd.DataFrame()
    
    analysis_results = []
    total = len(df)
    
    for i, row in df.iterrows():
        species_name = row["Name"]
        taxonomy = get_higher_taxonomy(species_name, include_fuzzy=True, include_higherrank=True)
        
        if taxonomy:
            result = {
                'Species': species_name,
                'GBIF_Match_Type': taxonomy.get('match_type', 'Unknown'),
                'GBIF_Rank': taxonomy.get('rank', 'Unknown'),
                'GBIF_Status': taxonomy.get('status', 'Unknown'),
                'GBIF_Confidence': taxonomy.get('confidence', 0),
                'Kingdom': taxonomy.get('kingdom', ''),
                'Class': taxonomy.get('class', ''),
                'Order': taxonomy.get('order', ''),
                'Family': taxonomy.get('family', ''),
                'Verified': 'Yes'
            }
        else:
            result = {
                'Species': species_name,
                'GBIF_Match_Type': 'NONE',
                'GBIF_Rank': '',
                'GBIF_Status': '',
                'GBIF_Confidence': 0,
                'Kingdom': '',
                'Class': '',
                'Order': '',
                'Family': '',
                'Verified': 'No'
            }
        
        analysis_results.append(result)
    
    return pd.DataFrame(analysis_results)

def test_gnfinder_connection(gnfinder_url: str = "http://localhost:4040/api/v1/find", offline_mode: bool = False) -> bool:
    """
    Test GNfinder connection with a simple request.
    
    Args:
        gnfinder_url: URL of the GNfinder service
        offline_mode: If True, tests without remote verification
    
    Returns True if successful, False otherwise.
    Prints detailed debug information.
    """
    test_text = "Homo sapiens and Canis lupus are common species."
    
    print(f"Testing GNfinder connection to: {gnfinder_url}")
    print(f"Offline mode: {offline_mode}")
    
    try:
        # Test ping first
        ping_url = gnfinder_url.replace('/api/v1/find', '/api/v1/ping')
        ping_response = requests.get(ping_url, timeout=5)
        print(f"Ping response: {ping_response.status_code}")
        
        # Test actual find request with offline mode support
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp_file:
            tmp_file.write(test_text)
            tmp_file_path = tmp_file.name
        
        with open(tmp_file_path, 'rb') as f:
            files = {'file': ('test.txt', f, 'text/plain')}
            
            # Configure parameters for offline mode (-U flag equivalent)
            if offline_mode:
                params = {
                    'WithPlainInput': 'true',    # -U, --utf8-input flag - skip Tika service
                    'WithVerification': 'true',  # Keep verification
                    'WithUniqueNames': 'true'
                }
            else:
                params = {
                    'WithVerification': 'true',
                    'WithUniqueNames': 'true'
                    # Uses Tika service by default
                }
            
            response = requests.post(gnfinder_url, files=files, params=params, timeout=30)
            print(f"Find response status: {response.status_code}")
            print(f"Find response content length: {len(response.text)}")
            
            if response.status_code != 200:
                print(f"Error response: {response.text}")
                return False
            
            result = response.json()
            print(f"Success! Found {len(result.get('names', []))} names")
            return True
            
    except Exception as e:
        print(f"Test failed: {type(e).__name__}: {str(e)}")
        return False
    finally:
        try:
            os.unlink(tmp_file_path)
        except:
            pass