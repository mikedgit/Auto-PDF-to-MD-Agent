# Auto PDF to Markdown Agent

## Overview
This project is a Python-based macOS background service that monitors a network folder for new PDF files. When a PDF appears, it uses LM Studio (with a local LLM) to perform optical character recognition (OCR) and converts the content into Markdown format. The Markdown output is saved to a target network directory, and the processed PDF is moved to a 'done' directory. The service is designed to run unattended, survive reboots, and handle multiple PDFs robustly.

## Features
- **Runs as a macOS background service** (LaunchAgent/daemon)
- **Monitors a network folder** for incoming PDFs
- **Invokes LM Studio** and a local model for OCR
- **Outputs Markdown** to a specified directory
- **Moves processed PDFs** to a 'done' directory
- **Handles multiple PDFs** and processes them sequentially
- **Robust error handling and logging**
- **Automatic startup on reboot**
- **Tested with PyTest**
- **Follows Simon Willison’s "perfect commit" principles**
- **GitHub issues managed via `gh` CLI**

## Requirements
- Python 3.9+
- macOS
- Access to LM Studio and a compatible OCR model
- Access to network share directories for input, output, and done folders
- `pytest` for testing
- `gh` CLI for GitHub issue management

## Setup
1. **Clone this repository locally.**
2. **Create and activate a Python virtual environment:**
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
4. **Configure environment variables** for the following required settings (can be set in a `.env` file):
   - `INPUT_DIR`: Path to the input directory to monitor for PDFs
   - `OUTPUT_DIR`: Path to the output directory for markdown files
   - `DONE_DIR`: Path to the directory where processed PDFs are moved
   - `LM_STUDIO_API`: URL for LM Studio API (e.g., `http://localhost:1234`)
   - `LOG_FILE`: (optional) Path for the log file (default: `app.log`)

   You may copy `.env.example` to `.env` and edit as needed. The app will automatically load `.env` if `python-dotenv` is installed.
5. **Set up LM Studio** and ensure it is accessible from the service.
6. **Run tests:**
   ```sh
   pytest
   ```

## Usage
- The service will run in the background, monitoring the configured folder.
- Place a PDF in the input directory to trigger processing.
- Markdown files will appear in the output directory; processed PDFs will be moved to the done directory.

## Logging
- All activity and errors are logged to a file for troubleshooting and auditing.

## Development
- Use PyTest for all tests.
- Follow the "perfect commit" process: small, focused, well-tested commits with clear messages.
- Use the `gh` CLI to manage issues and track progress.

## Roadmap
- [ ] Folder monitoring logic
- [ ] LM Studio OCR integration
- [ ] Markdown output
- [ ] PDF move/cleanup
- [ ] Logging and error handling
- [ ] macOS service integration
- [ ] Robust testing

---

*For more details on the perfect commit, see [Simon Willison’s blog](https://simonwillison.net/2020/Oct/9/perfect-commit/).*
