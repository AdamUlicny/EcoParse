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
from .sourcetext import get_species_context_chunks, get_species_page_images

extraction_list_adapter = TypeAdapter(ExtractionResultList)

class Extractor:
    def __init__(self, project_config: Dict[str, Any], llm_config: Dict[str, Any]):
        self.project_config = project_config
        self.llm_config = llm_config
        self.data_fields_schema = generate_data_fields_schema(
            project_config.get("data_fields", [])
        )

    def run_extraction(
        self, species_list: List[str], source_context: Dict[str, Any], update_callback=None
    ) -> Tuple[List[Dict], float, int, int]:

        all_results = []
        total_input_tokens = 0
        total_output_tokens = 0
        max_workers = self.llm_config.get("concurrent_requests", 5)
        
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self._extract_for_single_species, species, source_context)
                for species in species_list
            ]

            for i, future in enumerate(as_completed(futures)):
                result, in_tokens, out_tokens = future.result()
                if result:
                    all_results.append(result)
                
                # Aggregate token counts
                total_input_tokens += in_tokens or 0
                total_output_tokens += out_tokens or 0
                
                if update_callback:
                    update_callback(i + 1, len(species_list))
        
        runtime = time.time() - start_time
        return all_results, runtime, total_input_tokens, total_output_tokens

    def _extract_for_single_species(self, species_name: str, context: Dict[str, Any]) -> Tuple[Optional[Dict], int, int]:
        """Now returns a tuple including token counts."""
        # ... (logic is the same, but the return value changes)
        extraction_method = context.get("extraction_method")
        examples_text = context.get("examples_text", "")
        
        no_context_result = (
            {"species": species_name, "data": {}, "notes": "No text context found."},
            0, 0
        )
        no_image_result = (
            {"species": species_name, "data": {}, "notes": "No page images found."},
            0, 0
        )

        if extraction_method == "Text-based":
            chunks = get_species_context_chunks(
                context['full_text'],
                context['species_df'][context['species_df']['Name'] == species_name],
                context['context_before'],
                context['context_after']
            ).get(species_name, [])
            
            if not chunks: return no_context_result
            
            prompt = get_default_text_prompt(
                species_name, "\n---\n".join(chunks), self.data_fields_schema, examples_text
            )
            return self._call_llm(prompt, images=None)
        
        elif extraction_method == "Image-based":
            images = get_species_page_images(
                context['pdf_buffer'],
                context['species_df'][context['species_df']['Name'] == species_name]
            ).get(species_name, [])

            if not images: return no_image_result

            prompt = get_default_image_prompt(species_name, self.data_fields_schema, examples_text)
            return self._call_llm(prompt, images=images)

        return None, 0, 0

    def _call_llm(self, prompt: str, images: Optional[List[bytes]] = None) -> Tuple[Optional[Dict], int, int]:
        """Ensures all paths return a tuple with token counts."""
        provider = self.llm_config.get("provider")
        if provider == "Google Gemini":
            return self._call_gemini(prompt, images)
        elif provider == "Ollama":
            return self._call_ollama(prompt, images)
        return None, 0, 0

    def _call_gemini(self, prompt: str, images: Optional[List[bytes]]) -> Tuple[Optional[Dict], int, int]:
        """Parses usage_metadata and returns token counts."""
        try:
            client = genai.Client(api_key=self.llm_config["api_key"])
            content = [prompt] 
            if images:
                for img_bytes in images:
                    content.insert(0, types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
            
            config = {"response_mime_type": "application/json", "temperature": 0.1}
            response = client.models.generate_content(
                model=self.llm_config["model"], contents=content, config=config
            )
            
            in_tokens = response.usage_metadata.prompt_token_count
            out_tokens = response.usage_metadata.candidates_token_count
            
            parsed_list = extraction_list_adapter.validate_json(response.text)
            result = parsed_list.root[0].model_dump() if parsed_list.root else None
            return result, in_tokens, out_tokens
        
        except Exception as e:
            print(f"Error with Gemini API: {e}")
            return None, 0, 0

    def _call_ollama(self, prompt: str, images: Optional[List[bytes]]) -> Tuple[Optional[Dict], int, int]:
        """Now uses a specific client with the configured host URL."""
        try:
            client = ollama.Client(host=self.llm_config["ollama_url"])

            messages = [{"role": "user", "content": prompt}]
            if images:
                messages[0]["images"] = images

            response = client.chat(
                model=self.llm_config["model"],
                messages=messages,
                format="json",
                options={"temperature": 0.1}
            )

            response_content = response['message']['content']
            in_tokens = response.get('prompt_eval_count', 0)
            out_tokens = response.get('eval_count', 0)
            
            try:
                parsed_list = extraction_list_adapter.validate_json(response_content)
                result = parsed_list.root[0].model_dump() if parsed_list.root else None
            except ValidationError:
                single_object = SpeciesData.model_validate_json(response_content)
                result = single_object.model_dump()
            
            return result, in_tokens, out_tokens
        
        except Exception as e:
            print(f"Error with Ollama API: {e}")
            return None, 0, 0