import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.pdf2md_service import main, on_new_pdf, wait_for_file_stable


def test_wait_for_file_stable_success(tmp_path):
    """Test successful file stability detection."""
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"test content")

    result = wait_for_file_stable(test_file, stable_secs=1, max_wait=5)
    assert result is True


def test_wait_for_file_stable_file_not_found(tmp_path):
    """Test handling of non-existent file."""
    non_existent = tmp_path / "does_not_exist.pdf"

    result = wait_for_file_stable(non_existent, stable_secs=1, max_wait=2)
    assert result is False


def test_wait_for_file_stable_timeout(tmp_path):
    """Test timeout when file doesn't stabilize."""
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"initial")

    def modify_file():
        # Continuously modify file during wait
        for i in range(10):
            time.sleep(0.5)
            test_file.write_bytes(b"content " + str(i).encode())

    import threading

    modifier = threading.Thread(target=modify_file)
    modifier.daemon = True
    modifier.start()

    result = wait_for_file_stable(test_file, stable_secs=1, max_wait=2)
    assert result is False


def test_wait_for_file_stable_stat_error(tmp_path):
    """Test handling of stat errors."""
    # Create a file that will cause stat errors
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"test")

    with patch("pathlib.Path.stat", side_effect=PermissionError("Permission denied")):
        result = wait_for_file_stable(test_file, stable_secs=1, max_wait=2)
        assert result is False


@pytest.fixture
def service_env(monkeypatch):
    """Set up environment for service tests."""
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
        monkeypatch.setenv("PDF2MD_LM_STUDIO_API_KEY", "test-key")
        monkeypatch.setenv("PDF2MD_LM_STUDIO_MODEL", "test-model")
        monkeypatch.setenv("PDF2MD_LOG_FILE", str(Path(tmpdir) / "service.log"))
        monkeypatch.setenv("PDF2MD_MD_PAGE_DELIMITER", "delimited")

        yield input_dir, output_dir, done_dir


def test_on_new_pdf_file_not_stable(service_env):
    """Test handling when file doesn't stabilize."""
    input_dir, output_dir, done_dir = service_env
    pdf_path = input_dir / "unstable.pdf"
    pdf_path.write_bytes(b"test content")

    with patch("src.pdf2md_service.wait_for_file_stable", return_value=False):
        on_new_pdf(str(pdf_path))

        # Should not create any markdown files
        md_files = list(output_dir.glob("*.md"))
        assert len(md_files) == 0


def test_on_new_pdf_file_deleted_before_processing(service_env):
    """Test handling when file is deleted before processing."""
    input_dir, output_dir, done_dir = service_env
    pdf_path = input_dir / "will_be_deleted.pdf"
    pdf_path.write_bytes(b"test content")

    with (
        patch("src.pdf2md_service.wait_for_file_stable", return_value=True),
        patch("pathlib.Path.exists", return_value=False),
    ):
        on_new_pdf(str(pdf_path))

        # Should not create any markdown files
        md_files = list(output_dir.glob("*.md"))
        assert len(md_files) == 0


def test_on_new_pdf_success(service_env):
    """Test successful PDF processing."""
    input_dir, output_dir, done_dir = service_env
    pdf_path = input_dir / "success.pdf"
    pdf_path.write_bytes(b"test content")

    with (
        patch("src.pdf2md_service.wait_for_file_stable", return_value=True),
        patch(
            "src.pdf2md_service.ocr_pdf_to_markdown_sync",
            return_value="# Test Markdown",
        ),
    ):
        on_new_pdf(str(pdf_path))

        # Check markdown was created
        md_files = list(output_dir.glob("*.md"))
        assert len(md_files) == 1
        assert md_files[0].read_text() == "# Test Markdown"

        # Check PDF was moved to done directory
        done_files = list(done_dir.glob("*.pdf"))
        assert len(done_files) == 1


