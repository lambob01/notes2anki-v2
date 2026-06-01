# Notes2Anki v2

Notes2Anki v2 is a Python CLI tool that converts lecture PDFs, PowerPoint files, and images into Anki flashcards. It renders slides, sends each content slide to a vision-capable OpenAI-compatible model, and uploads generated cards to Anki through AnkiConnect.

## Features

- Converts `.pdf`, `.pptx`, `.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif`, and `.webp`
- Supports single-file conversion and watch-folder automation
- Uses speaker notes and document-wide context when available
- Skips already processed slides using a local history file
- Uploads slide images to Anki media and attaches them to cards
- Gives plain-English error messages instead of Python tracebacks

## Requirements

- Python 3.10 or newer
- Anki desktop app
- The AnkiConnect add-on installed in Anki
- An OpenAI-compatible API key for a vision-capable model
- LibreOffice is recommended for high-quality PowerPoint rendering

Without LibreOffice, PowerPoint files still process using a lower-fidelity text rendering fallback.

## Installation

From inside this folder:

```bash
pip install -e .
```

For development and tests:

```bash
pip install -e ".[dev]"
```

Create your environment file:

```bash
copy .env.example .env
```

On macOS or Linux:

```bash
cp .env.example .env
```

Edit `.env` and set at least:

```env
OPENAI_API_KEY=your_api_key_here
BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o-mini
ANKI_URL=http://127.0.0.1:8765
DEFAULT_DECK_NAME=Default
DEFAULT_NOTE_TYPE=Notes2Anki
```

If you use a custom OpenAI-compatible provider, set `BASE_URL` and `MODEL_NAME` for that provider.

## Anki Setup

1. Install Anki.
2. Install the AnkiConnect add-on.
3. Open Anki before running Notes2Anki.
4. The tool can create its own configured note type automatically. If you use an existing note type, make sure it has these fields:

```text
prompt
answer
formula
example question
solution
extra
topic
```

Do not use Anki's built-in `Basic` note type unless you add these fields yourself. A good default is `DEFAULT_NOTE_TYPE=Notes2Anki`.

## Usage

Convert one file:

```bash
notes2anki-v2 convert path/to/lecture.pdf --deck "My Deck" --note-type "My Note Type"
```

Use defaults from `.env`:

```bash
notes2anki-v2 convert path/to/lecture.pptx
```

Watch a folder:

```bash
notes2anki-v2 watch --dir ./upload_slides
```

By default, watch mode deletes a source file after it successfully adds cards. To keep files:

```bash
notes2anki-v2 watch --dir ./upload_slides --keep-files
```

Show help:

```bash
notes2anki-v2 --help
notes2anki-v2 convert --help
notes2anki-v2 watch --help
```

On Windows, if `notes2anki-v2` is not found after installation, use:

```bash
py -m notes2anki_v2 --help
```

## Configuration

Environment variables:

| Name | Default | Meaning |
| --- | --- | --- |
| `OPENAI_API_KEY` | empty | Required API key |
| `BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible API base URL |
| `MODEL_NAME` | `gpt-4o-mini` | Vision-capable model |
| `ANKI_URL` | `http://127.0.0.1:8765` | AnkiConnect URL |
| `DEFAULT_DECK_NAME` | `Default` | Default Anki deck |
| `DEFAULT_NOTE_TYPE` | `Notes2Anki` | Default Anki note type |
| `POLL_INTERVAL` | `3` | Watch mode scan interval in seconds |
| `DPI` | `150` | PDF/PPTX render quality |
| `MAX_WORKERS` | `4` | Parallel AI requests |
| `HISTORY_FILE` | `.notes2anki_v2/processed_slides.json` | Processed-slide history path |

## Troubleshooting

If Anki cannot be reached, open Anki and confirm AnkiConnect is installed.

If Anki rejects cards, check that your note type contains the required fields exactly as listed above.

If you point `DEFAULT_NOTE_TYPE` or `--note-type` at an existing Anki note type, Notes2Anki validates the required fields before processing. If the note type does not exist, it creates one automatically.

If PowerPoint rendering looks poor, install LibreOffice and rerun the command.

If the AI returns invalid output, try a stronger vision-capable model or reduce `MAX_WORKERS` to avoid provider rate limits.
