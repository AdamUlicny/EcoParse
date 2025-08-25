"""
Automated Verification and Quality Control Module

This module provides automated verification capabilities for species data extraction
results using large language models. It implements a two-stage verification process
where LLMs re-examine source documents to validate previously extracted data,
enabling systematic quality control and accuracy assessment.

Scientific Purpose:
- Automated quality control for large-scale extraction workflows
- Accuracy assessment and error detection in extraction results
- Ground truth dataset generation for method validation
- Systematic identification of extraction biases and errors

Verification Strategy:
- Independent re-extraction minimizes confirmation bias
- Separation of extraction and comparison logic reduces LLM interpretation errors
- Batch processing enables efficient verification of large datasets
- Standardized error handling ensures robust operation

Quality Assurance Applications:
- Validation of automated extraction accuracy
- Identification of systematic extraction errors
- Performance comparison across different extraction methods
- Quality control for scientific publication datasets
"""

import json
from typing import Dict, List, Any, Optional, Tuple
import tempfile
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import ValidationError, TypeAdapter

from .models import SimplifiedVerificationResponseList
from .prompter import get_default_verification_prompt

# Pydantic adapter for parsing LLM verification responses
verification_response_list_adapter = TypeAdapter(SimplifiedVerificationResponseList)
class Verifier:
    """
    Automated verification engine for species extraction quality control.
    
    This class orchestrates the verification workflow, where an LLM
    independently re-examines source documents to validate previously
    extracted species data. The verification process separates data
    extraction from comparison logic to minimize bias and improve accuracy.
    
    Workflow Components:
    1. Schema Generation: Creates field specifications for LLM guidance
    2. Batch Processing: Groups species for efficient API utilization
    3. Independent Extraction: LLM re-extracts data without comparison bias
    4. Systematic Comparison: Python logic compares expected vs found values
    5. Result Standardization: Formats verification outcomes consistently
    
    Scientific Considerations:
    - Reduces confirmation bias through independent re-extraction
    - Maintains systematic comparison standards across all verifications
    - Provides detailed error tracking and diagnostic information
    - Supports iterative improvement of extraction methodologies
    """
    def __init__(self, project_config: Dict[str, Any], llm_config: Dict[str, Any]):
        """
        Initialize verifier with project and LLM configurations.
        
        Args:
            project_config: Project-specific settings including data field definitions
            llm_config: LLM provider settings and API credentials
        """
        self.project_config = project_config
        self.llm_config = llm_config
        
        # Generate schema for LLM verification guidance
        self.data_fields_schema = self._generate_verification_data_fields_schema(
            project_config.get("data_fields", [])
        )

    def _generate_verification_data_fields_schema(self, data_fields: List[Dict[str, Any]]) -> str:
        """
        Generates field schema specification for verification prompts.
        
        Creates a structured description of data fields that guides the LLM
        during verification re-extraction. This ensures consistent field
        identification and value extraction across different verification runs.
        
        Args:
            data_fields: List of field definitions from project configuration
            
        Returns:
            Formatted schema string for prompt integration
            
        Schema Features:
        - Clear field name identification for exact matching
        - Descriptive context for field interpretation
        - Validation value constraints when applicable
        - Automatic "NF" inclusion for missing data handling
        
        Quality Control Benefits:
        - Standardizes verification field extraction
        - Reduces variability in LLM interpretation
        - Enables systematic comparison of verification results
        - Supports reproducible verification workflows
        """
        schema_parts = ["The LLM should find values for the following data fields:"]
        for field in data_fields:
            field_name = field.get('name')
            field_desc = field.get('description')
            validation_vals = field.get('validation_values')

            part = f"- '{field_name}': {field_desc}"
            if validation_vals:
                # Ensure "NF" is available for missing data scenarios
                if "NF" not in validation_vals:
                    validation_vals.append("NF")
                part += f" (Possible values: {validation_vals})"
            schema_parts.append(part)
        return "\n".join(schema_parts)

    def verify_species_batch_gemini(
        self,
        species_results_chunk: List[Dict[str, Any]],
        uploaded_gemini_pdf_file_object: types.File,
        llm_model_name: str,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Performs batch verification of species extraction results using Gemini models.
        
        This method implements the core verification workflow where an LLM
        independently re-examines source documents to validate previously
        extracted species data. The process separates extraction from comparison
        to minimize bias and improve verification accuracy.
        
        Args:
            species_results_chunk: List of species extraction results to verify
            uploaded_gemini_pdf_file_object: Gemini file object for source document
            llm_model_name: Name of Gemini model for verification
            
        Returns:
            Tuple of (verification_results, input_tokens, output_tokens)
            
        Verification Process:
        
        1. INPUT PREPARATION:
           - Formats species and expected data for LLM context
           - Generates structured verification prompt
           - Prepares multimodal content (PDF + text prompt)
        
        2. INDEPENDENT RE-EXTRACTION:
           - LLM examines document without comparison bias
           - Extracts current values for specified data fields
           - Returns structured found_data without verification judgment
        
        3. SYSTEMATIC COMPARISON:
           - Python logic compares expected vs found values
           - Implements consistent comparison standards
           - Generates match/mismatch/not-found classifications
           - Calculates overall verification status per species
        
        4. RESULT STANDARDIZATION:
           - Flattens results into consistent output format
           - Provides field-level and overall verification status
           - Includes diagnostic information for error analysis
        
        Error Handling:
        - Graceful degradation for API failures
        - Standardized error result formatting
        - Detailed error logging for troubleshooting
        - Token counting preservation across error paths
        
        Scientific Benefits:
        - Reduces confirmation bias through independent extraction
        - Enables systematic quality control at scale
        - Provides detailed accuracy metrics for method assessment
        - Supports iterative improvement of extraction workflows
        """
        
        # Handle empty input gracefully
        if not species_results_chunk: return [], 0, 0
        if not uploaded_gemini_pdf_file_object:
            # Return error results for all species if no document available
            processed_chunk_results = []
            for item in species_results_chunk:
                processed_chunk_results.append(
                    self._format_error_result(item, "Document Error", "No PDF document available for verification")
                )
            return processed_chunk_results, 0, 0

        try:
            # Initialize Gemini client
            client = genai.Client(api_key=self.llm_config["api_key"])
            
            # --- VERIFICATION PROMPT PREPARATION ---
            # Format species data for LLM context without introducing bias
            species_data_for_llm_prompt = []
            for item in species_results_chunk:
                species_name = item.get('species', 'Unknown')
                data_dict = item.get('data', {})
                species_data_for_llm_prompt.append(f"Species: {species_name}, Expected Data: {json.dumps(data_dict)}")
            species_list_str_for_prompt = "\n".join(species_data_for_llm_prompt)

            # Generate comprehensive verification prompt
            full_prompt_text = get_default_verification_prompt(
                species_data_list_for_llm=species_list_str_for_prompt,
                data_fields_schema=self.data_fields_schema
            )
            
            # Prepare multimodal content for Gemini
            content = [uploaded_gemini_pdf_file_object, full_prompt_text]
            config = {"response_mime_type": "application/json", "temperature": 0.0}  # Deterministic for consistency

            try:
                # --- LLM VERIFICATION EXECUTION ---
                response = client.models.generate_content(
                    model=llm_model_name, contents=content, config=config
                )
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
                response_text = response.text
                
                # Parse LLM verification response
                llm_verified_items = verification_response_list_adapter.validate_json(response_text).root
                
                # --- SYSTEMATIC COMPARISON AND RESULT PROCESSING ---
                # Perform comparison logic in Python for consistency and transparency
                processed_chunk_results = []
                for llm_item in llm_verified_items:
                    flat_result = {"species": llm_item.species}
                    all_fields_match = True
                    
                    # Field-by-field comparison and status determination
                    for field_name, expected_value in llm_item.expected_data.items():
                        found_value = llm_item.found_data.get(field_name, "NF")  # Default to NF if missing
                        
                        # Robust comparison logic (case-insensitive string comparison)
                        is_match = (str(found_value).lower() == str(expected_value).lower())
                        
                        # Determine verification status
                        if is_match:
                            status = "Match"
                        elif str(found_value).lower() == "nf":
                            status = "NotFound"
                        else:
                            status = "Mismatch"
                        
                        # Track overall verification success
                        if not is_match:
                            all_fields_match = False
                        
                        # Store field-level verification results
                        flat_result[f"{field_name}_expected"] = expected_value
                        flat_result[f"{field_name}_found"] = found_value
                        flat_result[f"{field_name}_verified"] = is_match
                        flat_result[f"{field_name}_status"] = status
                    
                    # Store overall verification outcome
                    flat_result['overall_match'] = all_fields_match
                    flat_result['notes'] = llm_item.notes or ""
                    processed_chunk_results.append(flat_result)

                return processed_chunk_results, input_tokens, output_tokens

            except (ValidationError, json.JSONDecodeError) as e:
                # Handle LLM response parsing errors
                print(f"LLM Response Validation Error for verification chunk: {e}\nRaw: {response_text}")
                processed_chunk_results = []
                for item in species_results_chunk:
                    processed_chunk_results.append(
                        self._format_error_result(item, "Validation Error", f"Malformed LLM response: {e}")
                    )
                return processed_chunk_results, 0, 0

        except Exception as e:
            # Handle API and other system errors
            print(f"Error during Gemini verification API call: {e}")
            processed_chunk_results = []
            for item in species_results_chunk:
                processed_chunk_results.append(
                    self._format_error_result(item, "API Error", f"API call failed: {type(e).__name__} - {e}")
                )
            return processed_chunk_results, 0, 0

    def _format_error_result(self, original_item: Dict, error_type: str, message: str) -> Dict:
        """
        Formats standardized error results when verification fails.
        
        Creates consistent error result structure that maintains compatibility
        with successful verification results while providing diagnostic information
        about verification failures.
        
        Args:
            original_item: Original species extraction result
            error_type: Category of error encountered
            message: Detailed error description
            
        Returns:
            Standardized error result dictionary
            
        Error Result Structure:
        - Maintains same field structure as successful verifications
        - Sets all verification statuses to False
        - Provides error type and message for troubleshooting
        - Enables systematic error analysis across verification runs
        """
        species_name = original_item.get('species', 'N/A')
        original_data = original_item.get('data', {})
        
        flat_result = {"species": species_name}
        # Create error entries for all expected data fields
        for field_name, expected_value in original_data.items():
            flat_result[f"{field_name}_expected"] = expected_value
            flat_result[f"{field_name}_found"] = "Error"
            flat_result[f"{field_name}_verified"] = False
            flat_result[f"{field_name}_status"] = error_type
        flat_result['overall_match'] = False
        flat_result['notes'] = message
        return flat_result