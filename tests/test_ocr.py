import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from openai import APITimeoutError, APIConnectionError, APIError
from src.ocr import OcrProcessor, ocr_pdf_to_markdown_sync

class DummyResponse:
    def __init__(self, content):
        self.choices = [type('obj', (object,), {'message': type('obj', (object,), {'content': content})})()]

@pytest.mark.asyncio
async def test_process_pdf_to_markdown_delimited(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    # Create a dummy PDF with 2 pages
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    with open(pdf_path, "wb") as f:
        writer.write(f)

    # Patch process_page to return predictable markdown
    with patch.object(OcrProcessor, 'process_page', new=AsyncMock(side_effect=["# Page 1", "# Page 2"])):
        processor = OcrProcessor("http://fake", "fake", "fake", 10)
        md = await processor.process_pdf_to_markdown(str(pdf_path), delimiter="delimited")
        assert md == "# Page 1\n\n---\n\n# Page 2"

@pytest.mark.asyncio
async def test_process_pdf_to_markdown_concat(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    with open(pdf_path, "wb") as f:
        writer.write(f)

    with patch.object(OcrProcessor, 'process_page', new=AsyncMock(side_effect=["# Page 1", "# Page 2"])):
        processor = OcrProcessor("http://fake", "fake", "fake", 10)
        md = await processor.process_pdf_to_markdown(str(pdf_path), delimiter="concat")
        assert md == "# Page 1\n\n# Page 2"

@pytest.mark.asyncio
async def test_process_pdf_to_markdown_error(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with open(pdf_path, "wb") as f:
        writer.write(f)

    # Simulate error on OCR (None return)
    with patch.object(OcrProcessor, 'process_page', new=AsyncMock(return_value="**[ERROR: LM Studio API returned None for page 1]**")):
        processor = OcrProcessor("http://fake", "fake", "fake", 10)
        md = await processor.process_pdf_to_markdown(str(pdf_path), delimiter="delimited")
        assert "[ERROR: LM Studio API returned None for page 1]" in md

    # Simulate error: missing choices
    class NoChoicesResponse:
        def __init__(self):
            self.choices = []
    with patch.object(OcrProcessor, 'process_page', new=AsyncMock(return_value="**[ERROR: LM Studio API response missing 'choices' for page 1]**")):
        processor = OcrProcessor("http://fake", "fake", "fake", 10)
        md = await processor.process_pdf_to_markdown(str(pdf_path), delimiter="delimited")
        assert "[ERROR: LM Studio API response missing 'choices' for page 1]" in md

    # Simulate error: missing message.content
    class NoMessageContentResponse:
        class DummyMessage:
            pass
        def __init__(self):
            self.choices = [type('obj', (object,), {'message': self.DummyMessage()})()]
    with patch.object(OcrProcessor, 'process_page', new=AsyncMock(return_value="**[ERROR: LM Studio API response missing 'message.content' for page 1]**")):
        processor = OcrProcessor("http://fake", "fake", "fake", 10)
        md = await processor.process_pdf_to_markdown(str(pdf_path), delimiter="delimited")
        assert "[ERROR: LM Studio API response missing 'message.content' for page 1]" in md


@pytest.mark.asyncio
async def test_process_page_success():
    """Test successful OCR processing of a single page."""
    processor = OcrProcessor("http://fake", "fake", "test-model", 10)
    
    # Mock successful response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        'natural_text': 'This is extracted text from the page'
    })
    
    with patch('olmocr.pipeline.build_page_query') as mock_build_query, \
         patch.object(processor.client.chat.completions, 'create', return_value=mock_response):
        mock_build_query.return_value = {'model': 'test-model'}
        
        result = await processor.process_page("/fake/path.pdf", 1)
        assert result == "This is extracted text from the page"


@pytest.mark.asyncio
async def test_process_page_none_response():
    """Test handling of None response from API."""
    processor = OcrProcessor("http://fake", "fake", "test-model", 10)
    
    with patch('olmocr.pipeline.build_page_query') as mock_build_query, \
         patch.object(processor.client.chat.completions, 'create', return_value=None):
        mock_build_query.return_value = {'model': 'test-model'}
        
        result = await processor.process_page("/fake/path.pdf", 1)
        assert "ERROR: LM Studio API returned None for page 1" in result


@pytest.mark.asyncio
async def test_process_page_no_choices():
    """Test handling of response without choices."""
    processor = OcrProcessor("http://fake", "fake", "test-model", 10)
    
    mock_response = MagicMock()
    mock_response.choices = []
    
    with patch('olmocr.pipeline.build_page_query') as mock_build_query, \
         patch.object(processor.client.chat.completions, 'create', return_value=mock_response):
        mock_build_query.return_value = {'model': 'test-model'}
        
        result = await processor.process_page("/fake/path.pdf", 1)
        assert "ERROR: LM Studio API response missing 'choices' for page 1" in result


@pytest.mark.asyncio
async def test_process_page_no_message_content():
    """Test handling of response without message.content."""
    processor = OcrProcessor("http://fake", "fake", "test-model", 10)
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    # Remove content attribute
    del mock_response.choices[0].message.content
    
    with patch('olmocr.pipeline.build_page_query') as mock_build_query, \
         patch.object(processor.client.chat.completions, 'create', return_value=mock_response):
        mock_build_query.return_value = {'model': 'test-model'}
        
        result = await processor.process_page("/fake/path.pdf", 1)
        assert "ERROR: LM Studio API response missing 'message.content' for page 1" in result


@pytest.mark.asyncio
async def test_process_page_diagram_classification():
    """Test handling of page classified as diagram with no text."""
    processor = OcrProcessor("http://fake", "fake", "test-model", 10)
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        'natural_text': None,
        'is_diagram': True,
        'primary_language': 'en'
    })
    
    with patch('olmocr.pipeline.build_page_query') as mock_build_query, \
         patch.object(processor.client.chat.completions, 'create', return_value=mock_response):
        mock_build_query.return_value = {'model': 'test-model'}
        
        result = await processor.process_page("/fake/path.pdf", 1)
        assert "Classified as diagram, language: en" in result
        assert "no text extracted" in result


