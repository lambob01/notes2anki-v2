import pytest

from notes2anki_v2.anki import AnkiClient, AnkiError, build_note
from notes2anki_v2.models import Card


class FakeAnkiClient(AnkiClient):
    def __init__(self, results: dict[str, object]) -> None:
        super().__init__("http://example.invalid")
        self.results = results
        self.calls: list[tuple[str, dict]] = []

    def invoke(self, action: str, **params: object) -> object:
        self.calls.append((action, params))
        return self.results[action]


def test_existing_note_type_requires_expected_fields() -> None:
    client = FakeAnkiClient(
        {
            "modelNames": ["Basic"],
            "modelFieldNames": ["Front", "Back"],
        }
    )

    with pytest.raises(AnkiError, match="missing required field"):
        client.ensure_note_type_exists("Basic")


def test_missing_note_type_is_created() -> None:
    client = FakeAnkiClient({"modelNames": [], "createModel": None})

    client.ensure_note_type_exists("Notes2Anki")

    assert client.calls[-1][0] == "createModel"
    assert client.calls[-1][1]["modelName"] == "Notes2Anki"


def test_build_note_uses_required_anki_fields() -> None:
    card = Card(
        prompt="What is X?",
        answer="X is Y",
        formula="x=y",
        topic="Topic",
        source_filename="lecture.pdf",
    )

    note = build_note(card, "slide.jpg", "Deck", "Notes2Anki")

    assert note["deckName"] == "Deck"
    assert note["modelName"] == "Notes2Anki"
    assert note["fields"]["formula"] == r"\[ x=y \]"
    assert note["fields"]["extra"] == '<img src="slide.jpg">'
