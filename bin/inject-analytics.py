#!/usr/bin/env python3

"""
Inject (or strip) the Google Analytics gtag.js snippet at the ``<!-- ANALYTICS -->`` marker of a pre-built HTML file.

The snippet is included only when ``ANALYTICS_ENABLED`` is set, and loads only on the production host, so one image
serves every environment.
"""

import argparse
import os
import sys

MARKER = "<!-- ANALYTICS -->"
GA_MEASUREMENT_ID = "G-6XR4WF9NY4"
PRODUCTION_HOSTNAME = "api.heliumedu.com"


def build_snippet() -> str:
    return (
        '<script>\n'
        f"    if (window.location.hostname === '{PRODUCTION_HOSTNAME}') {{\n"
        f"      var gtagScript = document.createElement('script');\n"
        '      gtagScript.async = true;\n'
        f"      gtagScript.src = 'https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}';\n"
        '      document.head.appendChild(gtagScript);\n'
        '      window.dataLayer = window.dataLayer || [];\n'
        f'      window.gtag = function () {{ window.dataLayer.push(arguments); }};\n'
        "      window.gtag('js', new Date());\n"
        f"      window.gtag('config', '{GA_MEASUREMENT_ID}');\n"
        f'    }}\n'
        '  </script>'
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html_file")
    target = parser.parse_args().html_file

    enabled = os.environ.get("ANALYTICS_ENABLED", "").strip()
    replacement = build_snippet() if enabled else ""

    with open(target, "r", encoding="utf-8") as f:
        content = f.read()
    with open(target, "w", encoding="utf-8") as f:
        f.write(content.replace(MARKER, replacement))

    return 0


if __name__ == "__main__":
    sys.exit(main())
