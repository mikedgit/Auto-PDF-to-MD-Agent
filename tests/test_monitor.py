import os
import tempfile
import shutil
import time
import threading
import pytest
from pathlib import Path

# We'll define a stub for the monitor function to test interface and basic logic
# Actual implementation will live in src/monitor.py

def fake_monitor_folder(input_dir, callback, stop_event, poll_interval=0.1):
    """Fake monitor that calls callback for each new PDF in the folder."""
    seen = set()
    while not stop_event.is_set():
        for f in Path(input_dir).glob("*.pdf"):
            if f not in seen:
                seen.add(f)
                callback(str(f))
        time.sleep(poll_interval)


def test_monitor_detects_new_pdf(tmp_path):
    """Test that the monitor detects a new PDF file and calls the callback."""
    detected = []
    stop_event = threading.Event()
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    def on_new_pdf(path):
        detected.append(path)
        stop_event.set()

    t = threading.Thread(target=fake_monitor_folder, args=(input_dir, on_new_pdf, stop_event))
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

    t = threading.Thread(target=fake_monitor_folder, args=(input_dir, on_new_pdf, stop_event))
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

    t = threading.Thread(target=fake_monitor_folder, args=(input_dir, on_new_pdf, stop_event))
    t.start()

    pdf1 = input_dir / "one.pdf"
    pdf2 = input_dir / "two.pdf"
    pdf1.write_bytes(b"%PDF-1.4 one")
    pdf2.write_bytes(b"%PDF-1.4 two")

    t.join(timeout=2)
    stop_event.set()

    assert set(detected) == {str(pdf1), str(pdf2)}
