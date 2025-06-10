import os
import pytest
from src import config

def test_config_env(monkeypatch):
    monkeypatch.setenv("INPUT_DIR", "/tmp/in")
    monkeypatch.setenv("OUTPUT_DIR", "/tmp/out")
    monkeypatch.setenv("DONE_DIR", "/tmp/done")
    monkeypatch.setenv("LM_STUDIO_API", "http://localhost:5678")
    monkeypatch.setenv("LOG_FILE", "test.log")

    # Reload config module to pick up new env vars
    import importlib
    importlib.reload(config)

    assert config.Config.INPUT_DIR == "/tmp/in"
    assert config.Config.OUTPUT_DIR == "/tmp/out"
    assert config.Config.DONE_DIR == "/tmp/done"
    assert config.Config.LM_STUDIO_API == "http://localhost:5678"
    assert config.Config.LOG_FILE == "test.log"

def test_config_required(monkeypatch):
    monkeypatch.delenv("INPUT_DIR", raising=False)
    monkeypatch.delenv("OUTPUT_DIR", raising=False)
    monkeypatch.delenv("DONE_DIR", raising=False)
    monkeypatch.delenv("LM_STUDIO_API", raising=False)
    with pytest.raises(RuntimeError):
        import importlib
        importlib.reload(config)
