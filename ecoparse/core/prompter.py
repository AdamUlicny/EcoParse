"""
Prompt Engineering and Template Generation Module

This module provides specialized prompt templates for large language model
interactions in species data extraction tasks. It implements systematic
prompt engineering strategies to ensure consistent, accurate, and structured
outputs from various LLM providers.

Scientific Purpose:
- Standardizes LLM interactions for biodiversity data extraction
- Implements prompt engineering best practices for scientific accuracy
- Ensures reproducible and consistent extraction results
- Supports both text-based and vision-based extraction workflows

Key Design Principles:
- Explicit output formatting requirements
- Mandatory field completion (using "NF" for missing data)
- Scientific persona establishment for domain expertise
- Clear task definition and rule specification
- Examples-based learning for context understanding
"""

from typing import List, Dict, Any

def generate_data_fields_schema(data_fields: List[Dict[str, Any]]) -> str:
    """
    Generates structured field definitions for LLM prompt templates.
    
    Converts project configuration data fields into a clear, formatted
    specification that instructs the LLM on required output structure.
    This ensures consistent data extraction across different species and
    documents.
    
    Args:
        data_fields: List of field definitions from project configuration
        
    Returns:
        Formatted string describing required output schema
        
    Schema Components:
    - Field name: Exact key to use in JSON output
    - Field description: Context and extraction guidelines
    - Validation values: Constrained vocabulary when applicable
    - "NF" handling: Automatic inclusion for missing data scenarios
    
    Design Rationale:
    - Explicit field naming prevents LLM interpretation variations
    - Validation values reduce extraction inconsistencies
    - "NF" standardization enables systematic missing data handling
    """
    schema_parts = ["The 'data' object in the JSON output should contain the following keys:"]
    for field in data_fields:
        field_name = field.get('name')
        field_desc = field.get('description')
        validation_vals = field.get('validation_values')

        part = f"- '{field_name}': {field_desc}"
        if validation_vals:
            # Ensure "NF" is always available for missing data
            if "NF" not in validation_vals:
                validation_vals.append("NF")
            part += f" The value MUST be one of {validation_vals}."
        schema_parts.append(part)
    return "\n".join(schema_parts)


def get_default_text_prompt(species_name: str, text_chunk: str, data_fields_schema: str, examples_text: str) -> str:
    """
    Generates specialized prompt for text-based species data extraction.
    
    Creates a comprehensive prompt template optimized for extracting structured
    data from textual passages. This prompt implements systematic approaches
    to ensure accuracy, consistency, and completeness in LLM responses.
    
    Args:
        species_name: Target species for data extraction
        text_chunk: Contextual text passage containing species information
        data_fields_schema: Formatted schema describing required output fields
        examples_text: Optional examples to guide extraction behavior
        
    Returns:
        Complete prompt string ready for LLM submission
        
    Prompt Engineering Strategy:
    
    1. PERSONA ESTABLISHMENT:
       - Establishes expert scientific identity for domain expertise
       - Emphasizes accuracy and precision requirements
    
    2. TASK DEFINITION:
       - Clearly specifies extraction target (species + fields)
       - Provides contextual text for analysis
       - Delimits input text for focus
    
    3. EXAMPLES INTEGRATION:
       - Incorporates provided examples for pattern learning
       - Handles cases with no examples gracefully
    
    4. OUTPUT SPECIFICATION:
       - Enforces JSON format with explicit schema
       - Mandates specific structure and field completion
       - Prevents hallucination through strict rules
    
    5. SCIENTIFIC RIGOR RULES:
       - "NF" requirement for missing data prevents fabrication
       - No inference rule ensures evidence-based extraction
       - Schema compliance maintains data consistency
       - Notes separation prevents data contamination
    """
    return f"""
<PERSONA>
You are an accurate scientific data extractor. Your task is to accurately extract specific pieces of information for a given species from a provided text chunk.
</PERSONA>

<TASK_DEFINITION>
For the species '{species_name}', extract the required data fields from the following text chunk.

Text Chunk for Analysis:
---
{text_chunk}
---
</TASK_DEFINITION>

<EXAMPLES>
Use these examples to understand the context and desired output format:
{examples_text if examples_text else "No examples provided."}
</EXAMPLES>

<OUTPUT_REQUIREMENTS>
Your output MUST be a JSON list containing exactly one JSON object.  
Do not include any text outside this JSON.  
The JSON MUST be valid and parseable.

**JSON Schema:**
{{
  "species": "{species_name}",
  "data": {{ ... }},
  "notes": "Any comments on the extraction process or if data is not found."
}}

{data_fields_schema}

---
**CONTEXT**
Not all species will have complete data available in the text. Use the 'NF' placeholder where information is missing.
Some species are mentioned in passing, not actually being assessed in the text. Also use 'NF' for those cases.
NEVER invent or infer information.
---
**SCIENTIFIC ACCURACY RULES:**
1. **MANDATORY 'NF' FOR MISSING DATA:** If you cannot find the information for a specific field in the text, you MUST use the exact string "NF".
2. **NO GUESSING OR INFERENCE:** Do not invent or infer values. Only extract values explicitly present in the text.
3. **STRICT SCHEMA COMPLIANCE:** Every field defined in the schema MUST be present in the 'data' object, even if its value is "NF".
4. **NOTES ARE ONLY FOR EXPLANATION:** The 'notes' field is for describing ambiguities or reasons for "NF". It must never contain data values that belong in 'data'.
5. **VALID JSON ONLY:** Your response must be syntactically correct JSON and nothing else.
---
</OUTPUT_REQUIREMENTS>
"""


