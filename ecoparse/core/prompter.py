"""
Prompt Engineering and Template Generation Module

This module provides specialized prompt templates for large language model
interactions in species data extraction tasks. It implements systematic
prompt engineering strategies to ensure consistent, accurate, and structured
outputs from various LLM providers.

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
You are a precise scientific data extractor. You extract ONLY formally stated values, never inferred from narrative.
</PERSONA>

<TASK_DEFINITION>
For '{species_name}', extract data fields from the text below. 

Text Chunk:
---
{text_chunk}
---
</TASK_DEFINITION>

<CRITICAL_RULES>
**FORMAL vs NARRATIVE DATA:**
- **FORMAL**: Explicit codes, values, or designations directly assigned to '{species_name}' (e.g., "Status: VU", "Category: Endangered", a dedicated assessment table row).
- **NARRATIVE**: Descriptive text that implies something about '{species_name}' but provides no formal value (e.g., "is expanding", "is threatened", "is common").

**EXTRACT ONLY FORMAL DATA.** If no formal value exists for a field, use "NF" – even if narrative text implies a status.

**OWNERSHIP CHECK:**
1. Is '{species_name}' the PRIMARY SUBJECT of structured data in this text?
   - YES: Extract from '{species_name}''s data only.
   - NO (mentioned in another entity's context, e.g., "uses nests of {species_name}"): ALL fields = "NF".

2. Does the text contain FORMAL values for the requested fields?
   - YES: Extract them.
   - NO (only narrative descriptions): ALL fields = "NF".
</CRITICAL_RULES>

<EXAMPLES>
{examples_text if examples_text else "No examples provided."}
</EXAMPLES>

<OUTPUT_REQUIREMENTS>
Output a JSON list with exactly one object. No text outside the JSON.

**Schema:**
{{
  "species": "{species_name}",
  "data": {{ ... }},
  "notes": "Brief explanation of data source or why NF.",
  "review_flag": "OK | CHECK | NF"
}}

**review_flag:**
- `OK`: Formal data clearly found for '{species_name}'.
- `CHECK`: Ambiguous (narrative only, role unclear, uncertain attribution).
- `NF`: All fields "NF".

{data_fields_schema}

**RULES**
1. Extract ONLY formal/explicit values. Never infer from narrative.
2. If '{species_name}' is mentioned in another entity's context, all fields = "NF".
3. If no formal data exists for a field, use "NF".
4. Set review_flag to "CHECK" if extraction relies on any interpretation.
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
You are an expert scientific data extractor. You extract ONLY formal/structured values, never inferred from narrative.
</PERSONA>

<DOCUMENT_FORMATS>
Documents may contain species data in various layouts:
- **Dedicated pages**: One species per page with header and assessment section.
- **Tables**: Multiple species in rows; each row contains one species' data.
- **Multi-section pages**: Several species listed sequentially in paragraphs or blocks.
- **Mixed**: Combinations of the above.
</DOCUMENT_FORMATS>

<CRITICAL_RULES>
**FORMAL vs NARRATIVE DATA:**
- **FORMAL**: Explicit codes, values, or designations in structured format (e.g., status boxes, table cells, labeled fields like "Status: VU").
- **NARRATIVE**: Descriptive text implying something (e.g., "is expanding", "is threatened", "is common") WITHOUT providing a formal code/value.

**EXTRACT ONLY FORMAL DATA.** Narrative descriptions ≠ formal values. Use "NF" if only narrative exists.

**OWNERSHIP CHECK:**
1. Does '{species_name}' have its OWN formal data (dedicated row, section, status box)?
   - YES → Extract from that section ONLY.
   - NO (mentioned in another entity's text, e.g., "uses nests of {species_name}") → ALL fields = "NF".

2. Are the values FORMAL (explicit codes/designations) or NARRATIVE (implied from text)?
   - FORMAL → Extract.
   - NARRATIVE only → "NF".
</CRITICAL_RULES>

<EXAMPLES>
{examples_text if examples_text else "No examples provided."}
</EXAMPLES>

<OUTPUT_REQUIREMENTS>
Output a JSON list with exactly one object. No text outside the JSON.

**Schema:**
{{
  "species": "{species_name}",
  "data": {{ ... }},
  "notes": "State: ASSESSED (source location) or MENTIONED ONLY (why NF). Note if only narrative was found.",
  "review_flag": "OK | CHECK | NF"
}}

**review_flag:**
- `OK`: Formal data clearly found in dedicated section/row.
- `CHECK`: Ambiguous (narrative only, role unclear, uncertain attribution).
- `NF`: All fields "NF".

{data_fields_schema}
</OUTPUT_REQUIREMENTS>

<RULES>
1. **FORMAL ONLY**: Extract explicit values. Never infer from narrative descriptions.
2. **NO CROSS-CONTAMINATION**: Data from adjacent rows/sections belongs to OTHER entities.
3. **MENTIONED = NF**: If '{species_name}' has no dedicated formal data, all fields = "NF".
4. **NARRATIVE = NF**: If only descriptive text exists (no formal codes), all fields = "NF".
5. **CHECK IF DOUBT**: Use "CHECK" flag if any interpretation was required.
6. **VALID JSON ONLY**.
</RULES>
"""

