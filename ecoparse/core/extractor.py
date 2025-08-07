import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

import ollama
# This is the correct import for the 'google-genai' package's Client pattern
from google import genai
from google.genai import types

from pydantic import ValidationError, TypeAdapter

from .models import ExtractionResultList
from .prompter import (
    generate_data_fields_schema, 
    get_default_text_prompt, 
    get_default_image_prompt
)
from .sourcetext import get_species_context_chunks, get_species_page_images

extraction_list_adapter = TypeAdapter(ExtractionResultList)

class Extractor:
    def __init__(self, project_config: Dict[str, Any], llm_config: Dict[str, Any]):
        self.project_config = project_config
        self.llm_config = llm_config
        self.data_fields_schema = generate_data_fields_schema(
            project_config.get("data_fields", [])
        )

    def run_extraction(self, species_list: List[str], source_context: Dict[str, Any], update_callback=None) -> List[Dict]:
        all_results = []
        max_workers = self.llm_config.get("concurrent_requests", 5)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self._extract_for_single_species, species, source_context)
                for species in species_list
            ]

            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                if result:
                    all_results.append(result)
                if update_callback:
                    update_callback(i + 1, len(species_list))
        
        return all_results

    def _extract_for_single_species(self, species_name: str, context: Dict[str, Any]) -> Optional[Dict]:
        extraction_method = context.get("extraction_method")
        examples_text = context.get("examples_text", "")

        if extraction_method == "Text-based":
            chunks = get_species_context_chunks(
                context['full_text'],
                context['species_df'][context['species_df']['Name'] == species_name],
                context['context_before'],
                context['context_after']
            ).get(species_name, [])
            
            if not chunks:
                return {"species": species_name, "data": {}, "notes": "No text context found."}
            
            prompt = get_default_text_prompt(
                species_name, "\n---\n".join(chunks), self.data_fields_schema, examples_text
            )
            return self._call_llm(prompt, images=None)
        
        elif extraction_method == "Image-based":
            images = get_species_page_images(
                context['pdf_buffer'],
                context['species_df'][context['species_df']['Name'] == species_name]
            ).get(species_name, [])

            if not images:
                return {"species": species_name, "data": {}, "notes": "No page images found."}

            prompt = get_default_image_prompt(species_name, self.data_fields_schema, examples_text)
            return self._call_llm(prompt, images=images)

        return None

    def _call_llm(self, prompt: str, images: Optional[List[bytes]] = None) -> Optional[Dict]:
        provider = self.llm_config.get("provider")
        if provider == "Google Gemini":
            return self._call_gemini(prompt, images)
        elif provider == "Ollama":
            return self._call_ollama(prompt, images)
        return None

    def _call_gemini(self, prompt: str, images: Optional[List[bytes]]) -> Optional[Dict]:
        # This version uses the genai.Client pattern correctly. It does NOT use .configure()
        try:
            client = genai.Client(api_key=self.llm_config["api_key"])
            
            content = []
            if images:
                for img_bytes in images:
                    content.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
            content.append(prompt)
            
            config = {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }

            response = client.models.generate_content(
                model=self.llm_config["model"],
                contents=content,
                config=config,
            )
            
            parsed_list = extraction_list_adapter.validate_json(response.text)
            return parsed_list.root[0].model_dump() if parsed_list.root else None
        
        except (ValidationError, json.JSONDecodeError) as e:
            response_text = "N/A"
            if 'response' in locals() and hasattr(response, 'text'):
                response_text = response.text
            print(f"Gemini Response Validation Error: {e}\nRaw Response: {response_text}")
            return None
        except Exception as e:
            print(f"Error with Gemini API: {e}")
            return None

    def _call_ollama(self, prompt: str, images: Optional[List[bytes]]) -> Optional[Dict]:
        try:
            messages = [{"role": "user", "content": prompt}]
            if images:
                messages[0]["images"] = images

            response = ollama.chat(
                model=self.llm_config["model"],
                messages=messages,
                format="json",
                options={"temperature": 0.1}
            )
            
            response_content = response['message']['content']
            parsed_list = extraction_list_adapter.validate_json(response_content)
            return parsed_list.root[0].model_dump() if parsed_list.root else None

        except (ValidationError, json.JSONDecodeError) as e:
            response_content = "N/A"
            if 'response' in locals() and 'message' in response and 'content' in response['message']:
                response_content = response['message']['content']
            print(f"Ollama Response Validation Error: {e}\nRaw Response: {response_content}")
            return None
        except Exception as e:
            print(f"Error with Ollama API: {e}")
            return None