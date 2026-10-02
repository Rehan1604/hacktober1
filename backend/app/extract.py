import io
from pathlib import Path

import pdfplumber
from PIL import Image, ImageOps

MAX_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 10
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


class ExtractError(Exception):
    pass


class OCRUnavailable(ExtractError):
    pass


def _ocr(data: bytes) -> str:
    try:
        import pytesseract
    except ImportError as e:
        raise OCRUnavailable("OCR library is not installed.") from e
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img).convert("L")  # fix phone rotation, grayscale
        img.thumbnail((2400, 2400))
    except Exception as e:
        raise ExtractError("Could not open this image.") from e
    try:
        langs = pytesseract.get_languages()
        lang = "eng+hin" if "hin" in langs else "eng"
        return pytesseract.image_to_string(img, lang=lang)
    except pytesseract.TesseractNotFoundError as e:
        raise OCRUnavailable("The OCR engine (Tesseract) is not installed on the server.") from e


def extract_text(filename: str, data: bytes) -> tuple[str, str]:
    """Return (text, source_type)."""
    if len(data) > MAX_BYTES:
        raise ExtractError("File is larger than 10 MB.")
    ext = Path(filename or "").suffix.lower()

    if ext == ".txt":
        return data.decode("utf-8", errors="replace"), "text"

    if ext == ".pdf":
        try:
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages[:MAX_PDF_PAGES]]
        except Exception as e:
            raise ExtractError("Could not read this PDF.") from e
        text = "\n".join(pages).strip()
        if len(text) < 20:
            raise ExtractError(
                "This PDF has no readable text (it may be a scan). Try a photo of it instead."
            )
        return text, "pdf"

    if ext in IMAGE_EXT:
        text = _ocr(data).strip()
        if len(text) < 20:
            raise ExtractError("Could not read any text from this image. Try a clearer, brighter photo.")
        return text, "image"

    raise ExtractError("Unsupported file type. Use a PDF, a photo (JPG/PNG) or a .txt file.")