@pytest.mark.asyncio
async def test_process_page_table_classification():
    """Test handling of page classified as table with no text."""
    processor = OcrProcessor("http://fake", "fake", "test-model", 10)
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        'natural_text': None,
        'is_table': True,
        'is_diagram': False
    })
    
    with patch('olmocr.pipeline.build_page_query') as mock_build_query, \
         patch.object(processor.client.chat.completions, 'create', return_value=mock_response):
        mock_build_query.return_value = {'model': 'test-model'}
        
        result = await processor.process_page("/fake/path.pdf", 1)
        assert "Classified as table" in result


@pytest.mark.asyncio
async def test_process_page_missing_natural_text():
    """Test handling of response missing natural_text field."""
    processor = OcrProcessor("http://fake", "fake", "test-model", 10)
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        'some_other_field': 'value'
    })
    
    with patch('olmocr.pipeline.build_page_query') as mock_build_query, \
         patch.object(processor.client.chat.completions, 'create', return_value=mock_response):
        mock_build_query.return_value = {'model': 'test-model'}
        
        result = await processor.process_page("/fake/path.pdf", 1)
        assert "ERROR: LM Studio API response JSON missing 'natural_text' for page 1" in result


@pytest.mark.asyncio
async def test_process_page_api_timeout_retry():
    """Test retry logic on API timeout."""
    processor = OcrProcessor("http://fake", "fake", "test-model", 10)
    
    # First call times out, second succeeds
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        'natural_text': 'Success after retry'
    })
    
    with patch('olmocr.pipeline.build_page_query') as mock_build_query, \
         patch.object(processor.client.chat.completions, 'create', side_effect=[APITimeoutError("Timeout"), mock_response]), \
         patch('time.sleep'):  # Speed up test
        mock_build_query.return_value = {'model': 'test-model'}
        
        result = await processor.process_page("/fake/path.pdf", 1, max_retries=2)
        assert result == "Success after retry"


@pytest.mark.asyncio
async def test_process_page_max_retries_exceeded():
    """Test behavior when max retries are exceeded."""
    processor = OcrProcessor("http://fake", "fake", "test-model", 10)
    
    with patch('olmocr.pipeline.build_page_query') as mock_build_query, \
         patch.object(processor.client.chat.completions, 'create', side_effect=APITimeoutError("Timeout")), \
         patch('time.sleep'):  # Speed up test
        mock_build_query.return_value = {'model': 'test-model'}
        
        result = await processor.process_page("/fake/path.pdf", 1, max_retries=2)
        assert "ERROR: Max retries exceeded for page 1" in result


@pytest.mark.asyncio
async def test_process_page_json_decode_error():
    """Test handling of invalid JSON response."""
    processor = OcrProcessor("http://fake", "fake", "test-model", 10)
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "invalid json content"
    
    with patch('olmocr.pipeline.build_page_query') as mock_build_query, \
         patch.object(processor.client.chat.completions, 'create', return_value=mock_response):
        mock_build_query.return_value = {'model': 'test-model'}
        
        result = await processor.process_page("/fake/path.pdf", 1)
        assert "ERROR: LM Studio API response not valid JSON for page 1" in result


@pytest.mark.asyncio
async def test_process_page_general_exception():
    """Test handling of general exceptions.""" 
    processor = OcrProcessor("http://fake", "fake", "test-model", 10)
    
    with patch('olmocr.pipeline.build_page_query', side_effect=Exception("General error")):
        result = await processor.process_page("/fake/path.pdf", 1)
        assert "ERROR: Exception during OCR page 1" in result and "General error" in result


@pytest.mark.asyncio
async def test_process_pdf_read_error(tmp_path):
    """Test handling of PDF read errors."""
    processor = OcrProcessor("http://fake", "fake", "test-model", 10)
    
    # Create a non-PDF file
    invalid_pdf = tmp_path / "invalid.pdf"
    invalid_pdf.write_text("not a pdf")
    
    result = await processor.process_pdf_to_markdown(str(invalid_pdf))
    assert "ERROR: Failed to read PDF" in result


def test_ocr_pdf_to_markdown_sync():
    """Test the synchronous wrapper function."""
    with patch('asyncio.run') as mock_run:
        mock_run.return_value = "Test markdown content"
        
        result = ocr_pdf_to_markdown_sync(
            "/fake/path.pdf",
            "http://fake",
            "fake_key", 
            "fake_model",
            timeout=60,
            delimiter="delimited"
        )
        
        assert result == "Test markdown content"
        mock_run.assert_called_once()


