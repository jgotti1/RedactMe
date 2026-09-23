"""Pixel check of redacted regions in a rebuilt output. stdin: PDF; argv[1]: JSON {page: [rects]}.
stdout: JSON {"min_dark": lowest fraction of near-black pixels across regions}."""
import json
import sys

if __name__ == "__main__":
    import resource

    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    try:
        import pymupdf

        pymupdf.TOOLS.mupdf_display_errors(False)
        regions = json.loads(sys.argv[1])
        lowest = 1.0
        lowest_page = None
        with pymupdf.open(stream=sys.stdin.buffer.read(), filetype="pdf") as doc:
            for number, rects in regions.items():
                page = doc[int(number) - 1]
                pix = page.get_pixmap(dpi=100, colorspace=pymupdf.csGRAY)
                samples = pix.samples  # Obtain the full buffer once, not once per pixel row.
                scale = 100 / 72
                for x0, y0, x1, y1 in rects:
                    # inset by 1pt so anti-aliased edges do not count
                    ix0, iy0 = int((x0 + 1) * scale), int((y0 + 1) * scale)
                    ix1, iy1 = int((x1 - 1) * scale), int((y1 - 1) * scale)
                    ix1, iy1 = max(ix1, ix0 + 1), max(iy1, iy0 + 1)
                    total = dark = 0
                    for y in range(max(iy0, 0), min(iy1, pix.height)):
                        row = samples[y * pix.stride + max(ix0, 0): y * pix.stride + min(ix1, pix.width)]
                        total += len(row)
                        dark += sum(1 for v in row if v < 40)
                    fraction = dark / total if total else 0.0
                    if fraction < lowest:
                        lowest, lowest_page = fraction, int(number)
        sys.stdout.write(json.dumps({"min_dark": lowest, "page": lowest_page}))
    except Exception:
        sys.exit(1)
