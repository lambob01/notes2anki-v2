from __future__ import annotations

import re


def clean_latex(text: object) -> str:
    if text is None:
        return ""
    cleaned = str(text)
    cleaned = re.sub(r"</?anki-mathjax[^>]*>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"&lt;/?anki-mathjax.*?&gt;", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"\\?</?anki-mathjax.*?\\?>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    return cleaned.strip()


def format_formula(formula: object) -> str:
    cleaned = clean_latex(formula)
    # Arrow shorthand is only meaningful inside MathJax-rendered formulas.
    cleaned = cleaned.replace("<->", r"\leftrightarrow").replace("->", r"\rightarrow")
    cleaned = cleaned.replace(r"\\[", r"\[").replace(r"\\]", r"\]")
    cleaned = cleaned.replace(r"\\(", r"\(").replace(r"\\)", r"\)")
    if cleaned and not cleaned.startswith((r"\[", "$$")):
        cleaned = cleaned.replace(r"\(", "").replace(r"\)", "").strip()
        return rf"\[ {cleaned} \]"
    return cleaned

