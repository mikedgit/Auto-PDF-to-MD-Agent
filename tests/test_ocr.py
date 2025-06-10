import pytest
from unittest.mock import patch, AsyncMock
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


