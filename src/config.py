import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; .env loading is best-effort


def get_env_var(name: str, default: Optional[str] = None, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


class Config:
    INPUT_DIR = get_env_var("INPUT_DIR", required=True)
    OUTPUT_DIR = get_env_var("OUTPUT_DIR", required=True)
    DONE_DIR = get_env_var("DONE_DIR", required=True)
    LM_STUDIO_API = get_env_var("LM_STUDIO_API", "http://localhost:1234", required=True)
    LOG_FILE = get_env_var("LOG_FILE", "app.log")

    @classmethod
    def as_dict(cls):
        return {k: getattr(cls, k) for k in dir(cls) if k.isupper() and not k.startswith("_")}
