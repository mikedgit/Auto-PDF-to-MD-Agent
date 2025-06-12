from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import threading
import time
import logging

logger = logging.getLogger("pdf2md.monitor")

class PDFHandler(FileSystemEventHandler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.seen = set()
        self.lock = threading.Lock()

    def on_deleted(self, event):
        if not event.is_directory and event.src_path.endswith('.pdf'):
            path = Path(event.src_path)
            with self.lock:
                self.seen.discard(path)  # Remove from seen set when deleted
            logger.warning(f"PDF deleted before processing: {path}")

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.pdf'):
            path = Path(event.src_path)
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

    def on_moved(self, event):
        # Handle renames/moves into the directory as well
        if not event.is_directory and event.dest_path.endswith('.pdf'):
            path = Path(event.dest_path)
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
    
    def clear_seen_file(self, path):
        """Remove a file from the seen set after successful processing"""
        with self.lock:
            self.seen.discard(Path(path))

def monitor_folder(input_dir, callback, stop_event=None, poll_interval=1.0):
    """
    Watches input_dir for new PDF files and calls callback(path) for each new file.
    If stop_event is provided, stops when set.
    """
    input_dir = Path(input_dir)
    
    # Store handler reference for use in callback
    handler_ref = {'handler': None}
    
    # Create a wrapper callback that can optionally pass the handler
    def wrapped_callback(path):
        import inspect
        sig = inspect.signature(callback)
        if len(sig.parameters) >= 2:
            # New signature: callback(path, handler)
            callback(path, handler_ref['handler'])
        else:
            # Old signature: callback(path)
            callback(path)
    
    handler = PDFHandler(wrapped_callback)
    handler_ref['handler'] = handler
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
