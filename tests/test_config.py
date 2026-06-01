from notes2anki_v2.config import Settings


def test_default_note_type_is_custom_model(monkeypatch) -> None:
    monkeypatch.delenv("DEFAULT_NOTE_TYPE", raising=False)

    settings = Settings.load()

    assert settings.default_note_type == "Notes2Anki"

