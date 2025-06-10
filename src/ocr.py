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

    async def process_page(self, pdf_path: str, page_num: int) -> Optional[str]:
        """OCR a single page, return markdown or None on error."""
        try:
            # olmocr build_page_query import assumed available
            from olmocr.pipeline import build_page_query
            query = await build_page_query(pdf_path, page=page_num, target_longest_image_dim=1024, target_anchor_text_len=6000)
            query['model'] = self.model_name
            response = self.client.chat.completions.create(**query)
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
            # Parse JSON and extract markdown from 'natural_text'
            model_obj = json.loads(choice.message.content)
            if 'natural_text' in model_obj and model_obj['natural_text']:
                return model_obj['natural_text'].strip()
            else:
                logger.error(f"LM Studio API response JSON missing 'natural_text' for page {page_num} of {pdf_path}. JSON: {model_obj}")
                return f"**[ERROR: LM Studio API response JSON missing 'natural_text' for page {page_num}]**"
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LM Studio API response as JSON for page {page_num} of {pdf_path}: {e}. Content: {choice.message.content}")
            return f"**[ERROR: LM Studio API response not valid JSON for page {page_num}]**"
        except Exception as e:
            logger.error(f"Failed to OCR page {page_num} of {pdf_path}: {e}")
            return f"**[ERROR: Exception during OCR page {page_num}: {e}]**"

    async def process_pdf_to_markdown(self, pdf_path: str, delimiter: str = "delimited") -> str:
        pdf_path = Path(pdf_path)
        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)
        markdown_chunks: List[str] = []
        for page_num in range(1, num_pages + 1):
            md = await self.process_page(str(pdf_path), page_num)
            if md is not None:
                markdown_chunks.append(md)
            else:
                markdown_chunks.append(f"**[ERROR: Failed to OCR page {page_num}]**")
        if delimiter == "delimited":
            sep = "\n\n---\n\n"
            return sep.join(markdown_chunks)
        else:
            return "\n\n".join(markdown_chunks)

# Synchronous wrapper for use in callback

def ocr_pdf_to_markdown_sync(pdf_path: str, base_url: str, api_key: str, model_name: str, timeout: int, delimiter: str) -> str:
    processor = OcrProcessor(base_url, api_key, model_name, timeout)
    return asyncio.run(processor.process_pdf_to_markdown(pdf_path, delimiter=delimiter))
