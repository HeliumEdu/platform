#!/usr/bin/env python3

"""
Inject (or strip) the Google Analytics gtag.js snippet into a pre-built static
HTML file at build time.

Mirrors the frontend's ``ifdef SENTRY_DIST`` pattern: when the
``GA_MEASUREMENT_ID`` env var is set, the snippet is baked into the artifact;
when unset (local dev, Docker, integration builds), the marker is stripped and
no metrics fire from the artifact at runtime.
"""

__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import os
import sys

MARKER = "<!-- ANALYTICS -->"


def build_snippet(ga_id: str) -> str:
    return (
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>\n'
        f'  <script>\n'
        f'    window.dataLayer = window.dataLayer || [];\n'
        f'    function gtag(){{dataLayer.push(arguments);}}\n'
        f"    gtag('js', new Date());\n"
        f"    gtag('config', '{ga_id}');\n"
        f'  </script>'
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: inject-analytics.py <html-file>", file=sys.stderr)
        return 1

    target = sys.argv[1]
    ga_id = os.environ.get("GA_MEASUREMENT_ID", "").strip()
    replacement = build_snippet(ga_id) if ga_id else ""

    with open(target, "r") as f:
        content = f.read()
    with open(target, "w") as f:
        f.write(content.replace(MARKER, replacement))

    return 0


if __name__ == "__main__":
    sys.exit(main())
