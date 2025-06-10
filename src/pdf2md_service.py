from src.config import load_config
from src.monitor import monitor_folder
from src.ocr import ocr_pdf_to_markdown_sync
import threading
from pathlib import Path
import shutil
import os
import time
import logging

# Setup logging
cfg_for_logging = load_config()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(cfg_for_logging.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("pdf2md.service")

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
            logger.error(f"File disappeared during wait: {path}")
            return False
        except Exception as e:
            logger.error(f"Error stat'ing {path}: {e}")
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
    logger.error(f"Timed out waiting for file to stabilize: {path}")
    return False

def on_new_pdf(path):
    cfg = load_config()
    pdf_path = Path(path)
    output_path = Path(cfg.OUTPUT_DIR) / (pdf_path.stem + ".md")
    logger.info(f"Waiting for file to be stable: {pdf_path}")
    if not wait_for_file_stable(pdf_path):
        logger.error(f"File did not stabilize in time or was deleted: {pdf_path}")
        return
    logger.info(f"Processing PDF to markdown: {pdf_path} -> {output_path}")
    try:
        if not pdf_path.exists():
            logger.error(f"File was deleted before processing: {pdf_path}")
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
        logger.info(f"Wrote markdown to {output_path}")
        # Move PDF to DONE_DIR
        done_path = Path(cfg.DONE_DIR) / pdf_path.name
        try:
            shutil.move(str(pdf_path), str(done_path))
            logger.info(f"Moved PDF to {done_path}")
        except FileNotFoundError:
            logger.error(f"PDF was deleted before it could be moved: {pdf_path}")
        except Exception as e:
            logger.error(f"Error moving PDF to done dir: {e}")
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {e}")

def main():
    cfg = load_config()
    logger.info(f"Monitoring: {cfg.INPUT_DIR}")
    stop_event = threading.Event()
    try:
        monitor_folder(cfg.INPUT_DIR, on_new_pdf, stop_event)
    except KeyboardInterrupt:
        logger.info("Stopping monitor...")
        stop_event.set()

if __name__ == "__main__":
    main()
