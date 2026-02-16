import re
from typing import Dict, List, Any

def map_offset_to_page(full_text: str, offset: int) -> int:
    """
    Determines the page number for a given character offset in the full text,
    assuming '=== PAGE X ===' markers are present.
    """
    if not full_text: return 1
    
    # Iterate backwards from the offset to find the nearest preceding page marker
    text_before_offset = full_text[:offset]
    matches = list(re.finditer(r'=== PAGE (\d+)', text_before_offset))
    
    if matches:
        try:
            return int(matches[-1].group(1))
        except (ValueError, IndexError):
            return 1
    return 1

def get_species_pages_from_gnfinder(full_text: str, gnfinder_results: Any) -> Dict[str, List[int]]:
    """
    Maps species names to a list of page numbers where they were found by GNfinder.
    """
    if not gnfinder_results:
        return {}
        
    names_list = []
    if isinstance(gnfinder_results, dict) and 'names' in gnfinder_results:
        names_list = gnfinder_results['names']
    elif isinstance(gnfinder_results, list):
         names_list = gnfinder_results
    elif isinstance(gnfinder_results, dict) and 'final_species_list' in gnfinder_results: # Handle loaded log structure
         names_list = gnfinder_results.get('final_species_list', [])

    if not names_list:
        return {}

    # Pre-calculate page markers for performance
    page_markers = []
    for match in re.finditer(r'=== PAGE (\d+)', full_text):
        page_markers.append((match.start(), int(match.group(1))))
    
    # Use empty list if no markers found (fallback to page 1 logic later if needed)
    if not page_markers:
        return {}

    species_pages = {}
    
    for item in names_list:
        if not isinstance(item, dict): continue
        
        name = item.get('Name') or item.get('species')
        start_offset = item.get('Start')
        
        if name and start_offset is not None:
            # Find page for this offset
            page = 1
            for marker_offset, page_num in page_markers:
                # If marker is beyond our start, the previous marker was the page start
                if marker_offset > start_offset:
                    break
                # Only update page if marker offset is <= start_offset
                if marker_offset <= start_offset:
                     page = page_num
            
            if name not in species_pages:
                species_pages[name] = []
            if page not in species_pages[name]:
                 species_pages[name].append(page)
                 
    return species_pages
