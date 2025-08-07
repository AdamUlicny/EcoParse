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

# --- GNfinder Functions ---

def send_text_to_gnfinder(text: str, gnfinder_url: str) -> Optional[Dict]:
    """Sends text to a GNfinder API instance."""
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
    """Parses raw GNfinder JSON into a DataFrame."""
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
    Applies initial filtering to GNfinder results and removes less-specific
    taxonomic names that are prefixes of more-specific names (e.g., species vs. subspecies).
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

    # --- START OF NEW, ROBUST DE-NESTING LOGIC ---
    
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

    # --- END OF NEW LOGIC ---

    # Step 5: Final de-duplication on the original 'Name' to ensure one result per verbatim find.
    return final_df.drop_duplicates(subset=["Name"], keep="first").reset_index(drop=True)

# --- GBIF Taxonomy Functions ---

@st.cache_data(ttl="1d")
def get_higher_taxonomy(species_name: str) -> Optional[Dict]:
    # ... (this function remains the same)
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
    # ... (this function remains the same, with the previous fix)
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