"""
Large Language Model Data Extraction Engine

This module orchestrates the extraction of species-specific data from documents
using various large language model (LLM) providers. It supports both text-based
and image-based extraction workflows with concurrent processing for efficiency.

Scientific Purpose:
- Automated extraction of ecological data from biodiversity literature
- Scalable processing of large document corpora
- Multi-modal analysis combining text and visual information
- Standardized data output format for downstream analysis

Supported LLM Providers:
- Google Gemini: Cloud-based models with strong multimodal capabilities
- Ollama: Local models for privacy-sensitive or offline processing

Key Features:
- Concurrent processing for improved throughput
- Token usage tracking for cost monitoring
- Robust error handling and fallback mechanisms
- Flexible prompt engineering framework
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple
import ollama
from google import genai
from google.genai import types
from pydantic import ValidationError, TypeAdapter
from .models import ExtractionResultList, SpeciesData
from .prompter import (
    generate_data_fields_schema, 
    get_default_text_prompt, 
    get_default_image_prompt
)
from .sourcetext import get_species_context_chunks, get_species_page_images, get_species_full_page_chunks, get_species_partial_page_chunks

# Pydantic adapter for validating LLM JSON responses
extraction_list_adapter = TypeAdapter(ExtractionResultList)

class Extractor:
    """
    LLM-based data extraction engine.
    
    Manages extraction workflow from preprocessing through validation.
    Supports text-based and image-based extraction with concurrent processing.
    """
    def __init__(self, project_config: Dict[str, Any], llm_config: Dict[str, Any]):
        """Initialize with project and LLM configurations."""
        self.project_config = project_config
        self.llm_config = llm_config
        self.data_fields_schema = generate_data_fields_schema(project_config.get("data_fields", []))

    def run_extraction(
        self, species_list: List[str], source_context: Dict[str, Any], update_callback=None
    ) -> Tuple[List[Dict], float, int, int]:
        """
        Execute data extraction for a list of species using concurrent processing.
        
        This method orchestrates the complete extraction pipeline, processing
        multiple species concurrently to maximize throughput while respecting
        API rate limits and system resources. Supports pause/stop functionality
        through session state monitoring.
        
        Args:
            species_list: List of species names for data extraction
            source_context: Dictionary containing document data and extraction parameters
            update_callback: Optional function for progress reporting
            
        Returns:
            Tuple containing:
            - List of extraction results (one dict per species)
            - Total runtime in seconds
            - Total input tokens consumed
            - Total output tokens generated
            
        Concurrent Processing Strategy:
        - Uses ThreadPoolExecutor for I/O-bound LLM API calls
        - Configurable max_workers to control API load
        - Progress tracking for long-running extractions
        - Token aggregation for cost monitoring
        - Stop/pause support via session state flags
        
        Scientific Considerations:
        - Maintains extraction order independence for reproducibility
        - Handles partial failures gracefully
        - Provides detailed performance metrics for analysis
        """

        all_results = []
        total_input_tokens = 0
        total_output_tokens = 0
        max_workers = self.llm_config.get("concurrent_requests", 5)
        
        start_time = time.time()

        # Check if we have Streamlit session state for stop/pause functionality
        try:
            import streamlit as st
            has_streamlit = True
        except ImportError:
            has_streamlit = False

        # Execute concurrent extraction tasks
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self._extract_for_single_species, species, source_context)
                for species in species_list
            ]

            # Collect results as they complete
            for i, future in enumerate(as_completed(futures)):
                # Check for stop/pause flags if running in Streamlit
                if has_streamlit:
                    if hasattr(st.session_state, 'extraction_running') and not st.session_state.extraction_running:
                        # User requested stop - cancel remaining futures
                        for remaining_future in futures:
                            if not remaining_future.done():
                                remaining_future.cancel()
                        break
                
                result, in_tokens, out_tokens = future.result()
                if result:
                    all_results.append(result)
                
                # Aggregate token counts for cost tracking
                total_input_tokens += in_tokens or 0
                total_output_tokens += out_tokens or 0
                
                # Report progress to callback function if provided
                if update_callback:
                    update_callback(i + 1, len(species_list))
        
        runtime = time.time() - start_time
        return all_results, runtime, total_input_tokens, total_output_tokens

    def run_resumable_extraction(
        self, species_list: List[str], source_context: Dict[str, Any], update_callback=None,
        completed_species: List[str] = None
    ) -> Tuple[List[Dict], float, int, int]:
        """
        Execute data extraction with support for pause/resume functionality.
        
        This method provides a resumable extraction workflow that can be paused
        and resumed, making it suitable for long-running extractions where users
        may need to stop and continue later.
        
        Args:
            species_list: List of species names for data extraction
            source_context: Dictionary containing document data and extraction parameters
            update_callback: Optional function for progress reporting
            completed_species: List of species already processed (for resume functionality)
            
        Returns:
            Tuple containing:
            - List of extraction results (one dict per species)
            - Total runtime in seconds
            - Total input tokens consumed
            - Total output tokens generated
        """
        
        # Filter out already completed species
        if completed_species:
            remaining_species = [s for s in species_list if s not in completed_species]
        else:
            remaining_species = species_list.copy()
        
        all_results = []
        total_input_tokens = 0
        total_output_tokens = 0
        max_workers = self.llm_config.get("concurrent_requests", 5)
        
        start_time = time.time()

        # Check if we have Streamlit session state for stop/pause functionality
        try:
            import streamlit as st
            has_streamlit = True
        except ImportError:
            has_streamlit = False

        completed_count = len(species_list) - len(remaining_species)
        
        # Process species one batch at a time to allow for pause/resume
        batch_size = min(max_workers, len(remaining_species))
        
        for batch_start in range(0, len(remaining_species), batch_size):
            # Check for stop/pause before starting each batch
            if has_streamlit and hasattr(st.session_state, 'extraction_running'):
                if not st.session_state.extraction_running:
                    break
            
            batch_end = min(batch_start + batch_size, len(remaining_species))
            batch_species = remaining_species[batch_start:batch_end]
            
            # Process this batch concurrently
            with ThreadPoolExecutor(max_workers=len(batch_species)) as executor:
                futures = [
                    executor.submit(self._extract_for_single_species, species, source_context)
                    for species in batch_species
                ]

                # Collect results as they complete
                for i, future in enumerate(as_completed(futures)):
                    # Check for stop/pause during batch processing
                    if has_streamlit and hasattr(st.session_state, 'extraction_running'):
                        if not st.session_state.extraction_running:
                            # Cancel remaining futures in this batch
                            for remaining_future in futures:
                                if not remaining_future.done():
                                    remaining_future.cancel()
                            break
                    
                    result, in_tokens, out_tokens = future.result()
                    if result:
                        all_results.append(result)
                    
                    # Aggregate token counts for cost tracking
                    total_input_tokens += in_tokens or 0
                    total_output_tokens += out_tokens or 0
                    
                    completed_count += 1
                    
                    # Report progress to callback function if provided
                    if update_callback:
                        update_callback(completed_count, len(species_list))
        
        runtime = time.time() - start_time
        return all_results, runtime, total_input_tokens, total_output_tokens

    def _extract_for_single_species(self, species_name: str, context: Dict[str, Any]) -> Tuple[Optional[Dict], int, int]:
        """
        Extract data for a single species using specified extraction method.
        
        This method handles the species-specific extraction workflow,
        preparing appropriate context (text chunks or page images) and
        invoking the configured LLM with properly formatted prompts.
        
        Args:
            species_name: Scientific name of target species
            context: Extraction context containing document data and parameters
            
        Returns:
            Tuple of (extraction_result_dict, input_tokens, output_tokens)
            
        Extraction Methods:
        
        Text-based Extraction:
        - Retrieves contextual text passages around species mentions
        - Uses specialized text prompts optimized for narrative content
        - Effective for descriptive text and species accounts
        
        Image-based Extraction:
        - Generates page images containing species information
        - Uses vision-capable models for visual data interpretation
        - Essential for tables, figures, and structured layouts
        
        Error Handling:
        - Returns standardized "no context" results for missing data
        - Maintains consistent token counting across all code paths
        - Preserves species information even when extraction fails
        """
        extraction_method = context.get("extraction_method")
        examples_text = context.get("examples_text", "")
        
        # Standardized fallback results when context is unavailable
        no_context_result = (
            {"species": species_name, "data": {}, "notes": "No text context found."},
            0, 0
        )
        no_image_result = (
            {"species": species_name, "data": {}, "notes": "No page images found."},
            0, 0
        )

        # Route to appropriate extraction method
        if extraction_method == "Text-based":
            # Check chunking method
            chunking_method = context.get('chunking_method', 'Context Window')
            
            if chunking_method == "Full Page":
                # Use full page chunking - get complete page content where species is mentioned
                chunks = get_species_full_page_chunks(
                    context['full_text'],
                    context['species_df']
                ).get(species_name, [])
            elif chunking_method == "Partial Page (Top + Bottom)":
                # Use partial page chunking - get top and bottom of pages where species is mentioned
                chars_from_top = context.get('chars_from_top', 500)
                chars_from_bottom = context.get('chars_from_bottom', 500)
                chunks = get_species_partial_page_chunks(
                    context['full_text'],
                    context['species_df'],
                    chars_from_top,
                    chars_from_bottom
                ).get(species_name, [])
            else:
                # Use context-based chunking (original method)
                chunks = get_species_context_chunks(
                    context['full_text'],
                    context['species_df'][context['species_df']['Name'] == species_name],
                    context['context_before'],
                    context['context_after']
                ).get(species_name, [])
            
            if not chunks: return no_context_result
            
            # Generate text-based extraction prompt
            prompt = get_default_text_prompt(
                species_name, "\n---\n".join(chunks), self.data_fields_schema, examples_text
            )
            return self._call_llm(prompt, images=None)
        
        elif extraction_method == "Image-based":
            # Generate page images containing species information
            images = get_species_page_images(
                context['pdf_buffer'],
                context['species_df'][context['species_df']['Name'] == species_name]
            ).get(species_name, [])

            if not images: return no_image_result

            # Generate image-based extraction prompt
            prompt = get_default_image_prompt(species_name, self.data_fields_schema, examples_text)
            return self._call_llm(prompt, images=images)

        return None, 0, 0

    def _call_llm(self, prompt: str, images: Optional[List[bytes]] = None) -> Tuple[Optional[Dict], int, int]:
        """
        Route LLM calls to appropriate provider implementation.
        
        Provides a unified interface for different LLM providers while
        ensuring consistent return format including token usage data.
        
        Args:
            prompt: Formatted prompt string for the LLM
            images: Optional list of image data for multimodal models
            
        Returns:
            Tuple of (result_dict, input_tokens, output_tokens)
        """
        provider = self.llm_config.get("provider")
        if provider == "Google Gemini":
            return self._call_gemini(prompt, images)
        elif provider == "Ollama":
            return self._call_ollama(prompt, images)
        return None, 0, 0

    def _call_gemini(self, prompt: str, images: Optional[List[bytes]]) -> Tuple[Optional[Dict], int, int]:
        """
        Execute extraction using Google Gemini models.
        
        Handles Gemini-specific API formatting, multimodal content preparation,
        and response parsing. Extracts detailed token usage information for
        cost tracking and performance analysis.
        
        Gemini-Specific Features:
        - Native multimodal support for text + image inputs
        - JSON response mode for structured output
        - Detailed token usage metadata
        - Configurable temperature for deterministic results
        
        Args:
            prompt: Text prompt for the model
            images: Optional list of PNG image bytes
            
        Returns:
            Tuple of (parsed_result, input_tokens, output_tokens)
        """
        try:
            # Initialize Gemini client with API key
            client = genai.Client(api_key=self.llm_config["api_key"])
            
            # Prepare multimodal content (images + text)
            content = [prompt] 
            if images:
                for img_bytes in images:
                    content.insert(0, types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
            
            # Execute generation with JSON response mode
            response = client.models.generate_content(
                model=self.llm_config["model"], 
                contents=content, 
                config={"response_mime_type": "application/json", 
                        "temperature": 0.1  # Low temperature for consistent extraction
                }
            )
            
            # Extract token usage metadata
            in_tokens = response.usage_metadata.prompt_token_count
            out_tokens = response.usage_metadata.candidates_token_count
            
            # Parse and validate JSON response
            parsed_list = extraction_list_adapter.validate_json(response.text)
            result = parsed_list.root[0].model_dump() if parsed_list.root else None
            return result, in_tokens, out_tokens
        
        except Exception as e:
            print(f"Error with Gemini API: {e}")
            return None, 0, 0

    def _call_ollama(self, prompt: str, images: Optional[List[bytes]]) -> Tuple[Optional[Dict], int, int]:
        """
        Execute extraction using local Ollama models.
        
        Handles Ollama-specific API formatting and response parsing.
        Supports both text-only and multimodal models depending on
        the selected model's capabilities.
        
        Ollama-Specific Features:
        - Local model execution for privacy and control
        - Support for custom and fine-tuned models
        - JSON format enforcement for structured output
        - Token counting for performance monitoring
        
        Args:
            prompt: Text prompt for the model
            images: Optional list of image bytes for multimodal models
            
        Returns:
            Tuple of (parsed_result, input_tokens, output_tokens)
            
        Response Parsing Strategy:
        - Primary: Parse as ExtractionResultList (array format)
        - Fallback: Parse as single SpeciesData object
        - This handles variations in model output format
        """
        try:
            # Initialize Ollama client with host URL
            client = ollama.Client(host=self.llm_config["ollama_url"])

            # Prepare chat message with optional images
            messages = [{"role": "user", "content": prompt}]
            if images:
                messages[0]["images"] = images

            # Execute chat completion with JSON format
            response = client.chat(
                model=self.llm_config["model"],
                messages=messages,
                format="json",  # Force JSON output
                options={"temperature": 0.1}  # Low temperature for consistency
            )

            response_content = response['message']['content']
            # Extract token counts (Ollama-specific fields)
            in_tokens = response.get('prompt_eval_count', 0)
            out_tokens = response.get('eval_count', 0)
            
            # Attempt to parse response with fallback handling
            try:
                # Primary: Parse as list format
                parsed_list = extraction_list_adapter.validate_json(response_content)
                result = parsed_list.root[0].model_dump() if parsed_list.root else None
            except ValidationError:
                # Fallback: Parse as single object format
                single_object = SpeciesData.model_validate_json(response_content)
                result = single_object.model_dump()
            
            return result, in_tokens, out_tokens
        
        except Exception as e:
            print(f"Error with Ollama API: {e}")
            return None, 0, 0