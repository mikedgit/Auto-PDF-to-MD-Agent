from src.config import load_config
from src.monitor import monitor_folder
import threading

def on_new_pdf(path):
    print(f"Detected new PDF: {path}")

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
