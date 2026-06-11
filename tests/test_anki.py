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


def test_build_note_escapes_html_in_model_output() -> None:
    card = Card(
        prompt='What is <script>alert("x")</script>?',
        answer="a < b",
    )

    note = build_note(card, "slide.jpg", "Deck", "Notes2Anki")

    assert "<script>" not in note["fields"]["prompt"]
    assert "&lt;script&gt;" in note["fields"]["prompt"]
    assert note["fields"]["answer"] == "a &lt; b"
    assert note["fields"]["extra"] == '<img src="slide.jpg">'


def test_add_card_returns_false_for_duplicates(tmp_path) -> None:
    class DuplicateRejectingClient(AnkiClient):
        def invoke(self, action: str, **params: object) -> object:
            if action == "addNote":
                raise AnkiError("cannot create note because it is a duplicate")
            return None

    image = tmp_path / "slide.jpg"
    image.write_bytes(b"fake image data")
    card = Card(prompt="Q", answer="A", image_path=image)
    client = DuplicateRejectingClient("http://example.invalid")

    assert client.add_card(card, "Deck", "Notes2Anki") is False
