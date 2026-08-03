import fitz


def make_pdf_bytes(texts: list[str]) -> bytes:
    document = fitz.open()
    try:
        for text in texts:
            page = document.new_page()
            if text:
                page.insert_text((72, 72), text)
        return document.tobytes()
    finally:
        document.close()