def get_default_image_prompt(species_name: str, data_fields_schema: str, examples_text: str) -> str:
    """
    Generates specialized prompt for image-based species data extraction.
    
    Creates a prompt template optimized for vision-capable language models
    to extract structured data from PDF page images. This approach is essential
    for documents with tables, figures, or complex layouts that don't extract
    well as plain text.
    
    Args:
        species_name: Target species for data extraction
        data_fields_schema: Formatted schema describing required output fields
        examples_text: Optional examples to guide extraction behavior
        
    Returns:
        Complete prompt string ready for multimodal LLM submission
        
    Vision-Specific Considerations:
    - Emphasizes analysis of all visual elements (text, tables, figures)
    - Accounts for potential OCR challenges in image interpretation
    - Provides explicit instructions for systematic image scanning
    - Maintains same output format as text-based extraction for consistency
    
    Multimodal Best Practices:
    - Clear persona establishment for visual analysis expertise
    - Explicit instruction to examine all image content types
    - Same rigorous output formatting requirements
    - Consistent "NF" handling for missing visual information
    """
    return f"""
<PERSONA>
You are an expert scientific data extractor. Your task is to accurately extract specific pieces of information for a given species from the provided page image(s).
</PERSONA>

<TASK_DEFINITION>
For the species '{species_name}', analyze the provided image(s) and extract the required data fields. Pay close attention to all text, tables, and figures.
</TASK_DEFINITION>

<EXAMPLES>
Use these examples to understand the context and desired output format:
{examples_text if examples_text else "No examples provided."}
</EXAMPLES>

<OUTPUT_REQUIREMENTS>
Your output MUST be a JSON list containing exactly one JSON object.  
Do not include any text outside this JSON.  
The JSON MUST be valid and parseable.

**JSON Schema:**
{{
  "species": "{species_name}",
  "data": {{ ... }},
  "notes": "Any comments on the extraction process or if data is not found."
}}

{data_fields_schema}

---
**CONTEXT**
Not all species will have complete data available in the text. Use the 'NF' placeholder where information is missing.
Some species are mentioned in passing, not actually being assessed in the text. Also use 'NF' for those cases.
NEVER invent or infer information.
---
**VISUAL ANALYSIS RULES:**
1. **ALWAYS POPULATE ALL DATA FIELDS:** Every field in the schema under 'data' MUST be present, even if its value is "NF".
2. **MANDATORY 'NF' FOR MISSING DATA:** If you cannot find the information for a field in the image, you MUST use the exact string "NF". Do not omit the field, leave it blank, or use null.
3. **NO GUESSING OR INFERENCE:** Do not invent or infer values. Only extract values explicitly present in the image.
4. **NOTES ARE ONLY FOR EXPLANATION:** The 'notes' field is for describing ambiguities or reasons for "NF". It must never contain data values that belong in 'data'.
5. **STRICT SCHEMA COMPLIANCE:** The JSON must strictly match the schema. No extra keys or formatting variations are allowed.
6. **VALID JSON ONLY:** Your response must be syntactically correct JSON and nothing else.
---
</OUTPUT_REQUIREMENTS>
"""

