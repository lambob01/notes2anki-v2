from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

from openai import OpenAI

from notes2anki_v2.models import Card


CARD_PROMPT = """You are an expert educator and spaced repetition card writer.

Analyze the slide image and optional speaker notes. Create high-quality Anki flashcards only for testable academic material.

Return a JSON object with exactly this shape:
{{"cards":[{{"prompt":"","answer":"","formula":"","example question":"","solution":"","topic":""}}]}}

Rules:
1. If the slide is a title slide, agenda, logistics, decorative image, or has no testable content, return {{"cards":[]}}.
2. Each card must test one idea only.
3. Use plain text. Do not use Markdown, HTML, cloze syntax, or Anki-specific tags.
4. Use LaTeX only in the "formula" field. Inline math must use \\(...\\), display math must use \\[...\\].
5. Populate "example question" and "solution" only when the slide explicitly contains an exercise, practice problem, or worked example.
6. If a diagram is important and image occlusion would be better, create one card whose prompt starts with "RECOMMENDATION: Use Image Occlusion for".
7. Do not invent facts. If essential context is inferred from the global lecture context rather than visible on this slide, append "(not in slides)" to the prompt.
8. Return valid JSON only. No code fences or explanatory text.

{global_context}
"""


class AiError(RuntimeError):
    pass


class CardGenerator:
    def __init__(self, api_key: str, base_url: str, model_name: str) -> None:
        if not api_key:
            raise AiError(
                "OPENAI_API_KEY is missing. Add it to .env or set it in your terminal environment."
            )
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name

    def generate_global_context(self, document_text: str) -> str:
        if not document_text.strip():
            return ""
        prompt = (
            "Create a concise lecture syllabus and concept map from this extracted lecture text. "
            "Focus on learning objectives and major topics. Return plain text only.\n\n"
            f"{document_text}"
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1800,
                timeout=120,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise AiError(f"Could not generate global lecture context: {exc}") from exc

    def generate_cards(
        self,
        image_path: Path,
        notes: str,
        source_filename: str,
        slide_index: int,
        global_context: str,
    ) -> list[Card]:
        image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        prompt = CARD_PROMPT.format(
            global_context=(
                f"Global lecture context:\n{global_context}\n" if global_context.strip() else ""
            )
        )
        content: list[dict[str, Any]] = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
        ]
        if notes.strip():
            content.append({"type": "text", "text": f"Speaker notes:\n{notes}"})

        last_error = ""
        for attempt in range(1, 4):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": content}],
                    max_tokens=4000,
                    timeout=120,
                )
                raw = response.choices[0].message.content or ""
                card_dicts = extract_cards_json(raw)
                return [
                    Card.from_mapping(item, image_path, source_filename, slide_index)
                    for item in card_dicts
                    if isinstance(item, dict)
                ]
            except Exception as exc:
                last_error = str(exc)
                if attempt == 3:
                    break
        raise AiError(f"AI card generation failed for slide {slide_index + 1}: {last_error}")


def extract_cards_json(raw_text: str) -> list[dict[str, Any]]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    first_json = re.search(r"[\[{]", text)
    if first_json:
        text = text[first_json.start() :]

    text = _escape_common_bad_latex_backslashes(text)
    candidates = [text]
    for end in range(len(text), 0, -1):
        if text[end - 1] in "]}":
            trimmed = text[:end]
            candidates.extend([trimmed, f"{trimmed}]}}", f"{trimmed}}}"])
            break

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            return _coerce_cards(parsed)
        except json.JSONDecodeError:
            continue

    raise AiError("The AI returned text that was not valid JSON.")


def _coerce_cards(parsed: Any) -> list[dict[str, Any]]:
    if isinstance(parsed, dict):
        cards = parsed.get("cards")
        if isinstance(cards, list):
            return [item for item in cards if isinstance(item, dict)]
        for value in parsed.values():
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [parsed]
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []


def _escape_common_bad_latex_backslashes(text: str) -> str:
    text = re.sub(r'(?<!\\)\\([^"\\/bfnrtu])', r"\\\\\1", text)
    text = re.sub(r"(?<!\\)\\f(?=rac)", r"\\\\f", text)
    text = re.sub(r"(?<!\\)\\b(?=egin|eta)", r"\\\\b", text)
    text = re.sub(r"(?<!\\)\\n(?=u|abla)", r"\\\\n", text)
    text = re.sub(r"(?<!\\)\\t(?=heta|au|ilde|imes)", r"\\\\t", text)
    text = re.sub(r"(?<!\\)\\r(?=ho|ight)", r"\\\\r", text)
    return text
