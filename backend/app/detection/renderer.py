"""Short-lived page preview renderer. stdin: PDF; argv: page number, dpi. stdout: PNG."""
import sys


if __name__ == "__main__":
    import resource

    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    try:
        import pymupdf

        pymupdf.TOOLS.mupdf_display_errors(False)
        number, dpi = int(sys.argv[1]), min(max(int(sys.argv[2]), 50), 150)
        with pymupdf.open(stream=sys.stdin.buffer.read(), filetype="pdf") as doc:
            sys.stdout.buffer.write(doc[number - 1].get_pixmap(dpi=dpi).tobytes("png"))
    except Exception:
        sys.exit(1)
