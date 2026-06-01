# Project Memory

This file exists so future Codex sessions can recover the important context for this project. At the start of a new session, ask Codex to read this file before making changes.

## Project

`notes2anki_v2` is a clean Python CLI replacement for the rough prototype in `notes2anki`.

Repository:

```text
https://github.com/lambob01/notes2anki-v2
```

The original `notes2anki` prototype should be treated only as a logic reference. Do not modify it unless explicitly asked.

## Local Path

```text
D:\uni\codex project\anki automator\notes2anki_v2
```

## Main Commands

Run commands from the `notes2anki_v2` project root.

Convert one file:

```powershell
py -m notes2anki_v2 convert "path\to\lecture.pptx"
```

Watch a folder:

```powershell
py -m notes2anki_v2 watch --dir ".\upload_slides"
```

Run tests:

```powershell
py -m pytest
```

## Configuration

The tool uses `.env` in the project root. `.env` is intentionally ignored by Git.

Important variables:

```env
OPENAI_API_KEY=
BASE_URL=
MODEL_NAME=
ANKI_URL=http://127.0.0.1:8765
DEFAULT_DECK_NAME=
DEFAULT_NOTE_TYPE=
POLL_INTERVAL=3
DPI=150
MAX_WORKERS=4
```

Current working provider notes:

- VectorEngine base URLs without `/v1` are normalized automatically.
- Some providers return plain string responses instead of OpenAI SDK response objects; the code handles both.

## Current Architecture

Important files:

- `src/notes2anki_v2/cli.py`: Click CLI commands.
- `src/notes2anki_v2/pipeline.py`: Main conversion orchestration.
- `src/notes2anki_v2/documents.py`: PDF/PPTX/image rendering and text extraction.
- `src/notes2anki_v2/ai.py`: AI prompts, provider calls, JSON extraction.
- `src/notes2anki_v2/anki.py`: AnkiConnect client, note model creation, media upload.
- `src/notes2anki_v2/config.py`: Environment settings.
- `src/notes2anki_v2/history.py`: Processed-slide history.

## Major Implementation Decisions

- Keep `notes2anki_v2` independent from the rough prototype.
- Use a package layout rather than a single script.
- Keep the CLI runnable with `py -m notes2anki_v2`.
- Let the tool auto-create the `Notes2Anki` note type if it does not exist.
- Validate required fields if the user points to an existing Anki note type.
- Keep generated slide history in `.notes2anki_v2/processed_slides.json`.
- Do not commit `.env`, caches, or generated state.

## Verified Runtime Result

This command was run successfully:

```powershell
py -m notes2anki_v2 convert "G:\My Drive\bath\lecture slides\biology\CE10232 - TCA - 2 - Biology.pptx"
```

Observed result:

- 31 slides ready for generation.
- 109 cards generated.
- 108 cards added to Anki.
- 1 card rejected by Anki as a duplicate.

## Known Caveats

- Anki must be open with AnkiConnect installed.
- Network access is required for AI calls.
- `notes2anki-v2.exe` may not be on Windows PATH, so `py -m notes2anki_v2 ...` is the reliable command.
- Duplicate Anki notes are rejected by design.

## Future Idea: Course Wiki / Memory

The user is interested in adding a Karpathy-style LLM wiki/memory system inspired by:

```text
https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
```

Recommended implementation path:

1. Start with a zero-extra-cost markdown memory export after each conversion.
2. Store lecture summaries and generated cards in a local `wiki/` or `.notes2anki_v2/wiki/` directory.
3. Add concept pages later using a text-only AI call.
4. Only after that, use relevant wiki snippets as context for future card generation.

Avoid sending the entire wiki into every lecture-processing run; retrieve only relevant concept pages to control cost.

