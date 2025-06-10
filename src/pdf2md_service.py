from src.config import load_config
from src.monitor import monitor_folder
from src.ocr import ocr_pdf_to_markdown_sync
import threading
from pathlib import Path
import shutil
import os

import time

def wait_for_file_stable(path, stable_secs=2, max_wait=300):
    """Wait until file size is unchanged for stable_secs and file is non-empty. Timeout after max_wait (seconds)."""
    path = Path(path)
    last_size = -1
    stable_time = 0
    waited = 0
    while waited < max_wait:
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            # File was deleted during wait
            print(f"File disappeared during wait: {path}")
            return False
        except Exception as e:
            print(f"Error stat'ing {path}: {e}")
            return False
        if size > 0 and size == last_size:
            stable_time += 1
            if stable_time >= stable_secs:
                return True
        else:
            stable_time = 0
        last_size = size
        time.sleep(1)
        waited += 1
    print(f"Timed out waiting for file to stabilize: {path}")
    return False

def on_new_pdf(path):
    cfg = load_config()
    pdf_path = Path(path)
    output_path = Path(cfg.OUTPUT_DIR) / (pdf_path.stem + ".md")
    print(f"Waiting for file to be stable: {pdf_path}")
    if not wait_for_file_stable(pdf_path):
        print(f"File did not stabilize in time or was deleted: {pdf_path}")
        return
    print(f"Processing PDF to markdown: {pdf_path} -> {output_path}")
    try:
        if not pdf_path.exists():
            print(f"File was deleted before processing: {pdf_path}")
            return
        md = ocr_pdf_to_markdown_sync(
            str(pdf_path),
            base_url=cfg.LM_STUDIO_API,
            api_key="lm-studio",  # Default for LM Studio
            model_name="allenai_olmocr-7b-0225-preview",  # Or make configurable
            timeout=120,
            delimiter=cfg.MD_PAGE_DELIMITER,
        )
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Wrote markdown to {output_path}")
        # Move PDF to DONE_DIR
        done_path = Path(cfg.DONE_DIR) / pdf_path.name
        try:
            shutil.move(str(pdf_path), str(done_path))
            print(f"Moved PDF to {done_path}")
        except FileNotFoundError:
            print(f"PDF was deleted before it could be moved: {pdf_path}")
        except Exception as e:
            print(f"Error moving PDF to done dir: {e}")
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")

def main():
    cfg = load_config()
    print(f"Monitoring: {cfg.INPUT_DIR}")
    stop_event = threading.Event()
    try:
        monitor_folder(cfg.INPUT_DIR, on_new_pdf, stop_event)
    except KeyboardInterrupt:
        print("Stopping monitor...")
        stop_event.set()

if __name__ == "__main__":
    main()
