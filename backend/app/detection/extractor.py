"""Short-lived PDF text/layout extraction process. Never emit diagnostics or document data."""
import json
import sys


def extract(data: bytes) -> dict:
    import pymupdf

    pymupdf.TOOLS.mupdf_display_errors(False)
    pymupdf.TOOLS.mupdf_display_warnings(False)
    pages = []
    with pymupdf.open(stream=data, filetype="pdf") as document:
        for number, page in enumerate(document, start=1):
            words = [[round(w[0], 2), round(w[1], 2), round(w[2], 2), round(w[3], 2), w[4], w[5], w[6]]
                     for w in page.get_text("words")]
            page_area = max(page.rect.width * page.rect.height, 1)
            image_area = 0.0
            for info in page.get_image_info():
                rect = pymupdf.Rect(info["bbox"]) & page.rect
                image_area += 0 if rect.is_empty else rect.width * rect.height
            pages.append({"page": number, "width": page.rect.width, "height": page.rect.height,
                          "words": words, "image_fraction": min(image_area / page_area, 1.0)})
    return {"pages": pages}


if __name__ == "__main__":
    import resource

    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024,) * 2)
    try:
        result = extract(sys.stdin.buffer.read())
    except Exception:
        result = {"error": "invalid"}
    sys.stdout.write(json.dumps(result))
