from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import threading
import time
import logging

class PDFHandler(FileSystemEventHandler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.seen = set()

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.pdf'):
            path = Path(event.src_path)
            if path not in self.seen:
                self.seen.add(path)
                self.callback(str(path))

    def on_moved(self, event):
        # Handle renames/moves into the directory as well
        if not event.is_directory and event.dest_path.endswith('.pdf'):
            path = Path(event.dest_path)
            if path not in self.seen:
                self.seen.add(path)
                self.callback(str(path))

def monitor_folder(input_dir, callback, stop_event=None, poll_interval=1.0):
    """
    Watches input_dir for new PDF files and calls callback(path) for each new file.
    If stop_event is provided, stops when set.
    """
    input_dir = Path(input_dir)
    handler = PDFHandler(callback)
    observer = Observer()
    observer.schedule(handler, str(input_dir), recursive=False)
    observer.start()
    try:
        while True:
            if stop_event and stop_event.is_set():
                break
            time.sleep(poll_interval)
    finally:
        observer.stop()
        observer.join()
