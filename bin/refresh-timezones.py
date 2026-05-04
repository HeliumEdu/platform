#!/usr/bin/env python3

"""
Refresh the IANA timezone allow-list across platform and frontend.

Computes the union of:

* ``pytz.common_timezones`` (the canonical curated subset, refreshed with the
  pinned pytz release in ``requirements.txt``), and
* every IANA tz identifier already on disk in the target files.

Writes the result to:

* ``projects/platform/helium/common/timezones.py`` — ``TIME_ZONE_CHOICES``
  grouped by region for Django ``CharField(choices=...)``.
* ``projects/frontend/lib/utils/time_zone_constants.dart`` — flat ``all`` list
  consumed by the frontend dropdown.

Union-with-existing is what guarantees backwards compatibility: any zone we
have ever shipped stays in the validation set, even if pytz later drops it as
a deprecated alias. To prune, edit the source files manually.
"""

import argparse
import re
from pathlib import Path

import pytz

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_PLATFORM_FILE = _REPO_ROOT / "helium" / "common" / "timezones.py"
_DEFAULT_FRONTEND_FILE = (
    _REPO_ROOT.parent / "frontend" / "lib" / "utils" / "time_zone_constants.dart"
)

# Matches an IANA tz identifier in single quotes (must contain a '/').
_TZ_PATTERN = re.compile(r"'([A-Za-z]+(?:/[A-Za-z][A-Za-z0-9_+\-]*)+)'")


def _extract_zones(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(_TZ_PATTERN.findall(path.read_text()))


def _label_for(tz: str) -> str:
    parts = tz.split("/")
    if len(parts) <= 2:
        return parts[-1]
    return " - ".join(parts[1:])


def _group_by_region(zones: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for tz in zones:
        region = tz.split("/", 1)[0]
        groups.setdefault(region, []).append(tz)
    for region in groups:
        groups[region].sort()
    return dict(sorted(groups.items()))


def _autogen_banner_py(pytz_version: str) -> str:
    return (
        "# AUTO-GENERATED — DO NOT EDIT.\n"
        "# Refreshed periodically from IANA tzdata via:\n"
        "#   platform/bin/refresh-timezones.py\n"
    )


def _autogen_banner_dart(pytz_version: str) -> str:
    return (
        "// AUTO-GENERATED — DO NOT EDIT.\n"
        "// Refreshed periodically from IANA tzdata via:\n"
        "//   platform/bin/refresh-timezones.py\n"
    )


def _render_platform(zones: list[str], pytz_version: str) -> str:
    groups = _group_by_region(zones)
    lines = [
        '__copyright__ = "Copyright (c) 2025 Helium Edu"',
        '__license__ = "MIT"',
        "",
        _autogen_banner_py(pytz_version).rstrip(),
        "",
        "TIME_ZONE_CHOICES = (",
    ]
    for region, tzs in groups.items():
        lines.append(f"    ('{region}', [")
        for tz in tzs:
            lines.append(f"        ('{tz}', '{_label_for(tz)}'),")
        lines.append("    ]),")
    lines.append(")")
    lines.append("")
    return "\n".join(lines)


def _render_frontend(zones: list[str], pytz_version: str) -> str:
    groups = _group_by_region(zones)
    lines = [
        "// Copyright (c) 2025 Helium Edu",
        "//",
        "// This source code is licensed under the MIT license found in the",
        "// LICENSE file in the root directory of this source tree.",
        "//",
        "// For details regarding the license, please refer to the LICENSE file.",
        "",
        _autogen_banner_dart(pytz_version).rstrip(),
        "",
        "import 'package:heliumapp/data/models/drop_down_item.dart';",
        "",
        "class TimeZoneConstants {",
        "  static final List<String> all = [",
    ]
    region_items = list(groups.items())
    for idx, (region, tzs) in enumerate(region_items):
        lines.append(f"    // {region}")
        for tz in tzs:
            lines.append(f"    '{tz}',")
        if idx < len(region_items) - 1:
            lines.append("")
    lines.extend([
        "  ];",
        "",
        "  static String _humanize(String tz) =>",
        "      tz.replaceAll('_', ' ').replaceAll('/', ' / ');",
        "",
        "  static final List<DropDownItem<String>> items = List.generate(",
        "    all.length,",
        "    (i) => DropDownItem(id: i, value: all[i], label: _humanize(all[i])),",
        "  );",
        "}",
        "",
    ])
    return "\n".join(lines)


def refresh(platform_file: Path, frontend_file: Path) -> tuple[int, int]:
    canonical = set(pytz.common_timezones)
    legacy = _extract_zones(platform_file) | _extract_zones(frontend_file)
    union = canonical | legacy
    zones = sorted(union)

    platform_file.parent.mkdir(parents=True, exist_ok=True)
    frontend_file.parent.mkdir(parents=True, exist_ok=True)
    platform_file.write_text(_render_platform(zones, pytz.__version__))
    frontend_file.write_text(_render_frontend(zones, pytz.__version__))

    return len(zones), len(legacy - canonical)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform-file", type=Path, default=_DEFAULT_PLATFORM_FILE)
    parser.add_argument("--frontend-file", type=Path, default=_DEFAULT_FRONTEND_FILE)
    args = parser.parse_args()

    total, legacy_only = refresh(args.platform_file, args.frontend_file)
    print(f"Wrote {total} zones ({legacy_only} preserved as deprecated aliases) to:")
    print(f"  {args.platform_file}")
    print(f"  {args.frontend_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
