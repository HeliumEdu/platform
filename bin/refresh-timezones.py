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
  consumed by the frontend dropdown, plus an ``aliases`` map of IANA link names
  to the selectable zone they resolve to.

The allow-list is canonical-only on purpose: it populates a picker, where listing
both ``Asia/Calcutta`` and ``Asia/Kolkata`` would be noise. Device APIs, however,
report whatever the device is set to and do not canonicalize, so the ``aliases``
map is what lets a reported link name be translated into something the platform
will accept instead of silently falling back to UTC.

Union-with-existing is what guarantees backwards compatibility: any zone we
have ever shipped stays in the validation set, even if pytz later drops it as
a deprecated alias. To prune, edit the source files manually.
"""

import argparse
import io
import re
import tarfile
import urllib.request
from pathlib import Path

_IANA_RELEASE_URL = "https://data.iana.org/time-zones/releases/tzdata{release}.tar.gz"


_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_PLATFORM_FILE = _REPO_ROOT / "helium" / "common" / "timezones.py"
_DEFAULT_FRONTEND_FILE = (
    _REPO_ROOT.parent / "frontend" / "lib" / "utils" / "time_zone_constants.dart"
)
_DEFAULT_FRONTEND_ALIAS_FILE = (
    _REPO_ROOT.parent / "frontend" / "lib" / "utils" / "time_zone_aliases.dart"
)

# Matches an IANA tz identifier in single quotes (must contain a '/').
_TZ_PATTERN = re.compile(r"'([A-Za-z]+(?:/[A-Za-z][A-Za-z0-9_+\-]*)+)'")


def _extract_zones(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(_TZ_PATTERN.findall(path.read_text()))


def _fetch_iana_links(release: str) -> dict[str, str]:
    """Return ``{alias: target}`` from the ``backward`` file of IANA ``release``.

    Link records are the only authoritative source. Matching UTC offsets instead maps
    ``Asia/Saigon`` onto ``Asia/Bangkok``; comparing TZif bytes cannot break ties
    between zones that are themselves links.
    """
    url = _IANA_RELEASE_URL.format(release=release)
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = response.read()

    links: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        backward_member = archive.extractfile("backward")
        if backward_member is None:
            raise RuntimeError("IANA tzdata archive has no 'backward' file")
        for raw in backward_member.read().decode().splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line.startswith("Link"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                # Link  <target>  <alias>
                links[parts[2]] = parts[1]

    return links


def _resolve_aliases(links: dict[str, str], selectable: set[str]) -> dict[str, str]:
    """Map each alias onto the first zone in ``selectable`` along its Link chain.

    Stopping early matters: IANA consolidates zones, so walking a chain to its end
    can pass right by the zone a user would recognize.
    """
    resolved: dict[str, str] = {}
    for alias in links:
        if alias in selectable:
            continue
        seen: set[str] = set()
        current = alias
        while current in links and current not in seen:
            seen.add(current)
            current = links[current]
            if current in selectable:
                resolved[alias] = current
                break
    return resolved


_ALIAS_PATTERN = re.compile(
    r"'([A-Za-z]+(?:[/-][A-Za-z0-9_+\-]+)*)':\s*'([A-Za-z]+(?:[/-][A-Za-z0-9_+\-]+)*)'"
)


def _extract_alias_pairs(path: Path) -> dict[str, str]:
    """Alias pairs already emitted to ``path``, unioned in so a retired IANA Link
    does not send devices still reporting it back to the UTC fallback."""
    if not path.exists():
        return {}
    return dict(_ALIAS_PATTERN.findall(path.read_text()))


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


def _autogen_banner_py(iana_release: str) -> str:
    return (
        "# AUTO-GENERATED — DO NOT EDIT.\n"
        "# Refreshed periodically from IANA tzdata via:\n"
        "#   platform/bin/refresh-timezones.py\n"
        f"# IANA release: {iana_release}\n"
    )


def _autogen_banner_dart(iana_release: str) -> str:
    return (
        "// AUTO-GENERATED — DO NOT EDIT.\n"
        "// Refreshed periodically from IANA tzdata via:\n"
        "//   platform/bin/refresh-timezones.py\n"
        f"// IANA release: {iana_release}\n"
    )


def _render_platform(zones: list[str], iana_release: str) -> str:
    groups = _group_by_region(zones)
    lines = [
        _autogen_banner_py(iana_release).rstrip(),
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


def _render_frontend(zones: list[str], iana_release: str) -> str:
    groups = _group_by_region(zones)
    lines = [
        _autogen_banner_dart(iana_release).rstrip(),
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


def _render_frontend_aliases(aliases: dict[str, str], iana_release: str) -> str:
    lines = [
        _autogen_banner_dart(iana_release).rstrip(),
        "",
        "/// IANA link (alias) names mapped to the selectable zone they point at.",
        "///",
        "/// Device APIs report whatever the device is set to without canonicalizing,",
        "/// so a legacy alias will not be found in `TimeZoneConstants.all`.",
        "///",
        "/// Kept out of `time_zone_constants.dart`: the generator unions its output",
        "/// with what is on disk, and would read these back as shipped zones.",
        "class TimeZoneAliases {",
        "  TimeZoneAliases._();",
        "",
        "  static const Map<String, String> all = {",
    ]
    for alias in sorted(aliases):
        lines.append(f"    '{alias}': '{aliases[alias]}',")
    lines.extend(["  };", "}", ""])
    return "\n".join(lines)


def refresh(
    platform_file: Path, frontend_file: Path, frontend_alias_file: Path
) -> tuple[int, int, int]:
    # Imported lazily so the pure helpers stay testable without pytz installed.
    import pytz

    # Pinned to pytz's tzdata so links and zones come from one IANA release.
    iana_release = pytz.OLSON_VERSION
    links = _fetch_iana_links(iana_release)

    canonical = set(pytz.common_timezones)
    legacy = _extract_zones(platform_file) | _extract_zones(frontend_file)
    union = canonical | legacy
    zones = sorted(union)

    # Fresh derivation wins on conflict; retired Links carry forward.
    aliases = {**_extract_alias_pairs(frontend_alias_file), **_resolve_aliases(links, union)}
    aliases = {a: c for a, c in aliases.items() if c in union and a not in union}

    platform_file.parent.mkdir(parents=True, exist_ok=True)
    frontend_file.parent.mkdir(parents=True, exist_ok=True)
    frontend_alias_file.parent.mkdir(parents=True, exist_ok=True)
    platform_file.write_text(_render_platform(zones, iana_release))
    frontend_file.write_text(_render_frontend(zones, iana_release))
    frontend_alias_file.write_text(_render_frontend_aliases(aliases, iana_release))

    return len(zones), len(legacy - canonical), len(aliases)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform-file", type=Path, default=_DEFAULT_PLATFORM_FILE)
    parser.add_argument("--frontend-file", type=Path, default=_DEFAULT_FRONTEND_FILE)
    parser.add_argument(
        "--frontend-alias-file", type=Path, default=_DEFAULT_FRONTEND_ALIAS_FILE
    )
    args = parser.parse_args()

    total, legacy_only, alias_count = refresh(
        args.platform_file, args.frontend_file, args.frontend_alias_file
    )
    print(f"Wrote {total} zones ({legacy_only} preserved as deprecated aliases) "
          f"and {alias_count} alias mappings to:")
    print(f"  {args.platform_file}")
    print(f"  {args.frontend_file}")
    print(f"  {args.frontend_alias_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
