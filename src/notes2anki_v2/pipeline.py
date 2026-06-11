from __future__ import annotations

import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from notes2anki_v2.ai import AiError, CardGenerator
from notes2anki_v2.anki import AnkiClient, AnkiError
from notes2anki_v2.config import Settings
from notes2anki_v2.console import Console
from notes2anki_v2.documents import Document, DocumentError, open_document
from notes2anki_v2.files import is_supported
from notes2anki_v2.history import HistoryStore, file_digest, slide_id
from notes2anki_v2.models import Card, ProcessingSummary, Slide


class Processor:
    def __init__(
        self,
        settings: Settings,
        anki: AnkiClient,
        generator: CardGenerator,
        console: Console | None = None,
    ) -> None:
        self.settings = settings
        self.anki = anki
        self.generator = generator
        self.history = HistoryStore(settings.history_file)
        self.console = console or Console()

    def process_file(self, path: Path, deck_name: str, note_type: str) -> ProcessingSummary:
        path = path.expanduser().resolve()
        summary = ProcessingSummary(source=path)

        if not path.exists():
            summary.messages.append("File does not exist.")
            return summary
        if not path.is_file():
            summary.messages.append("Path is not a file.")
            return summary
        if not is_supported(path):
            summary.messages.append(f"Unsupported file type: {path.suffix or '(no extension)'}")
            return summary

        self.console.info(f"\nProcessing {path.name}")
        digest = file_digest(path)
        document = open_document(path)
        with tempfile.TemporaryDirectory(prefix="notes2anki_v2_") as tmp:
            tmp_dir = Path(tmp)
            try:
                slides = self._prepare_slides(document, digest, tmp_dir, summary)
            except DocumentError as exc:
                summary.messages.append(str(exc))
                return summary

            if not slides:
                summary.completed = not summary.messages
                return summary

            global_context = ""
            document_text = document.text_summary()
            if document_text.strip():
                self.console.info("Analyzing the whole document for context...")
                try:
                    global_context = self.generator.generate_global_context(document_text)
                except AiError as exc:
                    self.console.warn(str(exc))
                    self.console.warn("Continuing with slide-by-slide generation.")

            cards = self._generate_cards(slides, global_context, summary)
            summary.generated = len(cards)
            if not cards:
                summary.messages.append("No flashcards were generated.")
                if summary.failed_slides == 0:
                    self._mark_slides_processed(digest, slides)
                    summary.completed = True
                return summary

            self.console.info(f"Uploading {len(cards)} card(s) to Anki...")
            with self.console.progress(cards, label="Uploading") as bar:
                for card in bar:
                    try:
                        if self.anki.add_card(card, deck_name, note_type):
                            summary.added += 1
                        else:
                            summary.duplicates += 1
                    except AnkiError as exc:
                        summary.messages.append(f"Anki rejected a card: {exc}")

            self._mark_slides_processed(digest, slides)
            # Duplicates count as handled: the card already exists in Anki.
            summary.completed = (summary.added + summary.duplicates) == len(cards)
            return summary

    def _prepare_slides(
        self, document: Document, digest: str, tmp_dir: Path, summary: ProcessingSummary
    ) -> list[Slide]:
        images = document.render_images(tmp_dir, self.settings.dpi, warn=self.console.warn)

        slides: list[Slide] = []
        for index, image_path in enumerate(images):
            if self.history.contains(slide_id(digest, index)):
                summary.skipped_already_processed += 1
                self.console.muted(f"Slide {index + 1}: already processed")
                continue
            if document.is_title_or_blank(index):
                summary.skipped_title_or_blank += 1
                self.console.muted(f"Slide {index + 1}: title or blank slide skipped")
                continue
            slides.append(
                Slide(
                    index=index,
                    image_path=image_path,
                    notes=document.slide_notes(index),
                    source_filename=document.path.name,
                )
            )

        self.console.info(f"{len(slides)} slide(s) ready for AI generation.")
        return slides

    def _generate_cards(
        self,
        slides: list[Slide],
        global_context: str,
        summary: ProcessingSummary,
    ) -> list[Card]:
        cards: list[Card] = []
        max_workers = min(self.settings.max_workers, max(len(slides), 1))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.generator.generate_cards,
                    slide.image_path,
                    slide.notes,
                    slide.source_filename,
                    slide.index,
                    global_context,
                ): slide
                for slide in slides
            }
            for future in as_completed(futures):
                slide = futures[future]
                try:
                    generated = [card for card in future.result() if card.is_usable()]
                    cards.extend(generated)
                    self.console.success(
                        f"Slide {slide.index + 1}: generated {len(generated)} card(s)"
                    )
                except AiError as exc:
                    summary.failed_slides += 1
                    summary.messages.append(str(exc))
                    self.console.warn(str(exc))

        return sorted(cards, key=lambda card: card.slide_index or 0)

    def _mark_slides_processed(self, digest: str, slides: list[Slide]) -> None:
        for slide in slides:
            self.history.add(slide_id(digest, slide.index))
        self.history.save()
