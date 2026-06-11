from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Slide:
    index: int
    image_path: Path
    notes: str = ""
    source_filename: str = ""


@dataclass
class Card:
    prompt: str
    answer: str
    formula: str = ""
    example_question: str = ""
    solution: str = ""
    topic: str = ""
    image_path: Path | None = None
    source_filename: str = ""
    slide_index: int | None = None

    @classmethod
    def from_mapping(cls, data: dict, image_path: Path, source_filename: str, slide_index: int) -> "Card":
        return cls(
            prompt=str(data.get("prompt", "")).strip(),
            answer=str(data.get("answer", "")).strip(),
            formula=str(data.get("formula", "")).strip(),
            example_question=str(data.get("example question", data.get("example_question", ""))).strip(),
            solution=str(data.get("solution", "")).strip(),
            topic=str(data.get("topic", "")).strip(),
            image_path=image_path,
            source_filename=source_filename,
            slide_index=slide_index,
        )

    def is_usable(self) -> bool:
        # Prompt is the duplicate-detection field in Anki and the card front;
        # RECOMMENDATION cards legitimately carry only a prompt.
        return bool(self.prompt)


@dataclass
class ProcessingSummary:
    source: Path
    added: int = 0
    duplicates: int = 0
    generated: int = 0
    completed: bool = False
    skipped_title_or_blank: int = 0
    skipped_already_processed: int = 0
    failed_slides: int = 0
    messages: list[str] = field(default_factory=list)
