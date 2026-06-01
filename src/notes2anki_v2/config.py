from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _to_int(value: str | None, default: int, name: str) -> int:
    if value is None or value.strip() == "":
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a whole number, got {value!r}.") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return parsed


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    base_url: str
    model_name: str
    anki_url: str
    default_deck_name: str
    default_note_type: str
    poll_interval: int
    dpi: int
    max_workers: int
    history_file: Path

    @classmethod
    def load(cls) -> "Settings":
        cwd_env = Path.cwd() / ".env"
        if cwd_env.exists():
            load_dotenv(cwd_env)
        else:
            load_dotenv()

        project_root = Path.cwd()
        data_dir = project_root / ".notes2anki_v2"
        history_file = Path(os.getenv("HISTORY_FILE", str(data_dir / "processed_slides.json")))

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            base_url=os.getenv("BASE_URL", "https://api.openai.com/v1").strip(),
            model_name=os.getenv("MODEL_NAME", "gpt-4o-mini").strip(),
            anki_url=os.getenv("ANKI_URL", "http://127.0.0.1:8765").strip(),
            default_deck_name=os.getenv("DEFAULT_DECK_NAME", "Default").strip() or "Default",
            default_note_type=os.getenv("DEFAULT_NOTE_TYPE", "Notes2Anki").strip()
            or "Notes2Anki",
            poll_interval=_to_int(os.getenv("POLL_INTERVAL"), 3, "POLL_INTERVAL"),
            dpi=_to_int(os.getenv("DPI"), 150, "DPI"),
            max_workers=_to_int(os.getenv("MAX_WORKERS"), 4, "MAX_WORKERS"),
            history_file=history_file,
        )
