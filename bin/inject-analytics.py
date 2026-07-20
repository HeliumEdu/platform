#!/usr/bin/env python3

"""
Inject (or strip) the Google Analytics gtag.js snippet into a pre-built static
HTML file at build time.

Mirrors the frontend's Sentry pattern: the public measurement ID is hardcoded
in source (analogous to ``SENTRY_DSN`` in ``lib/core/sentry_service.dart``),
and a presence-style env var (``ANALYTICS_ENABLED``, analogous to
``ifdef SENTRY_DIST``) gates whether the snippet is included in the artifact.
"""

__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import os
import sys

MARKER = "<!-- ANALYTICS -->"
GA_MEASUREMENT_ID = "G-6XR4WF9NY4"


def build_snippet() -> str:
    return (
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>\n'
        f'  <script>\n'
        f'    window.dataLayer = window.dataLayer || [];\n'
        f'    function gtag(){{dataLayer.push(arguments);}}\n'
        f"    gtag('js', new Date());\n"
        f"    gtag('config', '{GA_MEASUREMENT_ID}');\n"
        f'  </script>'
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: inject-analytics.py <html-file>", file=sys.stderr)
        return 1

    target = sys.argv[1]
    enabled = os.environ.get("ANALYTICS_ENABLED", "").strip()
    replacement = build_snippet() if enabled else ""

    with open(target, "r") as f:
        content = f.read()
    with open(target, "w") as f:
        f.write(content.replace(MARKER, replacement))

    return 0


if __name__ == "__main__":
    sys.exit(main())
