from notes2anki_v2.latex import clean_latex, format_formula


def test_clean_latex_strips_mathjax_tags() -> None:
    assert clean_latex("<anki-mathjax>x</anki-mathjax>") == "x"


def test_clean_latex_preserves_arrows_in_prose() -> None:
    assert clean_latex("glucose -> pyruvate") == "glucose -> pyruvate"
    assert clean_latex("A <-> B") == "A <-> B"


def test_format_formula_replaces_arrows() -> None:
    assert format_formula("a -> b") == r"\[ a \rightarrow b \]"
    assert format_formula("a <-> b") == r"\[ a \leftrightarrow b \]"


def test_format_formula_wraps_bare_formula() -> None:
    assert format_formula("x=y") == r"\[ x=y \]"


def test_format_formula_keeps_existing_display_math() -> None:
    assert format_formula(r"\[ x=y \]") == r"\[ x=y \]"


def test_format_formula_empty() -> None:
    assert format_formula("") == ""
    assert format_formula(None) == ""
