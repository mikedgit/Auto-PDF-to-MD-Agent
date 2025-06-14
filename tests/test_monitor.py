import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from src.monitor import PDFHandler, monitor_folder


def test_monitor_detects_new_pdf(tmp_path):
    """Test that the monitor detects a new PDF file and calls the callback."""
    detected = []
    stop_event = threading.Event()
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    def on_new_pdf(path):
        detected.append(path)
        stop_event.set()

    t = threading.Thread(
        target=monitor_folder, args=(input_dir, on_new_pdf, stop_event, 0.1)
    )
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

    t = threading.Thread(
        target=monitor_folder, args=(input_dir, on_new_pdf, stop_event, 0.1)
    )
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

    t = threading.Thread(
        target=monitor_folder, args=(input_dir, on_new_pdf, stop_event, 0.1)
    )
    t.start()

    pdf1 = input_dir / "one.pdf"
    pdf2 = input_dir / "two.pdf"
    pdf1.write_bytes(b"%PDF-1.4 one")
    pdf2.write_bytes(b"%PDF-1.4 two")

    t.join(timeout=2)
    stop_event.set()

    assert set(detected) == {str(pdf1), str(pdf2)}


def test_pdf_handler_on_deleted():
    """Test PDFHandler on_deleted method."""
    callback = MagicMock()
    handler = PDFHandler(callback)

    # Add a file to seen set first
    test_path = Path("/test/file.pdf")
    handler.seen.add(test_path)

    # Create mock event
    mock_event = MagicMock()
    mock_event.is_directory = False
    mock_event.src_path = str(test_path)

    handler.on_deleted(mock_event)

    # File should be removed from seen set
    assert test_path not in handler.seen


def test_pdf_handler_on_deleted_ignores_directory():
    """Test PDFHandler ignores directory deletion events."""
    callback = MagicMock()
    handler = PDFHandler(callback)

    # Create mock directory event
    mock_event = MagicMock()
    mock_event.is_directory = True
    mock_event.src_path = "/test/directory"

    handler.on_deleted(mock_event)

    # No effect should occur
    callback.assert_not_called()


def test_pdf_handler_on_deleted_ignores_non_pdf():
    """Test PDFHandler ignores non-PDF file deletions."""
    callback = MagicMock()
    handler = PDFHandler(callback)

    # Create mock non-PDF event
    mock_event = MagicMock()
    mock_event.is_directory = False
    mock_event.src_path = "/test/file.txt"

    handler.on_deleted(mock_event)

    # No effect should occur
    callback.assert_not_called()


def test_pdf_handler_on_created_callback_exception():
    """Test PDFHandler handles callback exceptions on creation."""
    callback = MagicMock(side_effect=Exception("Callback error"))
    handler = PDFHandler(callback)

    # Create mock event
    mock_event = MagicMock()
    mock_event.is_directory = False
    mock_event.src_path = "/test/file.pdf"

    handler.on_created(mock_event)

    # File should be removed from seen set after error
    test_path = Path("/test/file.pdf")
    assert test_path not in handler.seen


def test_pdf_handler_on_created_already_seen():
    """Test PDFHandler doesn't reprocess already seen files."""
    callback = MagicMock()
    handler = PDFHandler(callback)

    # Add file to seen set first
    test_path = Path("/test/file.pdf")
    handler.seen.add(test_path)

    # Create mock event
    mock_event = MagicMock()
    mock_event.is_directory = False
    mock_event.src_path = str(test_path)

    handler.on_created(mock_event)

    # Callback should not be called
    callback.assert_not_called()


def test_pdf_handler_on_moved():
    """Test PDFHandler on_moved method."""
    callback = MagicMock()
    handler = PDFHandler(callback)

    # Create mock event
    mock_event = MagicMock()
    mock_event.is_directory = False
    mock_event.dest_path = "/test/moved.pdf"

    handler.on_moved(mock_event)

    # Callback should be called
    callback.assert_called_once_with("/test/moved.pdf")

    # File should be in seen set
    assert Path("/test/moved.pdf") in handler.seen


def test_pdf_handler_on_moved_callback_exception():
    """Test PDFHandler handles callback exceptions on move."""
    callback = MagicMock(side_effect=Exception("Callback error"))
    handler = PDFHandler(callback)

    # Create mock event
    mock_event = MagicMock()
    mock_event.is_directory = False
    mock_event.dest_path = "/test/moved.pdf"

    handler.on_moved(mock_event)

    # File should be removed from seen set after error
    test_path = Path("/test/moved.pdf")
    assert test_path not in handler.seen


def test_pdf_handler_on_moved_already_seen():
    """Test PDFHandler doesn't reprocess already seen moved files."""
    callback = MagicMock()
    handler = PDFHandler(callback)

    # Add file to seen set first
    test_path = Path("/test/moved.pdf")
    handler.seen.add(test_path)

    # Create mock event
    mock_event = MagicMock()
    mock_event.is_directory = False
    mock_event.dest_path = str(test_path)

    handler.on_moved(mock_event)

    # Callback should not be called
    callback.assert_not_called()


def test_pdf_handler_on_moved_ignores_directory():
    """Test PDFHandler ignores directory move events."""
    callback = MagicMock()
    handler = PDFHandler(callback)

    # Create mock directory event
    mock_event = MagicMock()
    mock_event.is_directory = True
    mock_event.dest_path = "/test/directory"

    handler.on_moved(mock_event)

    # No effect should occur
    callback.assert_not_called()


