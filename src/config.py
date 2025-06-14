import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; .env loading is best-effort


def get_env_var(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass
class Config:
    INPUT_DIR: str
    OUTPUT_DIR: str
    DONE_DIR: str
    LM_STUDIO_API: str
    LM_STUDIO_MODEL: str = "allenai_olmocr-7b-0225-preview"
    LM_STUDIO_API_KEY: str = "lm-studio"
    LOG_FILE: str = "app.log"
    MD_PAGE_DELIMITER: str = "delimited"  # 'delimited' or 'concat'

    def as_dict(self):
        return self.__dict__


def load_config() -> Config:
    return Config(
        INPUT_DIR=get_env_var("PDF2MD_INPUT_DIR", required=True),
        OUTPUT_DIR=get_env_var("PDF2MD_OUTPUT_DIR", required=True),
        DONE_DIR=get_env_var("PDF2MD_DONE_DIR", required=True),
        LM_STUDIO_API=get_env_var(
            "PDF2MD_LM_STUDIO_API", "http://localhost:1234", required=True
        ),
        LM_STUDIO_MODEL=get_env_var(
            "PDF2MD_LM_STUDIO_MODEL", "allenai_olmocr-7b-0225-preview"
        ),
        LM_STUDIO_API_KEY=get_env_var("PDF2MD_LM_STUDIO_API_KEY", "lm-studio"),
        LOG_FILE=get_env_var("PDF2MD_LOG_FILE", "app.log"),
        MD_PAGE_DELIMITER=get_env_var("PDF2MD_MD_PAGE_DELIMITER", "delimited"),
    )
