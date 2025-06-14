import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional

from openai import OpenAI, APITimeoutError, APIConnectionError, APIError
from pypdf import PdfReader

logger = logging.getLogger("pdf2md.ocr")

class OcrProcessor:
    def __init__(self, base_url: str, api_key: str, model_name: str, timeout: int = 120):
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)

    async def process_page(self, pdf_path: str, page_num: int, max_retries: int = 3) -> Optional[str]:
        """OCR a single page, return markdown or None on error. Retries transient errors."""
        import time
        delay = 2
        for attempt in range(1, max_retries + 1):
            start_time = time.time()
            try:
                from olmocr.pipeline import build_page_query
                query = await build_page_query(pdf_path, page=page_num, target_longest_image_dim=1024, target_anchor_text_len=6000)
                query['model'] = self.model_name
                response = self.client.chat.completions.create(**query)
                duration = time.time() - start_time
                logger.info(f"OCR page {page_num} took {duration:.2f}s (attempt {attempt})")
                if response is None:
                    logger.error(f"LM Studio API returned None for page {page_num} of {pdf_path}. Query: {query}")
                    return f"**[ERROR: LM Studio API returned None for page {page_num}]**"
                if not hasattr(response, 'choices') or not response.choices:
                    logger.error(f"LM Studio API response missing 'choices' for page {page_num} of {pdf_path}. Response: {response}")
                    return f"**[ERROR: LM Studio API response missing 'choices' for page {page_num}]**"
                choice = response.choices[0]
                if not hasattr(choice, 'message') or not hasattr(choice.message, 'content'):
                    logger.error(f"LM Studio API response missing 'message.content' for page {page_num} of {pdf_path}. Response: {response}")
                    return f"**[ERROR: LM Studio API response missing 'message.content' for page {page_num}]**"
                model_obj = json.loads(choice.message.content)
                if 'natural_text' in model_obj and model_obj['natural_text']:
                    return model_obj['natural_text'].strip()
                elif 'natural_text' in model_obj and model_obj['natural_text'] is None:
                    # Handle case where model classifies page as diagram but might contain extractable text
                    # Log the classification but attempt to provide useful information
                    classification_info = []
                    if model_obj.get('is_diagram', False):
                        classification_info.append("diagram")
                    if model_obj.get('is_table', False):
                        classification_info.append("table")
                    if model_obj.get('primary_language'):
                        classification_info.append(f"language: {model_obj['primary_language']}")
                    
                    classification_str = ", ".join(classification_info) if classification_info else "unknown content"
                    logger.warning(f"Page {page_num} classified as {classification_str} with no extractable text - this might be a misclassification for forms or structured documents")
                    return f"**[Page {page_num}: Classified as {classification_str} - no text extracted. This may be a form or structured document that requires manual review.]**"
                else:
                    logger.error(f"LM Studio API response JSON missing 'natural_text' for page {page_num} of {pdf_path}. JSON: {model_obj}")
                    return f"**[ERROR: LM Studio API response JSON missing 'natural_text' for page {page_num}]**"
            except (APITimeoutError, APIConnectionError, APIError) as e:
                logger.warning(f"Transient error on page {page_num} (attempt {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue
                else:
                    logger.error(f"Max retries exceeded for page {page_num} of {pdf_path}")
                    return f"**[ERROR: Max retries exceeded for page {page_num}]**"
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LM Studio API response as JSON for page {page_num} of {pdf_path}: {e}.")
                return f"**[ERROR: LM Studio API response not valid JSON for page {page_num}]**"
            except Exception as e:
                logger.error(f"Failed to OCR page {page_num} of {pdf_path}: {e}")
                return f"**[ERROR: Exception during OCR page {page_num}: {e}]**"
        return None

    async def process_pdf_to_markdown(self, pdf_path: str, delimiter: str = "delimited") -> str:
        import time
        pdf_path = Path(pdf_path)
        try:
            with open(pdf_path, 'rb') as pdf_file:
                reader = PdfReader(pdf_file)
                num_pages = len(reader.pages)
        except Exception as e:
            logger.error(f"Failed to read PDF {pdf_path}: {e}")
            return f"**[ERROR: Failed to read PDF {pdf_path}: {e}]**"
        
        markdown_chunks: List[str] = []
        page_failures = 0
        total_start = time.time()
        for page_num in range(1, num_pages + 1):
            page_start = time.time()
            md = await self.process_page(str(pdf_path), page_num)
            page_time = time.time() - page_start
            if md is not None and not md.startswith("**[ERROR"):
                markdown_chunks.append(md)
            else:
                markdown_chunks.append(md or f"**[ERROR: Failed to OCR page {page_num}]**")
                page_failures += 1
            logger.info(f"Page {page_num} processed in {page_time:.2f}s")
        total_time = time.time() - total_start
        logger.info(f"OCR for {pdf_path} completed: {num_pages} pages in {total_time:.2f}s ({page_failures} errors)")
        if page_failures == num_pages:
            markdown_chunks.insert(0, f"**[ERROR: All {num_pages} pages failed OCR for {pdf_path}]**\n")
        if delimiter == "delimited":
            sep = "\n\n---\n\n"
            return sep.join(markdown_chunks)
        else:
            return "\n\n".join(markdown_chunks)

# Synchronous wrapper for use in callback

def ocr_pdf_to_markdown_sync(pdf_path: str, base_url: str, api_key: str, model_name: str, timeout: int, delimiter: str) -> str:
    processor = OcrProcessor(base_url, api_key, model_name, timeout)
    return asyncio.run(processor.process_pdf_to_markdown(pdf_path, delimiter=delimiter))
