"""PDF text extraction helpers for a future upload endpoint.

No API route currently accepts PDFs. Keep this module internal until upload
storage, validation, and request schemas are wired together.
"""

import fitz


def extract_text_from_bytes(pdf_bytes: bytes) -> str:
    text = ""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for page in doc:
        text += page.get_text()
    doc.close()
    return text.strip()
