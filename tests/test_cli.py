from pathlib import Path

from notes2anki_v2.cli import _resolve_settings
from notes2anki_v2.config import Settings


def _settings(monkeypatch) -> Settings:
    monkeypatch.setenv("MODEL_NAME", "gpt-4o-mini")
    monkeypatch.chdir(Path(__file__).parent)
    return Settings.load()


def test_model_flag_overrides_env(monkeypatch) -> None:
    settings = _settings(monkeypatch)
    assert settings.model_name == "gpt-4o-mini"

    overridden = _resolve_settings(settings, "gemini-2.5-pro")

    assert overridden.model_name == "gemini-2.5-pro"
    # Other settings are preserved unchanged.
    assert overridden.base_url == settings.base_url
    assert overridden.openai_api_key == settings.openai_api_key


def test_model_flag_is_trimmed(monkeypatch) -> None:
    settings = _settings(monkeypatch)

    assert _resolve_settings(settings, "  gpt-5.5  ").model_name == "gpt-5.5"


def test_blank_or_missing_model_keeps_env(monkeypatch) -> None:
    settings = _settings(monkeypatch)

    assert _resolve_settings(settings, None).model_name == "gpt-4o-mini"
    assert _resolve_settings(settings, "").model_name == "gpt-4o-mini"
    assert _resolve_settings(settings, "   ").model_name == "gpt-4o-mini"
