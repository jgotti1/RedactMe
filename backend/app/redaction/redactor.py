"""Short-lived redaction process: true removal of text/pixels, page rebuild for scanned pages,
and sanitization. stdin: 8-byte big-endian JSON length + JSON + PDF. stdout: redacted PDF bytes.
Never emit diagnostics or document data."""
import json
import struct
import sys

DPI = 200


def redact(data: bytes, plan: dict) -> bytes:
    import pymupdf

    pymupdf.TOOLS.mupdf_display_errors(False)
    rects = {int(k): v for k, v in plan["rects"].items()}
    rebuild = set(plan["rebuild_pages"])
    with pymupdf.open(stream=data, filetype="pdf") as source:
        for number, page_rects in rects.items():
            page = source[number - 1]
            for x0, y0, x1, y1 in page_rects:
                rect = pymupdf.Rect(x0, y0, x1, y1)
                if number in rebuild:
                    rect = rect + (-1, -1, 1, 1)  # pixel pages: small margin for anti-aliasing
                else:
                    trim = rect.height * 0.08  # avoid clipping glyphs of the adjacent line
                    rect = pymupdf.Rect(rect.x0, rect.y0 + trim, rect.x1, rect.y1 - trim)
                page.add_redact_annot(rect, fill=(0, 0, 0))
            # Removes underlying text, image pixels and touched vector graphics; not an overlay.
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS)
        with pymupdf.open() as out:
            for index, page in enumerate(source, start=1):
                if index in rebuild:
                    # Rasterize and rebuild so any original OCR text layer is discarded.
                    pix = page.get_pixmap(dpi=DPI)
                    fresh = out.new_page(width=page.rect.width, height=page.rect.height)
                    fresh.insert_image(fresh.rect, pixmap=pix)
                else:
                    out.insert_pdf(source, from_page=index - 1, to_page=index - 1, annots=False, links=False)
            out.set_metadata({})
            out.del_xml_metadata()
            out.set_toc([])
            out.scrub(metadata=True, xml_metadata=True, attached_files=True, embedded_files=True,
                      javascript=True, thumbnails=True, hidden_text=False, redactions=True)
            return out.tobytes(garbage=4, deflate=True, clean=True)  # full rewrite, no incremental history


if __name__ == "__main__":
    import resource

    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024,) * 2)
    try:
        raw = sys.stdin.buffer.read()
        (length,) = struct.unpack(">Q", raw[:8])
        plan = json.loads(raw[8:8 + length])
        sys.stdout.buffer.write(redact(raw[8 + length:], plan))
    except Exception:
        sys.exit(1)
