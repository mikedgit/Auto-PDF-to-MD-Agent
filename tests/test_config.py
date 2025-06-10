import os
import pytest
from src.config import load_config

def test_config_env(monkeypatch):
    monkeypatch.setenv("INPUT_DIR", "/tmp/in")
    monkeypatch.setenv("OUTPUT_DIR", "/tmp/out")
    monkeypatch.setenv("DONE_DIR", "/tmp/done")
    monkeypatch.setenv("LM_STUDIO_API", "http://localhost:5678")
    monkeypatch.setenv("LOG_FILE", "test.log")

    cfg = load_config()
    assert cfg.INPUT_DIR == "/tmp/in"
    assert cfg.OUTPUT_DIR == "/tmp/out"
    assert cfg.DONE_DIR == "/tmp/done"
    assert cfg.LM_STUDIO_API == "http://localhost:5678"
    assert cfg.LOG_FILE == "test.log"

def test_config_required(monkeypatch):
    monkeypatch.delenv("INPUT_DIR", raising=False)
    monkeypatch.delenv("OUTPUT_DIR", raising=False)
    monkeypatch.delenv("DONE_DIR", raising=False)
    monkeypatch.delenv("LM_STUDIO_API", raising=False)
    with pytest.raises(RuntimeError):
        load_config()
