"""Short-lived OCR process: renders pages and runs Tesseract. Never emit diagnostics or document data.
Modular: replace this script (same stdin/stdout contract) to swap OCR engines."""
import csv
import io
import json
import os
import subprocess
import sys

DPI = 200
MIN_WORD_CONF = 0


def ocr_page(page, tesseract):
    import pymupdf

    pix = page.get_pixmap(dpi=DPI)
    scale = 72 / DPI
    # The page image goes to Tesseract over stdin; document pixels are never written to disk.
    proc = subprocess.run([tesseract, "stdin", "stdout", "-l", "eng", "--psm", "6", "tsv"],
                          input=pix.tobytes("png"), capture_output=True, timeout=90, check=True,
                          env={"PATH": os.pathsep.join([os.path.dirname(tesseract), os.defpath]),
                               "OMP_THREAD_LIMIT": "1"})
    words, confs = [], []
    for row in csv.DictReader(io.StringIO(proc.stdout.decode("utf-8", "replace")), delimiter="\t", quoting=csv.QUOTE_NONE):
        text = (row.get("text") or "").strip()
        try:
            conf = float(row["conf"])
        except (KeyError, ValueError):
            continue
        if not text or conf < MIN_WORD_CONF:
            continue
        x, y, w, h = (int(row[k]) for k in ("left", "top", "width", "height"))
        words.append([round(x * scale, 2), round(y * scale, 2), round((x + w) * scale, 2),
                      round((y + h) * scale, 2), text, int(row["block_num"]) * 1000 + int(row["par_num"]),
                      int(row["line_num"])])
        confs.append(conf)
    return {"words": words, "confidence": (sum(confs) / len(confs)) if confs else 0.0}


def run(data: bytes, page_numbers: list, tesseract: str) -> dict:
    import pymupdf

    pymupdf.TOOLS.mupdf_display_errors(False)
    out = {}
    with pymupdf.open(stream=data, filetype="pdf") as document:
        for n in page_numbers:
            out[str(n)] = ocr_page(document[n - 1], tesseract)
    return {"pages": out}


if __name__ == "__main__":
    import resource

    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        payload = json.loads(sys.argv[1])
        result = run(sys.stdin.buffer.read(), payload["pages"], payload["tesseract"])
    except Exception:
        result = {"error": "ocr"}
    sys.stdout.write(json.dumps(result))
