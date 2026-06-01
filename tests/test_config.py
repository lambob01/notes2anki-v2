from pathlib import Path

from notes2anki_v2.config import Settings, _normalize_base_url


def test_default_note_type_is_custom_model(monkeypatch) -> None:
    monkeypatch.setenv("DEFAULT_NOTE_TYPE", "")
    monkeypatch.chdir(Path(__file__).parent)

    settings = Settings.load()

    assert settings.default_note_type == "Notes2Anki"


def test_vectorengine_base_url_adds_v1() -> None:
    assert _normalize_base_url("https://api.vectorengine.ai/") == "https://api.vectorengine.ai/v1"
