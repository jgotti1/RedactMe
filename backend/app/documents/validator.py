"""Short-lived PDF parser process. Never emit parser diagnostics or document data."""
import json
import re
import sys

MAX_BYTES = 20 * 1024 * 1024
MAX_PAGES = 200


def validate(data: bytes) -> dict:
    import pymupdf

    pymupdf.TOOLS.mupdf_display_errors(False)
    pymupdf.TOOLS.mupdf_display_warnings(False)
    pymupdf.TOOLS.reset_mupdf_warnings()
    if not data or len(data) > MAX_BYTES:
        return {"error": "size"}
    if not re.match(rb"%PDF-(?:1\.[0-7]|2\.0)[\r\n]", data) or not data.rstrip().endswith(b"%%EOF"):
        return {"error": "invalid"}
    try:
        with pymupdf.open(stream=data, filetype="pdf") as document:
            if document.needs_pass or document.is_encrypted:
                return {"error": "encrypted"}
            if not document.is_pdf or document.is_repaired:
                return {"error": "invalid"}
            count = document.page_count
            if count < 1 or count > MAX_PAGES:
                return {"error": "pages"}
            for page in document:
                if page.rect.is_empty or page.rect.is_infinite:
                    return {"error": "invalid"}
                # Interpret page streams without rendering, extracting text or scanning PII.
                display = page.get_displaylist()
                del display
            if pymupdf.TOOLS.mupdf_warnings():
                return {"error": "invalid"}
            return {"page_count": count}
    except Exception:
        return {"error": "invalid"}


if __name__ == "__main__":
    import resource

    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    # macOS does not reliably support RLIMIT_AS; production Linux does.
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
    try:
        result = validate(sys.stdin.buffer.read(MAX_BYTES + 1))
    except Exception:
        result = {"error": "invalid"}
    sys.stdout.write(json.dumps(result))
