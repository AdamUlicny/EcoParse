from typing import List, Dict, Any

def generate_data_fields_schema(data_fields: List[Dict[str, Any]]) -> str:
    schema_parts = ["The 'data' object in the JSON output should contain the following keys:"]
    for field in data_fields:
        field_name = field.get('name')
        field_desc = field.get('description')
        validation_vals = field.get('validation_values')

        part = f"- '{field_name}': {field_desc}"
        if validation_vals:
            if "NF" not in validation_vals:
                validation_vals.append("NF")
            part += f" The value MUST be one of {validation_vals}."
        schema_parts.append(part)
    return "\n".join(schema_parts)


def get_default_text_prompt(species_name: str, text_chunk: str, data_fields_schema: str, examples_text: str) -> str:
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
**RULES:**
1. **MANDATORY 'NF' FOR MISSING DATA:** If you cannot find the information for a specific field in the text, you MUST use the exact string "NF".
2. **NO GUESSING OR INFERENCE:** Do not invent or infer values. Only extract values explicitly present in the text.
3. **STRICT SCHEMA COMPLIANCE:** Every field defined in the schema MUST be present in the 'data' object, even if its value is "NF".
4. **NOTES ARE ONLY FOR EXPLANATION:** The 'notes' field is for describing ambiguities or reasons for "NF". It must never contain data values that belong in 'data'.
5. **VALID JSON ONLY:** Your response must be syntactically correct JSON and nothing else.
---
</OUTPUT_REQUIREMENTS>
"""


def get_default_image_prompt(species_name: str, data_fields_schema: str, examples_text: str) -> str:
    """Returns a stricter default prompt for image-based extraction."""
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
**RULES:**
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
    """Returns a stricter prompt for automated verification."""
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
**CRITICAL RULES FOR OUTPUT:**
1. **POPULATE 'found_data':** Your primary task is to fill the 'found_data' object with values discovered in the document.
2. **USE 'NF' FOR MISSING DATA:** If you cannot find the information for a specific field, you MUST use the exact string "NF".
3. **INCLUDE ALL SPECIES:** Each species in the input list MUST appear in the output with its own JSON object.
4. **NO GUESSING OR INFERENCE:** Only record values explicitly present in the document. Do not generate or infer missing values.
5. **STRICT SCHEMA COMPLIANCE:** The output must strictly follow the JSON schema provided. No extra keys, text, or formatting variations are allowed.
6. **VALID JSON ONLY:** Your response must be syntactically correct JSON and nothing else.
---
</OUTPUT_REQUIREMENTS>
"""