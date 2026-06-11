from pathlib import Path

from PIL import Image

from notes2anki_v2.anki import AnkiClient, AnkiError
from notes2anki_v2.config import Settings
from notes2anki_v2.history import file_digest, slide_id
from notes2anki_v2.models import Card
from notes2anki_v2.pipeline import Processor


class FakeGenerator:
    def __init__(self, cards_per_slide: int = 1) -> None:
        self.cards_per_slide = cards_per_slide

    def generate_global_context(self, document_text: str) -> str:
        return ""

    def generate_cards(self, image_path, notes, source_filename, slide_index, global_context):
        return [
            Card(
                prompt=f"Q{slide_index}-{n}",
                answer="A",
                image_path=image_path,
                source_filename=source_filename,
                slide_index=slide_index,
            )
            for n in range(self.cards_per_slide)
        ]


class FakeAnki(AnkiClient):
    def __init__(self, duplicate_prompts: set[str] | None = None) -> None:
        super().__init__("http://example.invalid")
        self.duplicate_prompts = duplicate_prompts or set()
        self.calls: list[tuple[str, dict]] = []

    def invoke(self, action: str, **params):
        self.calls.append((action, params))
        if action == "addNote":
            prompt = params["note"]["fields"]["prompt"]
            if prompt in self.duplicate_prompts:
                raise AnkiError("cannot create note because it is a duplicate")
        return None


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        openai_api_key="test-key",
        base_url="http://example.invalid/v1",
        model_name="test-model",
        anki_url="http://example.invalid",
        default_deck_name="Deck",
        default_note_type="Notes2Anki",
        poll_interval=3,
        dpi=72,
        max_workers=2,
        history_file=tmp_path / "history.json",
    )


def _make_image(tmp_path: Path) -> Path:
    image_path = tmp_path / "slide.png"
    Image.new("RGB", (20, 20), "white").save(image_path)
    return image_path


def test_process_image_adds_cards_and_records_history(tmp_path: Path) -> None:
    image_path = _make_image(tmp_path)
    anki = FakeAnki()
    processor = Processor(_settings(tmp_path), anki, FakeGenerator(cards_per_slide=2))

    summary = processor.process_file(image_path, "Deck", "Notes2Anki")

    assert summary.generated == 2
    assert summary.added == 2
    assert summary.completed is True
    expected_id = slide_id(file_digest(image_path.resolve()), 0)
    assert processor.history.contains(expected_id)
    assert (tmp_path / "history.json").exists()


def test_media_uploaded_once_per_image(tmp_path: Path) -> None:
    image_path = _make_image(tmp_path)
    anki = FakeAnki()
    processor = Processor(_settings(tmp_path), anki, FakeGenerator(cards_per_slide=3))

    processor.process_file(image_path, "Deck", "Notes2Anki")

    media_calls = [call for call in anki.calls if call[0] == "storeMediaFile"]
    note_calls = [call for call in anki.calls if call[0] == "addNote"]
    assert len(media_calls) == 1
    assert len(note_calls) == 3


def test_duplicates_count_as_completed(tmp_path: Path) -> None:
    image_path = _make_image(tmp_path)
    anki = FakeAnki(duplicate_prompts={"Q0-1"})
    processor = Processor(_settings(tmp_path), anki, FakeGenerator(cards_per_slide=2))

    summary = processor.process_file(image_path, "Deck", "Notes2Anki")

    assert summary.added == 1
    assert summary.duplicates == 1
    assert summary.completed is True


def test_already_processed_slide_is_skipped(tmp_path: Path) -> None:
    image_path = _make_image(tmp_path)
    anki = FakeAnki()
    processor = Processor(_settings(tmp_path), anki, FakeGenerator())

    first = processor.process_file(image_path, "Deck", "Notes2Anki")
    second = processor.process_file(image_path, "Deck", "Notes2Anki")

    assert first.added == 1
    assert second.added == 0
    assert second.skipped_already_processed == 1
    assert second.completed is True


def test_unsupported_file_is_rejected(tmp_path: Path) -> None:
    bogus = tmp_path / "notes.txt"
    bogus.write_text("hello")
    processor = Processor(_settings(tmp_path), FakeAnki(), FakeGenerator())

    summary = processor.process_file(bogus, "Deck", "Notes2Anki")

    assert summary.added == 0
    assert summary.completed is False
    assert any("Unsupported" in message for message in summary.messages)


def test_card_without_prompt_is_unusable() -> None:
    assert Card(prompt="", answer="A").is_usable() is False
    assert Card(prompt="RECOMMENDATION: Use Image Occlusion for X", answer="").is_usable() is True
