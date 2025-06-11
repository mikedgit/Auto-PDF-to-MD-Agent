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
