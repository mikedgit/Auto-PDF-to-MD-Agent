import os
import tempfile
import shutil
import time
import threading
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from src.monitor import monitor_folder


def test_monitor_detects_new_pdf(tmp_path):
    """Test that the monitor detects a new PDF file and calls the callback."""
    detected = []
    stop_event = threading.Event()
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    def on_new_pdf(path):
        detected.append(path)
        stop_event.set()

    t = threading.Thread(target=monitor_folder, args=(input_dir, on_new_pdf, stop_event, 0.1))
    t.start()

    # Simulate adding a PDF
    pdf_path = input_dir / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test content")

    t.join(timeout=2)
    stop_event.set()

    assert detected == [str(pdf_path)]


def test_monitor_ignores_non_pdf(tmp_path):
    """Test that the monitor ignores non-PDF files."""
    detected = []
    stop_event = threading.Event()
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    def on_new_pdf(path):
        detected.append(path)
        stop_event.set()

    t = threading.Thread(target=monitor_folder, args=(input_dir, on_new_pdf, stop_event, 0.1))
    t.start()

    # Add a non-PDF file
    txt_path = input_dir / "not_a_pdf.txt"
    txt_path.write_text("hello")
    time.sleep(0.2)
    stop_event.set()
    t.join(timeout=2)

    assert detected == []


def test_monitor_detects_multiple_pdfs(tmp_path):
    """Test that the monitor detects multiple PDFs."""
    detected = []
    stop_event = threading.Event()
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    def on_new_pdf(path):
        detected.append(path)
        if len(detected) == 2:
            stop_event.set()

    t = threading.Thread(target=monitor_folder, args=(input_dir, on_new_pdf, stop_event, 0.1))
    t.start()

    pdf1 = input_dir / "one.pdf"
    pdf2 = input_dir / "two.pdf"
    pdf1.write_bytes(b"%PDF-1.4 one")
    pdf2.write_bytes(b"%PDF-1.4 two")

    t.join(timeout=2)
    stop_event.set()

    assert set(detected) == {str(pdf1), str(pdf2)}