def get_default_verification_prompt(species_data_list_for_llm: str, data_fields_schema: str) -> str:
    """
    Generates prompt for automated verification of extraction results.
    
    Creates a specialized prompt for quality control workflows where an LLM
    re-examines source documents to verify previously extracted data. This
    supports iterative improvement and accuracy assessment of extraction
    pipelines.
    
    Args:
        species_data_list_for_llm: Formatted list of species and expected data
        data_fields_schema: Schema describing required verification fields
        
    Returns:
        Complete verification prompt for LLM submission
        
    Verification Workflow:
    1. Provide previously extracted data as context
    2. Instruct LLM to re-examine source document
    3. Extract current values without comparison bias
    4. Separate extraction task from validation logic
    
    Quality Assurance Strategy:
    - Independent re-extraction reduces confirmation bias
    - Expected data provides context without influencing results
    - Systematic field-by-field verification
    - Standardized "NF" handling for missing information
    
    Scientific Applications:
    - Accuracy assessment of extraction algorithms
    - Ground truth dataset generation
    - Identification of extraction errors and biases
    - Iterative improvement of prompt engineering
    """
    return f"""
<PERSONA>
You are a highly meticulous scientific data extraction assistant. Your task is to review a full PDF document I have provided and find the current data for a list of species.
</PERSONA>

<TASK_DEFINITION>
For EACH species in the 'Species List' below, you must:
1. Locate the species in the document.
2. Find the actual value(s) for the specified data fields.

I have provided 'expected_data' from a previous run for context, but your primary mission is to extract the true values from the document.

**Species List and Contextual Expected Data:**
{species_data_list_for_llm}

**Data Fields Schema (The fields you must find values for):**
{data_fields_schema}
</TASK_DEFINITION>

<OUTPUT_REQUIREMENTS>
Your output MUST be a JSON list containing exactly one JSON object per species.  
Do not include any text outside this JSON.  
The JSON MUST be valid and parseable.

**JSON Schema for EACH item in the output list:**
{{
  "species": "Species Name from Input List",
  "expected_data": {{ "field_name_1": "Expected Value", ... }},
  "found_data": {{ "field_name_1": "Value from Document", ... }},
  "notes": "Any general notes about this species' verification (e.g., page number where data was found)."
}}

---
**VERIFICATION ACCURACY RULES:**
1. **POPULATE 'found_data':** Your primary task is to fill the 'found_data' object with values discovered in the document.
2. **USE 'NF' FOR MISSING DATA:** If you cannot find the information for a specific field, you MUST use the exact string "NF".
3. **INCLUDE ALL SPECIES:** Each species in the input list MUST appear in the output with its own JSON object.
4. **NO GUESSING OR INFERENCE:** Only record values explicitly present in the document. Do not generate or infer missing values.
5. **STRICT SCHEMA COMPLIANCE:** The output must strictly follow the JSON schema provided. No extra keys, text, or formatting variations are allowed.
6. **VALID JSON ONLY:** Your response must be syntactically correct JSON and nothing else.
---
</OUTPUT_REQUIREMENTS>
"""