import json
from typing import Dict, List, Any, Optional, Tuple
import tempfile
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import ValidationError, TypeAdapter

from .models import SimplifiedVerificationResponseList
from .prompter import get_default_verification_prompt

# Adapter for robust parsing of the LLM's verification output
verification_response_list_adapter = TypeAdapter(SimplifiedVerificationResponseList)
class Verifier:
    def __init__(self, project_config: Dict[str, Any], llm_config: Dict[str, Any]):
        self.project_config = project_config
        self.llm_config = llm_config
        
        # This schema is needed for the LLM to understand what fields to verify
        self.data_fields_schema = self._generate_verification_data_fields_schema(
            project_config.get("data_fields", [])
        )

    def _generate_verification_data_fields_schema(self, data_fields: List[Dict[str, Any]]) -> str:
        """
        Generates a string schema for the LLM prompt, specific to verification,
        telling it what fields to look for in the document.
        """
        schema_parts = ["The LLM should find values for the following data fields:"]
        for field in data_fields:
            field_name = field.get('name')
            field_desc = field.get('description')
            validation_vals = field.get('validation_values')

            part = f"- '{field_name}': {field_desc}"
            if validation_vals:
                # Always add "NF" as a valid option for verification
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
        
        # --- START OF REWRITE: Logic is now much cleaner ---
        
        if not species_results_chunk: return [], 0, 0
        if not uploaded_gemini_pdf_file_object:
            # Handle file error
            ...

        try:
            client = genai.Client(api_key=self.llm_config["api_key"])
            
            # Prepare species data for the simplified prompt
            species_data_for_llm_prompt = []
            for item in species_results_chunk:
                species_name = item.get('species', 'Unknown')
                data_dict = item.get('data', {})
                species_data_for_llm_prompt.append(f"Species: {species_name}, Expected Data: {json.dumps(data_dict)}")
            species_list_str_for_prompt = "\n".join(species_data_for_llm_prompt)

            full_prompt_text = get_default_verification_prompt(
                species_data_list_for_llm=species_list_str_for_prompt,
                data_fields_schema=self.data_fields_schema
            )
            
            content = [uploaded_gemini_pdf_file_object, full_prompt_text]
            config = {"response_mime_type": "application/json", "temperature": 0.0}

            try:
                response = client.models.generate_content(
                    model=llm_model_name, contents=content, config=config
                )
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
                response_text = response.text
                
                # Parse the simplified response from the LLM
                llm_verified_items = verification_response_list_adapter.validate_json(response_text).root
                
                # Now, perform the comparison and flattening logic here in Python
                processed_chunk_results = []
                for llm_item in llm_verified_items:
                    flat_result = {"species": llm_item.species}
                    all_fields_match = True
                    
                    for field_name, expected_value in llm_item.expected_data.items():
                        found_value = llm_item.found_data.get(field_name, "NF") # Default to NF
                        
                        # The reliable comparison logic
                        is_match = (str(found_value).lower() == str(expected_value).lower())
                        
                        if is_match:
                            status = "Match"
                        elif str(found_value).lower() == "nf":
                            status = "NotFound"
                        else:
                            status = "Mismatch"
                        
                        if not is_match:
                            all_fields_match = False
                        
                        flat_result[f"{field_name}_expected"] = expected_value
                        flat_result[f"{field_name}_found"] = found_value
                        flat_result[f"{field_name}_verified"] = is_match
                        flat_result[f"{field_name}_status"] = status
                    
                    flat_result['overall_match'] = all_fields_match
                    flat_result['notes'] = llm_item.notes or ""
                    processed_chunk_results.append(flat_result)

                return processed_chunk_results, input_tokens, output_tokens

            except (ValidationError, json.JSONDecodeError) as e:
                print(f"LLM Response Validation Error for verification chunk: {e}\nRaw: {response_text}")
                for item in species_results_chunk:
                    processed_chunk_results.append(self._format_error_result(item, "Validation Error", f"Malformed LLM response: {e}"))

        except Exception as e:
            print(f"Error during Gemini verification API call: {e}")
            for item in species_results_chunk:
                processed_chunk_results.append(self._format_error_result(item, "API Error", f"API call failed: {type(e).__name__} - {e}"))
            return processed_chunk_results, 0, 0

    def _format_error_result(self, original_item: Dict, error_type: str, message: str) -> Dict:
        """Helper to format results when an error occurs for a species."""
        species_name = original_item.get('species', 'N/A')
        original_data = original_item.get('data', {})
        
        flat_result = {"species": species_name}
        for field_name, expected_value in original_data.items():
            flat_result[f"{field_name}_expected"] = expected_value
            flat_result[f"{field_name}_found"] = "Error"
            flat_result[f"{field_name}_verified"] = False
            flat_result[f"{field_name}_status"] = error_type
        flat_result['overall_match'] = False
        flat_result['notes'] = message
        return flat_result