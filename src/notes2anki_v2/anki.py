from __future__ import annotations

import base64
import hashlib
import html
import time
from pathlib import Path
from typing import Any

import requests

from notes2anki_v2.latex import clean_latex, format_formula
from notes2anki_v2.models import Card

MAX_ATTEMPTS = 5
RETRY_DELAY_SECONDS = 1
BUSY_RETRY_DELAY_SECONDS = 1.5
REQUEST_TIMEOUT_SECONDS = 15

REQUIRED_FIELDS = (
    "prompt",
    "answer",
    "formula",
    "example question",
    "solution",
    "extra",
    "topic",
)


class AnkiError(RuntimeError):
    pass


class AnkiClient:
    def __init__(self, url: str) -> None:
        self.url = url.rstrip("/")
        self._media_cache: dict[Path, str] = {}

    def is_running(self) -> bool:
        try:
            response = requests.get(self.url, timeout=2)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def invoke(self, action: str, **params: Any) -> Any:
        payload = {"action": action, "version": 6, "params": params}
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = requests.post(self.url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                if attempt == MAX_ATTEMPTS:
                    raise AnkiError(f"Could not talk to AnkiConnect at {self.url}: {exc}") from exc
                time.sleep(RETRY_DELAY_SECONDS)
                continue

            if not isinstance(data, dict):
                raise AnkiError(f"Unexpected AnkiConnect response: {data!r}")
            error = data.get("error")
            if error:
                if "QPushButton" in error or "deleted object" in error:
                    time.sleep(BUSY_RETRY_DELAY_SECONDS)
                    continue
                raise AnkiError(str(error))
            return data.get("result")
        raise AnkiError("AnkiConnect stayed busy after several retries.")

    def ensure_deck_exists(self, deck_name: str) -> None:
        self.invoke("createDeck", deck=deck_name)

    def ensure_note_type_exists(self, note_type: str) -> None:
        existing = self.invoke("modelNames")
        if isinstance(existing, list) and note_type in existing:
            fields = self.invoke("modelFieldNames", modelName=note_type)
            if not isinstance(fields, list):
                raise AnkiError(f"Could not inspect fields for note type '{note_type}'.")
            missing = [field for field in REQUIRED_FIELDS if field not in fields]
            if missing:
                missing_text = ", ".join(missing)
                raise AnkiError(
                    f"Note type '{note_type}' is missing required field(s): {missing_text}. "
                    "Use DEFAULT_NOTE_TYPE=Notes2Anki or create those fields in Anki."
                )
            return
        self.invoke(
            "createModel",
            modelName=note_type,
            inOrderFields=list(REQUIRED_FIELDS),
            cardTemplates=[
                {
                    "Name": "Card 1",
                    "Front": "{{prompt}}",
                    "Back": (
                        "{{FrontSide}}<hr id=answer>"
                        "{{answer}}<br>{{formula}}<br>{{example question}}<br>"
                        "{{solution}}<br>{{extra}}<br><small>{{topic}}</small>"
                    ),
                }
            ],
            css=(
                ".card { font-family: Arial, sans-serif; font-size: 20px; text-align: left; "
                "color: #111; background: #fff; line-height: 1.45; } "
                "img { max-width: 100%; height: auto; } "
                "small { color: #666; }"
            ),
        )

    def add_card(self, card: Card, deck_name: str, note_type: str) -> bool:
        """Add a card to Anki. Returns False if Anki rejected it as a duplicate."""
        if card.image_path is None:
            raise AnkiError("Cannot add card because it has no slide image.")
        media_name = self.store_media(card.image_path)
        note = build_note(card, media_name, deck_name, note_type)
        try:
            self.invoke("addNote", note=note)
        except AnkiError as exc:
            if "duplicate" in str(exc).lower():
                return False
            raise
        return True

    def store_media(self, image_path: Path) -> str:
        cached = self._media_cache.get(image_path)
        if cached is not None:
            return cached
        data = image_path.read_bytes()
        image_b64 = base64.b64encode(data).decode("utf-8")
        digest = hashlib.sha256(data).hexdigest()[:16]
        extension = image_path.suffix.lower() or ".jpg"
        filename = f"notes2anki_v2_{digest}{extension}"
        self.invoke("storeMediaFile", filename=filename, data=image_b64)
        self._media_cache[image_path] = filename
        return filename


def _text_field(value: object) -> str:
    # Model output is rendered as HTML by Anki; escape it so a hostile or
    # confused model cannot inject markup into the collection.
    return html.escape(clean_latex(value), quote=False)


def build_note(card: Card, media_filename: str, deck_name: str, note_type: str) -> dict[str, Any]:
    topic = clean_latex(card.topic) or "Notes2Anki"
    if card.source_filename:
        topic = f"{topic} - {Path(card.source_filename).stem}"

    fields = {
        "prompt": _text_field(card.prompt),
        "answer": _text_field(card.answer),
        "formula": html.escape(format_formula(card.formula), quote=False),
        "example question": _text_field(card.example_question),
        "solution": _text_field(card.solution),
        "extra": f'<img src="{media_filename}">',
        "topic": html.escape(topic, quote=False),
    }
    return {
        "deckName": deck_name,
        "modelName": note_type,
        "fields": fields,
        "options": {"allowDuplicate": False},
        "tags": ["notes2anki_v2"],
    }
