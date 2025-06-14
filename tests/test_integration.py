import tempfile
from pathlib import Path

import pytest

# Integration test for end-to-end PDF processing pipeline


def create_dummy_pdf(pdf_path):
    # Minimal valid PDF
    with open(pdf_path, "wb") as f:
        f.write(
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000061 00000 n \n0000000116 00000 n \ntrailer\n<< /Root 1 0 R /Size 4 >>\nstartxref\n171\n%%EOF"
        )


@pytest.fixture
def integration_env(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = Path(tmpdir) / "input"
        output_dir = Path(tmpdir) / "output"
        done_dir = Path(tmpdir) / "done"
        input_dir.mkdir()
        output_dir.mkdir()
        done_dir.mkdir()
        monkeypatch.setenv("PDF2MD_INPUT_DIR", str(input_dir))
        monkeypatch.setenv("PDF2MD_OUTPUT_DIR", str(output_dir))
        monkeypatch.setenv("PDF2MD_DONE_DIR", str(done_dir))
        monkeypatch.setenv("PDF2MD_LM_STUDIO_API", "http://localhost:1234/v1")
        monkeypatch.setenv("PDF2MD_LOG_FILE", str(Path(tmpdir) / "service.log"))
        monkeypatch.setenv("PDF2MD_MD_PAGE_DELIMITER", "delimited")
        yield input_dir, output_dir, done_dir


def test_end_to_end_pipeline(integration_env, monkeypatch):
    input_dir, output_dir, done_dir = integration_env
    pdf_path = input_dir / "test.pdf"
    create_dummy_pdf(pdf_path)
    # Patch OCR to avoid real API call
    monkeypatch.setenv("PDF2MD_LM_STUDIO_API_KEY", "dummy-key")
    monkeypatch.setenv("PDF2MD_LM_STUDIO_MODEL", "dummy-model")
    from unittest.mock import AsyncMock, patch

    from src.ocr import OcrProcessor

    with patch.object(
        OcrProcessor,
        "process_pdf_to_markdown",
        new=AsyncMock(return_value="# Dummy Markdown\n\n---\n\nPage 2"),
    ):
        from src.pdf2md_service import on_new_pdf

        on_new_pdf(str(pdf_path))
    # Check output
    md_files = list(output_dir.glob("*.md"))
    assert len(md_files) == 1
    with open(md_files[0]) as f:
        content = f.read()
    assert "Dummy Markdown" in content
    # Check PDF moved
    assert not pdf_path.exists()
    moved_pdfs = list(done_dir.glob("*.pdf"))
    assert len(moved_pdfs) == 1