def get_default_verification_prompt(species_data_list_for_llm: str, data_fields_schema: str) -> str:
    """
    Approach currently not recommended due to high costs.

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

def generate_verification_rubric_prompt(data_fields_schema: str, prompt_examples: List[Dict[str, Any]] = None) -> str:
    """
    Generates a meta-prompt to create a strict verification rubric.
    
    Asks an LLM to review the extraction schema and examples to create 
    a checklist for verified extraction accuracy.
    """
    examples_context = ""
    if prompt_examples:
        examples_context = "Here are examples of correct extraction input/output:\n"
        for i, ex in enumerate(prompt_examples[:3]): # Limit to first 3 to save tokens
             examples_context += f"Example {i+1}:\nInput: {ex.get('input', '')[:200]}...\nOutput: {json.dumps(ex.get('output', {}))}\n\n"

    return f"""
<TASK>
You are a QA Specialist for a scientific data extraction project.
Your goal is to create a "Verification Rubric" (a checklist of rules) that another analyst will use to verify if data extracted from a PDF is correct.

Based ONLY on the schema and examples below, write a set of 5-10 strict Yes/No rules or checks to validate data.
Focus on:
1. Data type/format correctness (e.g., is it a number? is it one of the allowed values?).
2. Distinction between "Formal" data (tables, codes) vs "Narrative" (text descriptions).
3. Handling of "NF" (Not Found).

<SCHEMA>
{data_fields_schema}
</SCHEMA>

<EXAMPLES>
{examples_context}
</EXAMPLES>

<OUTPUT_FORMAT>
Return ONLY the rubric text as a bulleted list. No intro/outro.
</OUTPUT_FORMAT>
</TASK>
"""

def get_openrouter_verification_prompt(species_data_list_for_llm: str, verification_rubric: str, examples_text: str = "", extraction_rules: str = "") -> str:
    """
    Generates a prompt for OpenRouter/LLM verification using the dynamic rubric.
    
    Includes a "confidence_score" and "verification_status" in the output schema.
    """
    return f"""
<PERSONA>
You are a meticulous Data Verification Specialist. Your task is to verify results of species-specific extraction.
</PERSONA>

<TASK>
For the provided species list, search the PDF (provided as context) and to the best of your ability, verify the provided "Expected Data".
</TASK>

<CONTEXT_EXAMPLES>
Here are few-shot examples of correct extractions provided for the previous extraction run. Use these to understand the formatting and logic:
{examples_text if examples_text else "No examples provided."}
</CONTEXT_EXAMPLES>

<EXTRACTION_RULES>
Here are the general rules that were used to extract this data:
{extraction_rules if extraction_rules else "No specific rules provided."}
</EXTRACTION_RULES>

<VERIFICATION_RUBRIC_AND_SCHEMA>
This is the data we are looking for (Schema) and specific verification checks:
{verification_rubric}
</VERIFICATION_RUBRIC_AND_SCHEMA>

<SPECIES_LIST_TO_VERIFY>
{species_data_list_for_llm}
</SPECIES_LIST_TO_VERIFY>

<OUTPUT_REQUIREMENTS>
Output a valid JSON list of objects. One object per species.

**JSON Schema:**
{{
  "species": "Species Name",
  "verification_status": "OK | FLAGGED | NF",
  "confidence_score": 10, // Integer 1-10
  "issue_description": "None" or "Description of error/ambiguity...",
  "corrected_data": {{ "field_name": "Correct Value" }} // Only include fields that need correction. Empty if Status is OK.
}}
</OUTPUT_REQUIREMENTS>

<CRITICAL_INSTRUCTIONS>
- **OK**: Data matches the document and rules.
- **FLAGGED**: Data is incorrect, missing, contradicts rules (e.g., narrative vs formal), or is ambiguous.
- **NF**: Species or data not found.
- If you are unsure (blurry text, conflicting info), set status to **FLAGGED** and confidence < 8.
- Be accurate but allow for minor OCR or formatting discrepancies (e.g., "ssp." vs "subsp.").
</CRITICAL_INSTRUCTIONS>
"""

def get_general_extraction_rules() -> str:
    """
    Returns the standard, streamlined extraction rules used in the main prompt.
    """
    return """
<CRITICAL_RULES>
**FORMAL vs NARRATIVE DATA:**
- **FORMAL**: Explicit codes, values, or designations directly assigned to the species (e.g., "Status: VU", assessment table row).
- **NARRATIVE**: Descriptive text that implies something but provides no formal value (e.g., "is expanding", "is threatened").
- **EXTRACT ONLY FORMAL DATA.** If no formal value exists, use "NF".

**OWNERSHIP CHECK:**
1. Is the species the PRIMARY SUBJECT of structured data?
   - YES: Extract.
   - NO (mentioned in another entity's context): ALL fields = "NF".
</CRITICAL_RULES>
"""
