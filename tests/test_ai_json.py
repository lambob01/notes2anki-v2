from notes2anki_v2.ai import _response_text, extract_cards_json


def test_extract_cards_json_accepts_fenced_object() -> None:
    raw = '```json\n{"cards":[{"prompt":"Q","answer":"A"}]}\n```'

    cards = extract_cards_json(raw)

    assert cards == [{"prompt": "Q", "answer": "A"}]


def test_extract_cards_json_repairs_common_latex_backslashes() -> None:
    raw = '{"cards":[{"prompt":"Formula","answer":"","formula":"\\frac{a}{b}"}]}'

    cards = extract_cards_json(raw)

    assert cards[0]["formula"] == "\\frac{a}{b}"


def test_response_text_accepts_plain_string_provider_response() -> None:
    assert _response_text('{"cards":[]}') == '{"cards":[]}'
