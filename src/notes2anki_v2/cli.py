from __future__ import annotations

import time
from pathlib import Path

import click

from notes2anki_v2.ai import AiError, CardGenerator
from notes2anki_v2.anki import AnkiClient, AnkiError
from notes2anki_v2.config import Settings
from notes2anki_v2.console import Console
from notes2anki_v2.files import SUPPORTED_EXTENSIONS, is_supported, wait_for_file_stability
from notes2anki_v2.pipeline import Processor


def _settings() -> Settings:
    try:
        return Settings.load()
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _processor(settings: Settings, console: Console) -> Processor:
    anki = AnkiClient(settings.anki_url)
    if not anki.is_running():
        raise click.ClickException(
            "AnkiConnect is not reachable. Open Anki, install the AnkiConnect add-on, "
            f"and confirm it is listening at {settings.anki_url}."
        )
    try:
        generator = CardGenerator(
            api_key=settings.openai_api_key,
            base_url=settings.base_url,
            model_name=settings.model_name,
        )
    except AiError as exc:
        raise click.ClickException(str(exc)) from exc
    return Processor(settings=settings, anki=anki, generator=generator, console=console)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option()
def cli() -> None:
    """Convert lecture PDFs, PowerPoints, and images into Anki flashcards."""


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--deck", help="Anki deck name. Defaults to DEFAULT_DECK_NAME from .env.")
@click.option("--note-type", help="Anki note type/model. Defaults to DEFAULT_NOTE_TYPE from .env.")
def convert(file_path: Path, deck: str | None, note_type: str | None) -> None:
    """Convert one PDF, PPTX, or image file and upload cards to Anki."""
    console = Console()
    settings = _settings()
    deck_name = deck or settings.default_deck_name
    note_model = note_type or settings.default_note_type
    processor = _processor(settings, console)

    try:
        processor.anki.ensure_deck_exists(deck_name)
        processor.anki.ensure_note_type_exists(note_model)
        summary = processor.process_file(file_path, deck_name, note_model)
    except AnkiError as exc:
        raise click.ClickException(f"Anki error: {exc}") from exc
    except Exception as exc:
        raise click.ClickException(f"Unexpected error: {exc}") from exc

    _print_summary(summary.added, summary.generated, summary.messages, console)


@cli.command()
@click.option(
    "--dir",
    "directory",
    default="./upload_slides",
    type=click.Path(file_okay=False, path_type=Path),
    show_default=True,
    help="Directory to monitor for supported files.",
)
@click.option("--deck", help="Anki deck name. Defaults to DEFAULT_DECK_NAME from .env.")
@click.option("--note-type", help="Anki note type/model. Defaults to DEFAULT_NOTE_TYPE from .env.")
@click.option("--interval", type=int, help="Seconds between folder scans.")
@click.option(
    "--keep-files",
    is_flag=True,
    help="Keep source files after successful processing instead of deleting them.",
)
def watch(
    directory: Path,
    deck: str | None,
    note_type: str | None,
    interval: int | None,
    keep_files: bool,
) -> None:
    """Watch a folder and process files as they appear."""
    console = Console()
    settings = _settings()
    deck_name = deck or settings.default_deck_name
    note_model = note_type or settings.default_note_type
    scan_interval = interval or settings.poll_interval
    if scan_interval <= 0:
        raise click.ClickException("--interval must be greater than zero.")

    processor = _processor(settings, console)
    try:
        processor.anki.ensure_deck_exists(deck_name)
        processor.anki.ensure_note_type_exists(note_model)
    except AnkiError as exc:
        raise click.ClickException(
            f"Could not create or verify Anki deck/note type '{deck_name}' / '{note_model}': {exc}"
        ) from exc

    directory.mkdir(parents=True, exist_ok=True)
    console.info(f"Watching {directory.resolve()}")
    console.info(f"Supported file types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
    console.info("Press Ctrl+C to stop.\n")

    session_added = 0
    try:
        while True:
            files = sorted(path for path in directory.iterdir() if path.is_file() and is_supported(path))
            for file_path in files:
                if not wait_for_file_stability(file_path):
                    console.warn(f"Skipping {file_path.name}: file is still changing or cannot be read.")
                    continue
                summary = processor.process_file(file_path, deck_name, note_model)
                session_added += summary.added
                _print_summary(summary.added, summary.generated, summary.messages, console)
                if summary.completed and not keep_files:
                    try:
                        file_path.unlink()
                        console.muted(f"Deleted processed file: {file_path.name}")
                    except OSError as exc:
                        console.warn(f"Could not delete {file_path.name}: {exc}")
            time.sleep(scan_interval)
    except KeyboardInterrupt:
        console.success(f"\nStopped. Added {session_added} card(s) this session.")


def _print_summary(added: int, generated: int, messages: list[str], console: Console) -> None:
    if added:
        console.success(f"Done. Added {added} card(s) to Anki.")
    elif generated:
        console.warn("Cards were generated, but none were added to Anki.")
    else:
        console.warn("Done. No cards were added.")
    for message in messages:
        console.warn(f"- {message}")
