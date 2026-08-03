from argparse import ArgumentParser
from html import escape
from pathlib import Path

import fitz

DEFAULT_OUTPUT = Path(__file__).with_name("demo-financial-results.pdf")
DEMO_TEXT = """MARKETLENS SYNTHETIC DEMO ANNOUNCEMENT

This document is not an exchange announcement and does not describe a real company.

MarketLens Demo Industries Limited reports synthetic quarterly revenue of
₹1,250 crore for the period ended 30 June 2026, compared with ₹1,100 crore in
the synthetic comparison period. Synthetic operating margin was 18.5%.

The board noted that these values exist only to demonstrate PDF extraction,
structured analysis, source citations, limitations, and the educational disclaimer.
"""


def generate_demo_pdf(output_path: Path, *, force: bool = False) -> None:
    if output_path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite existing file: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open()
    try:
        page = document.new_page()
        text_rect = fitz.Rect(64, 64, page.rect.width - 64, page.rect.height - 64)
        html = (
            "<div style='font-family: sans-serif; font-size: 11pt; line-height: 1.4; "
            "font-variant-ligatures: none;'>"
            f"{escape(DEMO_TEXT).replace(chr(10), '<br>')}"
            "</div>"
        )
        page.insert_htmlbox(text_rect, html)
        document.save(output_path)
    finally:
        document.close()


def main() -> int:
    parser = ArgumentParser(description="Generate a synthetic MarketLens demo PDF")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    arguments = parser.parse_args()
    try:
        generate_demo_pdf(arguments.output, force=arguments.force)
    except FileExistsError as error:
        parser.error(str(error))
    print(f"Created synthetic demo PDF: {arguments.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
