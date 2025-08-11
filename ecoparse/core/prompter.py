from typing import List, Dict, Any

def generate_data_fields_schema(data_fields: List[Dict[str, Any]]) -> str:
    """Creates a string representation of the data fields schema for the LLM prompt."""
    schema_parts = ["The 'data' object in the JSON output should contain the following keys:"]
    for field in data_fields:
        field_name = field.get('name')
        field_desc = field.get('description')
        validation_vals = field.get('validation_values')

        part = f"- '{field_name}': {field_desc}"
        if validation_vals:
            # Add the 'Not Found' code to the list of valid options for clarity
            if "NF" not in validation_vals:
                validation_vals.append("NF")
            part += f" The value MUST be one of {validation_vals}."
        schema_parts.append(part)
    return "\n".join(schema_parts)


def get_default_text_prompt(species_name: str, text_chunk: str, data_fields_schema: str, examples_text: str) -> str:
    """Returns a generalized default prompt for text-based extraction with stricter rules."""
    return f"""
<PERSONA>
You are an expert scientific data extractor. Your task is to accurately extract specific pieces of information for a given species from a provided text chunk.
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
Your output MUST be a JSON list containing a single JSON object.

**JSON Schema:**
{{
  "species": "{species_name}",
  "data": {{ ... }},
  "notes": "Any comments on the extraction process or if data is not found."
}}

{data_fields_schema}

---
**RULES:**
1.  **MANDATORY 'NF' FOR MISSING DATA:** If you cannot find the information for a specific field in the text, you MUST use the exact string "NF" (for "Not Found") as its value. 
2.  **NOTES ARE FOR EXPLANATION:** The 'notes' field is for explaining *why* a value was "NF" or if there was ambiguity. It is separate from and does not replace the requirement to populate the data fields.
---
</OUTPUT_REQUIREMENTS>
"""

def get_default_image_prompt(species_name: str, data_fields_schema: str, examples_text: str) -> str:
    """Returns a generalized default prompt for image-based extraction with stricter rules."""
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
Your output MUST be a JSON list containing a single JSON object.

**JSON Schema:**
{{
  "species": "{species_name}",
  "data": {{ ... }},
  "notes": "Any comments on the extraction process or if data is not found."
}}

{data_fields_schema}

---
**RULES:**
1.  **ALWAYS POPULATE ALL DATA FIELDS:** Every single field defined in the schema under 'data' MUST be present in your output.
2.  **MANDATORY 'NF' FOR MISSING DATA:** If you cannot find the information for a specific field in the image, you MUST use the exact string "NF" (for "Not Found") as its value. **DO NOT** omit the field, leave it empty, or use null.
3.  **NOTES ARE FOR EXPLANATION:** The 'notes' field is for explaining *why* a value was "NF" or if there was ambiguity. It is separate from and does not replace the requirement to populate the data fields.
---
</OUTPUT_REQUIREMENTS>
"""


def get_default_verification_prompt(species_data_list_for_llm: str, data_fields_schema: str) -> str:
    """
    Returns a default prompt for automated verification using the full document.
    Includes the list of species and their expected data for the LLM to verify.
    """
    return f"""
<PERSONA>
You are a highly meticulous scientific data verification assistant. Your task is to review a full PDF document I have provided and verify previously extracted data for a list of species.
</PERSONA>

<TASK_DEFINITION>
For EACH species in the 'Species Data to Verify' list below, you must:
1.  Locate the species in the document.
2.  Find the actual value(s) for the specified data fields.
3.  Compare the 'found' value(s) with the 'expected' value(s) provided.

**Species Data to Verify (Expected Data from Previous Extraction):**
{species_data_list_for_llm}

**Data Fields Schema (for accurate extraction from document):**
{data_fields_schema}

</TASK_DEFINITION>

<OUTPUT_REQUIREMENTS>
Your output MUST be a single JSON list. Each object in this list corresponds to one species from the input 'Species Data to Verify' list and MUST conform to the following schema:

**JSON Schema for EACH item in the output list:**
{{
  "species": "Species Name from Input List",
  "verified_data": {{
    "field_name_1": {{
      "expected": "Expected Value",
      "found": "Value from Document",
      "verified": true/false,
      "status": "Match/Mismatch/NotFound/Error"
    }},
    "field_name_2": {{...}},
    // ... (for all data fields defined in the schema)
  }},
  "notes": "Any general notes about this species' verification (e.g., clarity of data, issues)."
}}

---
**CRITICAL RULES FOR VERIFICATION OUTPUT:**
1.  **ALL SPECIES**: You MUST include an entry for EVERY species provided in the 'Species Data to Verify' list, even if data is not found or an error occurs.
2.  **ALL FIELDS**: For each species, you MUST include an entry for EVERY data field defined in the 'Data Fields Schema' under `verified_data`.
3.  **"found" VALUE**: If you cannot find a value for a field in the document, use "NF" for "found". Do NOT omit, leave empty, or use null.
4.  **"verified" BOOLEAN**: Set to `true` if `expected` exactly matches `found`. Otherwise, set to `false`.
5.  **"status" STRING**:
    -   "Match": If `verified` is `true`.
    -   "Mismatch": If `verified` is `false` AND `found` is NOT "NF".
    -   "NotFound": If `found` is "NF".
    -   "Error": If you encountered a problem processing this species.

</OUTPUT_REQUIREMENTS>
"""