def test_on_new_pdf_move_error_file_not_found(service_env):
    """Test handling when PDF is deleted before move."""
    input_dir, output_dir, done_dir = service_env
    pdf_path = input_dir / "will_disappear.pdf"
    pdf_path.write_bytes(b"test content")

    with (
        patch("src.pdf2md_service.wait_for_file_stable", return_value=True),
        patch(
            "src.pdf2md_service.ocr_pdf_to_markdown_sync",
            return_value="# Test Markdown",
        ),
        patch("shutil.move", side_effect=FileNotFoundError("File not found")),
    ):
        on_new_pdf(str(pdf_path))

        # Markdown should still be created
        md_files = list(output_dir.glob("*.md"))
        assert len(md_files) == 1


def test_on_new_pdf_move_error_general_exception(service_env):
    """Test handling of general move errors."""
    input_dir, output_dir, done_dir = service_env
    pdf_path = input_dir / "move_error.pdf"
    pdf_path.write_bytes(b"test content")

    with (
        patch("src.pdf2md_service.wait_for_file_stable", return_value=True),
        patch(
            "src.pdf2md_service.ocr_pdf_to_markdown_sync",
            return_value="# Test Markdown",
        ),
        patch("shutil.move", side_effect=PermissionError("Permission denied")),
    ):
        on_new_pdf(str(pdf_path))

        # Markdown should still be created
        md_files = list(output_dir.glob("*.md"))
        assert len(md_files) == 1


def test_on_new_pdf_processing_exception(service_env):
    """Test handling of general processing exceptions."""
    input_dir, output_dir, done_dir = service_env
    pdf_path = input_dir / "exception.pdf"
    pdf_path.write_bytes(b"test content")

    with (
        patch("src.pdf2md_service.wait_for_file_stable", return_value=True),
        patch(
            "src.pdf2md_service.ocr_pdf_to_markdown_sync",
            side_effect=Exception("Processing error"),
        ),
    ):
        on_new_pdf(str(pdf_path))

        # Should not create any markdown files
        md_files = list(output_dir.glob("*.md"))
        assert len(md_files) == 0


def test_on_new_pdf_with_handler(service_env):
    """Test on_new_pdf with handler for clearing seen files."""
    input_dir, output_dir, done_dir = service_env
    pdf_path = input_dir / "with_handler.pdf"
    pdf_path.write_bytes(b"test content")

    mock_handler = MagicMock()

    with (
        patch("src.pdf2md_service.wait_for_file_stable", return_value=True),
        patch(
            "src.pdf2md_service.ocr_pdf_to_markdown_sync",
            return_value="# Test Markdown",
        ),
    ):
        on_new_pdf(str(pdf_path), handler=mock_handler)

        # Handler should be called to clear seen file
        mock_handler.clear_seen_file.assert_called_once_with(str(pdf_path))


def test_main_healthcheck():
    """Test main function with healthcheck argument."""
    with patch("sys.argv", ["pdf2md_service.py", "--healthcheck"]):
        # Should print OK and return (not exit)
        main()  # This should complete without raising SystemExit


def test_main_normal_run(service_env):
    """Test main function normal execution."""
    input_dir, output_dir, done_dir = service_env

    with (
        patch("sys.argv", ["pdf2md_service.py"]),
        patch("src.pdf2md_service.monitor_folder") as mock_monitor,
        patch("threading.Event"),
    ):
        # Mock the monitor to exit immediately
        def mock_monitor_func(*args):
            args[2].set()  # Set the stop event

        mock_monitor.side_effect = mock_monitor_func

        main()

        # Monitor should have been called
        mock_monitor.assert_called_once()


def test_main_keyboard_interrupt(service_env):
    """Test main function handling KeyboardInterrupt."""
    input_dir, output_dir, done_dir = service_env

    with (
        patch("sys.argv", ["pdf2md_service.py"]),
        patch("src.pdf2md_service.monitor_folder", side_effect=KeyboardInterrupt()),
    ):
        # Should exit gracefully
        main()
