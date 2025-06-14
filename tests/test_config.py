import os
import pytest
from src.config import load_config

def test_config_env(monkeypatch):
    monkeypatch.setenv("PDF2MD_INPUT_DIR", "/tmp/in")
    monkeypatch.setenv("PDF2MD_OUTPUT_DIR", "/tmp/out")
    monkeypatch.setenv("PDF2MD_DONE_DIR", "/tmp/done")
    monkeypatch.setenv("PDF2MD_LM_STUDIO_API", "http://localhost:5678")
    monkeypatch.setenv("PDF2MD_LM_STUDIO_MODEL", "test-model")
    monkeypatch.setenv("PDF2MD_LM_STUDIO_API_KEY", "test-key")
    monkeypatch.setenv("PDF2MD_LOG_FILE", "test.log")

    cfg = load_config()
    assert cfg.INPUT_DIR == "/tmp/in"
    assert cfg.OUTPUT_DIR == "/tmp/out"
    assert cfg.DONE_DIR == "/tmp/done"
    assert cfg.LM_STUDIO_API == "http://localhost:5678"
    assert cfg.LM_STUDIO_MODEL == "test-model"
    assert cfg.LM_STUDIO_API_KEY == "test-key"
    assert cfg.LOG_FILE == "test.log"

def test_config_required(monkeypatch):
    monkeypatch.delenv("PDF2MD_INPUT_DIR", raising=False)
    monkeypatch.delenv("PDF2MD_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("PDF2MD_DONE_DIR", raising=False)
    monkeypatch.delenv("PDF2MD_LM_STUDIO_API", raising=False)
    monkeypatch.delenv("PDF2MD_LM_STUDIO_MODEL", raising=False)
    monkeypatch.delenv("PDF2MD_LM_STUDIO_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        load_config()


def test_config_defaults(monkeypatch):
    # Set only required variables
    monkeypatch.setenv("PDF2MD_INPUT_DIR", "/tmp/in")
    monkeypatch.setenv("PDF2MD_OUTPUT_DIR", "/tmp/out")
    monkeypatch.setenv("PDF2MD_DONE_DIR", "/tmp/done")
    monkeypatch.setenv("PDF2MD_LM_STUDIO_API", "http://localhost:1234")
    
    # Clear optional variables to test defaults
    monkeypatch.delenv("PDF2MD_LM_STUDIO_MODEL", raising=False)
    monkeypatch.delenv("PDF2MD_LM_STUDIO_API_KEY", raising=False)
    monkeypatch.delenv("PDF2MD_LOG_FILE", raising=False)
    monkeypatch.delenv("PDF2MD_MD_PAGE_DELIMITER", raising=False)

    cfg = load_config()
    assert cfg.LM_STUDIO_MODEL == "allenai_olmocr-7b-0225-preview"
    assert cfg.LM_STUDIO_API_KEY == "lm-studio"
    assert cfg.LOG_FILE == "app.log"
    assert cfg.MD_PAGE_DELIMITER == "delimited"


def test_get_env_var_with_default():
    """Test get_env_var function with default values."""
    import os
    from src.config import get_env_var
    
    # Test with non-existent variable and default
    result = get_env_var("NON_EXISTENT_VAR", "default_value")
    assert result == "default_value"
    
    # Test with existing variable
    os.environ["TEST_VAR"] = "test_value"
    result = get_env_var("TEST_VAR", "default_value")
    assert result == "test_value"
    
    # Clean up
    os.environ.pop("TEST_VAR", None)


def test_get_env_var_required_missing():
    """Test get_env_var raises error for missing required variables."""
    from src.config import get_env_var
    
    with pytest.raises(RuntimeError, match="Missing required environment variable: NON_EXISTENT_REQUIRED"):
        get_env_var("NON_EXISTENT_REQUIRED", required=True)
