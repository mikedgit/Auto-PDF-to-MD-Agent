# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Architecture

This is a Python-based macOS background service that converts PDFs to Markdown using OCR. The system consists of:

- **Monitor System** (`src/monitor.py`): Uses `watchdog` to monitor input directories for new PDF files
- **OCR Engine** (`src/ocr.py`): Integrates with LM Studio API using the `allenai/olmocr-7b-0225-preview` model via OpenAI client
- **Service Controller** (`src/pdf2md_service.py`): Main orchestrator that coordinates file processing, stability checks, and cleanup
- **Configuration** (`src/config.py`): Environment-based configuration with `.env` file support

## Key Technical Details

- **File Processing Flow**: PDF detected → stability check → OCR via LM Studio → Markdown output → move to done directory
- **Async OCR**: Pages are processed asynchronously with retry logic for transient API errors
- **File Stability**: Implements `wait_for_file_stable()` to ensure files are fully written before processing
- **Error Handling**: Comprehensive logging with both file and console output; graceful degradation on API failures

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_ocr.py

# Run integration tests
pytest tests/test_integration.py

# Run with verbose output
pytest -v
```

### Running the Service
```bash
# Manual execution (requires activated venv)
source venv/bin/activate
python -m src.pdf2md_service

# Or directly
python src/pdf2md_service.py

# Healthcheck
python src/pdf2md_service.py --healthcheck
```

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your paths and LM Studio settings
```

## Required Environment Variables

All configuration is environment-based. Required variables (see `.env.example`):
- `PDF2MD_INPUT_DIR`: Directory to monitor for PDFs
- `PDF2MD_OUTPUT_DIR`: Directory for markdown output
- `PDF2MD_DONE_DIR`: Directory for processed PDFs
- `PDF2MD_LM_STUDIO_API`: LM Studio API URL (usually `http://localhost:1234`)

Optional:
- `PDF2MD_LM_STUDIO_MODEL`: Model name (default: `allenai_olmocr-7b-0225-preview`)
- `PDF2MD_LM_STUDIO_API_KEY`: API key (default: `lm-studio`)
- `PDF2MD_MD_PAGE_DELIMITER`: Page separation mode (`delimited` or `concat`)

## LaunchAgent Deployment

The service runs as a macOS LaunchAgent for auto-start on login. The plist file must use the full path to the venv Python interpreter, not system Python, to ensure dependencies are available.

## Testing Architecture

- **Unit Tests**: Mock LM Studio responses and test individual components
- **Integration Tests**: End-to-end testing with temporary directories
- **Async Testing**: Uses `pytest-asyncio` for OCR processor testing
- **Mocking**: Extensive use of `unittest.mock` for external API calls

## Dependencies

Core dependencies:
- `watchdog`: File system monitoring
- `openai`: LM Studio API client
- `pypdf`: PDF text extraction
- `olmocr`: OCR pipeline utilities
- `python-dotenv`: Environment file loading
- `pytest` + `pytest-asyncio`: Testing framework