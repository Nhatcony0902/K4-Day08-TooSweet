"""Configuration helper with an optional python-dotenv dependency."""

import os
from pathlib import Path


def load_dotenv(path: str | Path = ".env") -> None:
    try:
        from dotenv import load_dotenv as external_load_dotenv

        external_load_dotenv(path)
        return
    except ImportError:
        pass

    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
