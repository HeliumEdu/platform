#!/usr/bin/env python3

"""
Refresh the IANA timezone allow-list across platform and frontend.

Computes the union of:

* the canonical zones in ``zone.tab`` of the ``tzdata`` release pinned in
  ``bin/requirements.txt`` (the only zone source the platform resolves against,
  see ``CommonConfig.init_time_zones``), plus the
  region-less ``UTC`` and ``GMT``, and
* every IANA tz identifier already on disk in the target files.

Writes the result to:

* ``projects/platform/helium/common/timezones.py`` — ``TIME_ZONE_CHOICES``
  grouped by region for Django ``CharField(choices=...)``, and
  ``COUNTRY_BY_TIME_ZONE`` mapping each zone to its ISO 3166-1 alpha-2
  country from ``zone.tab`` (region-less zones have no country).
* ``projects/frontend/lib/utils/time_zone_constants.dart`` — flat ``all`` list
  consumed by the frontend dropdown, plus an ``aliases`` map of IANA link names
  to the selectable zone they resolve to.

The allow-list is canonical-only on purpose: it populates a picker, where listing
both ``Asia/Calcutta`` and ``Asia/Kolkata`` would be noise. Device APIs, however,
report whatever the device is set to and do not canonicalize, so the ``aliases``
map is what lets a reported link name be translated into something the platform
will accept instead of silently falling back to UTC. Aliases resolve to the first
selectable zone along their IANA Link chain, since IANA consolidates zones and the
end of a chain can pass by the zone a user would recognize. Link records are the
only authoritative alias source: matching UTC offsets maps ``Asia/Saigon`` onto
``Asia/Bangkok``, and comparing TZif bytes can't break ties between zones that are
themselves links.

Countries come from ``zone.tab``, which lists every canonical zone with exactly one
country; ``zone1970.tab`` merges countries that share a zone.

Union-with-existing is what guarantees backwards compatibility: any zone we
have ever shipped stays in the validation set, even if IANA later drops it as
a deprecated alias, and a retired Link still maps devices that report it.
"""

import re
import sys
from importlib import resources
from pathlib import Path

import tzdata

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_PLATFORM_FILE = _REPO_ROOT / "helium" / "common" / "timezones.py"
_DEFAULT_FRONTEND_FILE = (
    _REPO_ROOT.parent / "frontend" / "lib" / "utils" / "time_zone_constants.dart"
)
_DEFAULT_FRONTEND_ALIAS_FILE = (
    _REPO_ROOT.parent / "frontend" / "lib" / "utils" / "time_zone_aliases.dart"
)

_REGIONLESS_ZONES = {"GMT", "UTC"}

_TZ_PATTERN = re.compile(r"'([A-Za-z]+(?:/[A-Za-z][A-Za-z0-9_+\-]*)+)'")
_ALIAS_PATTERN = re.compile(
    r"'([A-Za-z]+(?:[/-][A-Za-z0-9_+\-]+)*)':\s*'([A-Za-z]+(?:[/-][A-Za-z0-9_+\-]+)*)'"
)


def _extract_zones(path: Path) -> set[str]:
    return set(_TZ_PATTERN.findall(path.read_text(encoding="utf-8")))


def _read_country_by_zone() -> dict[str, str]:
    country_by_zone: dict[str, str] = {}
    zone_tab = (resources.files("tzdata.zoneinfo") / "zone.tab").read_text(encoding="utf-8")
    for raw in zone_tab.splitlines():
        if not raw or raw.startswith("#"):
            continue
        country, _, zone = raw.split("\t")[:3]
        country_by_zone[zone] = country
    return country_by_zone


def _read_iana_links() -> dict[str, str]:
    links: dict[str, str] = {}
    zi = (resources.files("tzdata.zoneinfo") / "tzdata.zi").read_text(encoding="utf-8")
    for raw in zi.splitlines():
        if not raw.startswith("L "):
            continue
        _, target, alias = raw.split()
        links[alias] = target
    return links


def _resolve_aliases(links: dict[str, str], selectable: set[str]) -> dict[str, str]:
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


def _extract_alias_pairs(path: Path) -> dict[str, str]:
    return dict(_ALIAS_PATTERN.findall(path.read_text(encoding="utf-8")))


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


def _render_platform(zones: list[str], country_by_zone: dict[str, str], iana_release: str) -> str:
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
    lines.append("COUNTRY_BY_TIME_ZONE = {")
    for tz in zones:
        if tz in country_by_zone:
            lines.append(f"    '{tz}': '{country_by_zone[tz]}',")
    lines.append("}")
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
        "/// so an alias will not be found in `TimeZoneConstants.all`.",
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
    iana_release = tzdata.IANA_VERSION
    links = _read_iana_links()

    country_by_zone = _read_country_by_zone()
    canonical = set(country_by_zone) | _REGIONLESS_ZONES
    on_disk = _extract_zones(platform_file) | _extract_zones(frontend_file)
    union = canonical | on_disk
    zones = sorted(union)

    aliases = {**_extract_alias_pairs(frontend_alias_file), **_resolve_aliases(links, union)}
    aliases = {a: c for a, c in aliases.items() if c in union and a not in union}

    platform_file.write_text(_render_platform(zones, country_by_zone, iana_release), encoding="utf-8")
    frontend_file.write_text(_render_frontend(zones, iana_release), encoding="utf-8")
    frontend_alias_file.write_text(_render_frontend_aliases(aliases, iana_release), encoding="utf-8")

    return len(zones), len(on_disk - canonical), len(aliases)


def main() -> int:
    total, deprecated_only, alias_count = refresh(
        _DEFAULT_PLATFORM_FILE, _DEFAULT_FRONTEND_FILE, _DEFAULT_FRONTEND_ALIAS_FILE
    )
    print(f"Wrote {total} zones ({deprecated_only} preserved as deprecated aliases) "
          f"and {alias_count} alias mappings to:")
    print(f"  {_DEFAULT_PLATFORM_FILE}")
    print(f"  {_DEFAULT_FRONTEND_FILE}")
    print(f"  {_DEFAULT_FRONTEND_ALIAS_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
