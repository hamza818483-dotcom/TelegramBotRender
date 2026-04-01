import fitz  # PyMuPDF
import io


def extract_text_from_pdf(pdf_bytes: bytes, page_start: int = 1, page_end: int = None) -> dict:
    """
    Extract text from PDF pages.
    Returns dict: {page_num: text}
    page_start and page_end are 1-based.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)

    if page_end is None or page_end > total_pages:
        page_end = total_pages

    page_start = max(1, page_start)
    page_end = min(page_end, total_pages)

    result = {}
    for i in range(page_start - 1, page_end):
        page = doc[i]
        text = page.get_text("text")
        result[i + 1] = text.strip()

    doc.close()
    return result


def get_pdf_page_count(pdf_bytes: bytes) -> int:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    count = len(doc)
    doc.close()
    return count


def get_pdf_first_page_image(pdf_bytes: bytes) -> bytes:
    """Get first page as PNG image bytes."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    mat = fitz.Matrix(1.5, 1.5)  # 1.5x zoom
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    doc.close()
    return img_bytes
