import inspect
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

logger = logging.getLogger("pdf2md.monitor")


class PDFHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[..., Any]) -> None:
        super().__init__()
        self.callback = callback
        self.seen: set[Path] = set()
        self.lock = threading.Lock()

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory and str(event.src_path).endswith(".pdf"):
            path = Path(str(event.src_path))
            with self.lock:
                self.seen.discard(path)  # Remove from seen set when deleted
            logger.warning(f"PDF deleted before processing: {path}")

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and str(event.src_path).endswith(".pdf"):
            path = Path(str(event.src_path))
            with self.lock:
                if path not in self.seen:
                    self.seen.add(path)
                    logger.info(f"Detected new PDF: {path}")
                    try:
                        self.callback(str(path))
                    except Exception as e:
                        logger.error(f"Error in callback for new PDF {path}: {e}")
                        # Remove from seen on callback error so it can be retried
                        self.seen.discard(path)

    def on_moved(self, event: FileSystemEvent) -> None:
        # Handle renames/moves into the directory as well
        if not event.is_directory and str(event.dest_path).endswith(".pdf"):
            path = Path(str(event.dest_path))
            with self.lock:
                if path not in self.seen:
                    self.seen.add(path)
                    logger.info(f"Detected moved PDF: {path}")
                    try:
                        self.callback(str(path))
                    except Exception as e:
                        logger.error(f"Error in callback for moved PDF {path}: {e}")
                        # Remove from seen on callback error so it can be retried
                        self.seen.discard(path)

    def clear_seen_file(self, path: str) -> None:
        """Remove a file from the seen set after successful processing"""
        with self.lock:
            self.seen.discard(Path(path))


def _process_existing_pdfs(
    input_dir: Path, handler: PDFHandler, callback: Callable[[str], None]
) -> None:
    """Scan input directory for existing PDF files and queue them for processing."""
    import threading
    try:
        existing_pdfs = list(input_dir.glob("*.pdf"))
        if existing_pdfs:
            logger.info(f"Found {len(existing_pdfs)} existing PDF files to process")
            for pdf_path in existing_pdfs:
                if pdf_path.is_file():
                    with handler.lock:
                        if pdf_path not in handler.seen:
                            handler.seen.add(pdf_path)
                            logger.info(f"Queuing existing PDF for processing: {pdf_path}")
                            # Process each file in a separate thread to avoid blocking
                            def process_file(file_path: str, path_obj: Path) -> None:
                                try:
                                    callback(file_path)
                                except Exception as e:
                                    logger.error(f"Error processing existing PDF {file_path}: {e}")
                                    # Remove from seen on callback error so it can be retried
                                    with handler.lock:
                                        handler.seen.discard(path_obj)
                            
                            thread = threading.Thread(target=process_file, args=(str(pdf_path), pdf_path))
                            thread.daemon = True
                            thread.start()
        else:
            logger.info("No existing PDF files found in input directory")
    except Exception as e:
        logger.error(f"Error scanning for existing PDF files: {e}")


def monitor_folder(
    input_dir: str | Path,
    callback: Callable[..., Any],
    stop_event: threading.Event | None = None,
    poll_interval: float = 1.0,
) -> None:
    """
    Watches input_dir for new PDF files and calls callback(path) for each new file.
    Also processes any existing PDF files in the directory on startup.
    If stop_event is provided, stops when set.
    """
    input_dir = Path(input_dir)

    # Store handler reference for use in callback
    handler_ref: dict[str, PDFHandler | None] = {"handler": None}

    # Create a wrapper callback that can optionally pass the handler
    def wrapped_callback(path: str) -> None:
        sig = inspect.signature(callback)
        if len(sig.parameters) >= 2:
            # New signature: callback(path, handler)
            callback(path, handler_ref["handler"])
        else:
            # Old signature: callback(path)
            callback(path)

    handler = PDFHandler(wrapped_callback)
    handler_ref["handler"] = handler
    
    # Process existing PDF files before starting file system monitoring
    _process_existing_pdfs(input_dir, handler, wrapped_callback)
    
    observer = Observer()
    observer.schedule(handler, str(input_dir), recursive=False)
    observer.start()
    logger.info(f"Started monitoring folder: {input_dir}")
    try:
        while True:
            if stop_event and stop_event.is_set():
                logger.info("Stop event set, stopping folder monitor.")
                break
            time.sleep(poll_interval)
    except Exception as e:
        logger.error(f"Error in folder monitoring loop: {e}")
        raise
    finally:
        observer.stop()
        observer.join()
        logger.info(f"Stopped monitoring folder: {input_dir}")
