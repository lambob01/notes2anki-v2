from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


class DocumentError(RuntimeError):
    pass


def find_libreoffice() -> str | None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        return soffice
    if os.name == "nt":
        for candidate in (
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ):
            if Path(candidate).exists():
                return candidate
    return None


def pdf_to_images(pdf_path: Path, out_dir: Path, dpi: int) -> list[Path]:
    try:
        import fitz  # type: ignore
    except ImportError as exc:
        raise DocumentError("PyMuPDF is not installed. Install dependencies with: pip install -e .") from exc

    fitz.TOOLS.mupdf_display_errors(False)
    images: list[Path] = []
    try:
        document = fitz.open(str(pdf_path))
        matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        for index, page in enumerate(document):
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image_path = out_dir / f"slide-{index:03d}.jpg"
            pixmap.save(str(image_path))
            images.append(image_path)
    except Exception as exc:
        raise DocumentError(f"Could not render PDF '{pdf_path.name}': {exc}") from exc
    return images


def pptx_to_images(pptx_path: Path, out_dir: Path, dpi: int) -> list[Path]:
    soffice = find_libreoffice()
    if soffice:
        try:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx_path)],
                check=True,
                capture_output=True,
                timeout=180,
            )
            rendered_pdf = out_dir / f"{pptx_path.stem}.pdf"
            if rendered_pdf.exists():
                images = pdf_to_images(rendered_pdf, out_dir, dpi)
                if images:
                    return images
        except Exception:
            # Fall through to python-pptx fallback. It is lower fidelity but lets the tool continue.
            pass

    return _pptx_text_fallback_to_images(pptx_path, out_dir)


def _pptx_text_fallback_to_images(pptx_path: Path, out_dir: Path) -> list[Path]:
    try:
        from pptx import Presentation
    except ImportError as exc:
        raise DocumentError("python-pptx is not installed. Install dependencies with: pip install -e .") from exc

    try:
        presentation = Presentation(str(pptx_path))
        images: list[Path] = []
        for index, slide in enumerate(presentation.slides):
            image = Image.new("RGB", (1280, 720), "white")
            draw = ImageDraw.Draw(image)
            y = 40
            for line in _slide_text_lines(slide):
                draw.text((40, y), line[:180], fill="black")
                y += 30
                if y > 680:
                    break
            image_path = out_dir / f"slide-{index:03d}.jpg"
            image.save(image_path, "JPEG", quality=90)
            images.append(image_path)
        return images
    except Exception as exc:
        raise DocumentError(f"Could not render PPTX '{pptx_path.name}': {exc}") from exc


def normalize_image_to_jpeg(image_path: Path, out_dir: Path) -> Path:
    try:
        with Image.open(image_path) as image:
            converted = image.convert("RGB")
            out_path = out_dir / f"{image_path.stem}.jpg"
            converted.save(out_path, "JPEG", quality=95)
            return out_path
    except Exception as exc:
        raise DocumentError(f"Could not read image '{image_path.name}': {exc}") from exc


def get_slide_notes(pptx_path: Path, slide_index: int) -> str:
    if pptx_path.suffix.lower() != ".pptx":
        return ""
    try:
        from pptx import Presentation

        presentation = Presentation(str(pptx_path))
        slide = presentation.slides[slide_index]
        if not slide.has_notes_slide:
            return ""
        frame = slide.notes_slide.notes_text_frame
        if frame is None:
            return ""
        return "\n".join(p.text.strip() for p in frame.paragraphs if p.text.strip())
    except Exception:
        return ""


def looks_like_title_or_blank(pptx_path: Path, slide_index: int) -> bool:
    if pptx_path.suffix.lower() != ".pptx":
        return False
    try:
        from pptx import Presentation

        presentation = Presentation(str(pptx_path))
        slide = presentation.slides[slide_index]
        text_chunks = list(_slide_text_lines(slide))
        words = sum(len(chunk.split()) for chunk in text_chunks)
        if words < 6:
            return True

        has_non_title_shape = False
        for shape in slide.shapes:
            placeholder = getattr(shape, "placeholder_format", None)
            if placeholder is None:
                has_non_title_shape = True
                continue
            if getattr(placeholder, "idx", None) not in (0, 1):
                has_non_title_shape = True
        return not has_non_title_shape and len(text_chunks) <= 2
    except Exception:
        return False


def get_document_text_summary(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return _pdf_text(path)
    if path.suffix.lower() == ".pptx":
        return _pptx_text(path)
    return ""


def _pdf_text(path: Path) -> str:
    try:
        import fitz  # type: ignore

        fitz.TOOLS.mupdf_display_errors(False)
        document = fitz.open(str(path))
        parts = []
        for page_number, page in enumerate(document, start=1):
            text = page.get_text().strip()
            if text:
                parts.append(f"--- Slide {page_number} ---\n{text}")
        return "\n\n".join(parts)[:80000]
    except Exception:
        return ""


def _pptx_text(path: Path) -> str:
    try:
        from pptx import Presentation

        presentation = Presentation(str(path))
        parts = []
        for index, slide in enumerate(presentation.slides, start=1):
            text = "\n".join(_slide_text_lines(slide))
            notes = get_slide_notes(path, index - 1)
            combined = text
            if notes:
                combined = f"{combined}\n\n[Speaker Notes]: {notes}".strip()
            if combined:
                parts.append(f"--- Slide {index} ---\n{combined}")
        return "\n\n".join(parts)[:80000]
    except Exception:
        return ""


def _slide_text_lines(slide: object) -> list[str]:
    lines: list[str] = []
    for shape in getattr(slide, "shapes", []):
        if getattr(shape, "has_text_frame", False):
            for paragraph in shape.text_frame.paragraphs:
                text = paragraph.text.strip()
                if text:
                    lines.append(text)
    return lines