def test_pdf_handler_on_moved_ignores_non_pdf():
    """Test PDFHandler ignores non-PDF file moves."""
    callback = MagicMock()
    handler = PDFHandler(callback)

    # Create mock non-PDF event
    mock_event = MagicMock()
    mock_event.is_directory = False
    mock_event.dest_path = "/test/file.txt"

    handler.on_moved(mock_event)

    # No effect should occur
    callback.assert_not_called()


def test_pdf_handler_clear_seen_file():
    """Test PDFHandler clear_seen_file method."""
    callback = MagicMock()
    handler = PDFHandler(callback)

    # Add file to seen set
    test_path = "/test/file.pdf"
    handler.seen.add(Path(test_path))

    # Clear the file
    handler.clear_seen_file(test_path)

    # File should be removed from seen set
    assert Path(test_path) not in handler.seen


def test_monitor_folder_with_handler_callback():
    """Test monitor_folder passes handler to callback when using new signature."""
    detected = []
    stop_event = threading.Event()

    def callback_with_handler(path, handler=None):
        detected.append((path, handler is not None))
        stop_event.set()

    with (
        patch("src.monitor.Observer") as mock_observer_class,
        patch("src.monitor._process_existing_pdfs"),
    ):
        mock_observer = MagicMock()
        mock_observer_class.return_value = mock_observer

        # Start monitoring in separate thread
        monitor_thread = threading.Thread(
            target=monitor_folder,
            args=("/fake/path", callback_with_handler, stop_event, 0.1),
        )
        monitor_thread.start()

        # Wait for monitoring to start
        time.sleep(0.2)

        # Simulate file creation by calling handler directly
        # Get the handler from the observer.schedule call
        watch_call = mock_observer.schedule.call_args
        handler = watch_call[0][0]  # First argument is the handler

        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = "/fake/path/test.pdf"

        handler.on_created(mock_event)

        monitor_thread.join(timeout=1)
        stop_event.set()

        # Check that handler was passed to callback
        assert len(detected) == 1
        assert detected[0][1] is True  # Handler was passed


def test_process_existing_pdfs():
    """Test _process_existing_pdfs function queues existing PDF files for processing."""
    import time

    from src.monitor import _process_existing_pdfs

    detected = []

    def callback(path):
        detected.append(path)

    handler = PDFHandler(callback)

    with patch("pathlib.Path.glob") as mock_glob:
        # Create mock Path objects
        pdf1_path = MagicMock(spec=Path)
        pdf1_path.__str__.return_value = "/fake/path/file1.pdf"
        pdf1_path.is_file.return_value = True

        pdf2_path = MagicMock(spec=Path)
        pdf2_path.__str__.return_value = "/fake/path/file2.pdf"
        pdf2_path.is_file.return_value = True

        mock_glob.return_value = [pdf1_path, pdf2_path]

        input_dir = Path("/fake/path")
        _process_existing_pdfs(input_dir, handler, callback)

        # Give threads a moment to start processing
        time.sleep(0.1)

        # Should have processed both files (eventually)
        assert len(detected) == 2
        assert "/fake/path/file1.pdf" in detected
        assert "/fake/path/file2.pdf" in detected

        # Files should be in seen set
        assert pdf1_path in handler.seen
        assert pdf2_path in handler.seen


def test_process_existing_pdfs_no_files():
    """Test _process_existing_pdfs when no PDF files exist."""
    from src.monitor import _process_existing_pdfs

    detected = []

    def callback(path):
        detected.append(path)

    handler = PDFHandler(callback)

    with patch("pathlib.Path.glob") as mock_glob:
        mock_glob.return_value = []

        input_dir = Path("/fake/path")
        _process_existing_pdfs(input_dir, handler, callback)

        # Should have processed no files
        assert len(detected) == 0
        assert len(handler.seen) == 0


def test_process_existing_pdfs_callback_error():
    """Test _process_existing_pdfs handles callback errors gracefully."""
    import time

    from src.monitor import _process_existing_pdfs

    def error_callback(path):
        raise Exception("Callback error")

    handler = PDFHandler(error_callback)

    with patch("pathlib.Path.glob") as mock_glob:
        pdf_path = MagicMock(spec=Path)
        pdf_path.__str__.return_value = "/fake/path/error.pdf"
        pdf_path.is_file.return_value = True

        mock_glob.return_value = [pdf_path]

        input_dir = Path("/fake/path")
        # Should not raise exception
        _process_existing_pdfs(input_dir, handler, error_callback)

        # Give thread time to process and handle error
        time.sleep(0.2)

        # File should not be in seen set after error (error handling happens in thread)
        assert pdf_path not in handler.seen


def test_monitor_folder_old_callback_signature():
    """Test monitor_folder works with old callback signature (no handler param)."""
    detected = []
    stop_event = threading.Event()

    def old_callback(path):
        detected.append(path)
        stop_event.set()

    with (
        patch("src.monitor.Observer") as mock_observer_class,
        patch("src.monitor._process_existing_pdfs"),
    ):
        mock_observer = MagicMock()
        mock_observer_class.return_value = mock_observer

        # Start monitoring in separate thread
        monitor_thread = threading.Thread(
            target=monitor_folder, args=("/fake/path", old_callback, stop_event, 0.1)
        )
        monitor_thread.start()

        # Wait for monitoring to start
        time.sleep(0.2)

        # Simulate file creation
        watch_call = mock_observer.schedule.call_args
        handler = watch_call[0][0]

        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = "/fake/path/test.pdf"

        handler.on_created(mock_event)

        monitor_thread.join(timeout=1)
        stop_event.set()

        # Check that callback was called without handler
        assert detected == ["/fake/path/test.pdf"]
