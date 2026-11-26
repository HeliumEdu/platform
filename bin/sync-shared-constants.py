#!/usr/bin/env python3

"""
Write the platform constants that the frontend and connector mirror, so they can't drift.

Reads ``helium/common/enums.py`` and writes:

* ``projects/frontend/lib/utils/grade_scale_constants.dart`` — the grade scale templates (``GRADE_SCALE_TEMPLATES``);
  names with words, and "Custom", are read from ``app_en.arb`` keys.
* ``projects/frontend/lib/utils/resource_constants.dart`` — resource status and condition labels
  (``RESOURCE_STATUS_CHOICES``, ``CONDITION_CHOICES``), read from ``app_en.arb`` keys. Fails, writing nothing, until
  ``app_en.arb`` holds each localized label's key with the platform's English text.
* ``projects/frontend/lib/utils/preferred_colors.dart`` — the course color palette (``PREFERRED_COLORS``).
* ``projects/connector/helium_connector/platform_enums.py`` — resource status and condition labels, the ungraded
  sentinels, the recurrence horizon, the grade scale preset names and ids, and the OAuth scopes.
"""

import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PROJECTS = _REPO_ROOT.parent
_FRONTEND_UTILS = _PROJECTS / "frontend" / "lib" / "utils"
_FRONTEND_GRADE_SCALES = _FRONTEND_UTILS / "grade_scale_constants.dart"
_FRONTEND_RESOURCES = _FRONTEND_UTILS / "resource_constants.dart"
_FRONTEND_COLORS = _FRONTEND_UTILS / "preferred_colors.dart"
_FRONTEND_ARB = _PROJECTS / "frontend" / "lib" / "l10n" / "app_en.arb"
_CONNECTOR_ENUMS = _PROJECTS / "connector" / "helium_connector" / "platform_enums.py"

_DART_BANNER = ("// AUTO-GENERATED — DO NOT EDIT.\n"
                "// Written from platform/helium/common/enums.py by:\n"
                "//   platform/bin/sync-shared-constants.py\n")
_PY_BANNER = ("# AUTO-GENERATED — DO NOT EDIT.\n"
              "# Written from platform/helium/common/enums.py by:\n"
              "#   platform/bin/sync-shared-constants.py\n")


def _dart_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'").replace("$", "\\$") + "'"


def _dart_number(value: float) -> str:
    return repr(float(value))


def _labels(choices: tuple[tuple[int, str], ...]) -> list[str]:
    labels = [label for _, label in sorted(choices)]
    if [value for value, _ in sorted(choices)] != list(range(len(labels))):
        raise ValueError(f"Choices must be numbered 0..n-1 to mirror as a list: {choices}")
    return labels


def _arb_key(prefix: str, label: str) -> str:
    return prefix + "".join(word.capitalize() for word in re.findall(r"[A-Za-z0-9]+", label))


def _missing_arb_messages(arb: dict[str, object], prefix: str, labels: list[str]) -> list[str]:
    return [f'  "{_arb_key(prefix, label)}": {json.dumps(label)}'
            for label in labels if arb.get(_arb_key(prefix, label)) != label]


def _dart_localized_list(prefix: str, labels: list[str]) -> str:
    return "\n".join(f"      l10n.{_arb_key(prefix, label)}," for label in labels)


def _grade_scale_arb_keys(enums: ModuleType) -> dict[int, str]:
    names = {value: name for name, value in vars(enums).items()
             if name.startswith("GRADE_SCALE_") and isinstance(value, int)}
    return {key: _arb_key("gradeScale", names[key].removeprefix("GRADE_SCALE_"))
            for key, template in enums.GRADE_SCALE_TEMPLATES.items() if re.search(r"[A-Za-z]", template["label"])}


def _missing_grade_scale_messages(arb: dict[str, object], enums: ModuleType) -> list[str]:
    keys = _grade_scale_arb_keys(enums)
    expected = [(arb_key, enums.GRADE_SCALE_TEMPLATES[key]["label"]) for key, arb_key in keys.items()]
    expected.append(("gradeScaleCustom", "Custom"))
    return [f'  "{arb_key}": {json.dumps(label)}' for arb_key, label in expected if arb.get(arb_key) != label]


def _render_grade_scales(enums: ModuleType) -> str:
    arb_keys = _grade_scale_arb_keys(enums)
    labels = "\n".join(f"      {key}: l10n.{arb_keys[key]}," if key in arb_keys
                       else f"      {key}: {_dart_string(template['label'])},"
                       for key, template in enums.GRADE_SCALE_TEMPLATES.items())
    scales = []
    for key, template in enums.GRADE_SCALE_TEMPLATES.items():
        bands = "".join(f"\n      GradeScaleBandModel(minGrade: {_dart_number(band['min_grade'])}, "
                        f"gradePoint: {_dart_number(band['grade_point'])}, label: {_dart_string(band['label'])}),"
                        for band in template["scale"])
        scales.append(f"    {key}: [{bands}\n    ]," if bands else f"    {key}: [],")
    return f"""{_DART_BANNER}
import 'package:heliumapp/config/locale_notifier.dart';
import 'package:heliumapp/data/models/planner/grade_scale_band_model.dart';

class GradeScaleTemplate {{
  GradeScaleTemplate._();

  static const int none = {enums.GRADE_SCALE_NONE};

  static const int custom = -1;

  static const Map<int, List<GradeScaleBandModel>> scales = {{
{chr(10).join(scales)}
  }};

  static Map<int, String> get labels {{
    final l10n = LocaleNotifier().localizations;
    return {{
{labels}
    }};
  }}

  static String labelFor(int template) =>
      template == custom ? LocaleNotifier().localizations.gradeScaleCustom : labels[template]!;
}}
"""


def _render_resources(enums: ModuleType) -> str:
    status = _labels(enums.RESOURCE_STATUS_CHOICES)
    condition = _labels(enums.CONDITION_CHOICES)
    return f"""{_DART_BANNER}
import 'package:heliumapp/config/locale_notifier.dart';
import 'package:heliumapp/data/models/drop_down_item.dart';
import 'package:heliumapp/utils/dropdown_extensions.dart';

class ResourceConstants {{
  static const int statusDigital = {status.index('Digital')};

  static const int conditionDigital = {condition.index('Digital')};

  static List<String> get statusLabels {{
    final l10n = LocaleNotifier().localizations;
    return [
{_dart_localized_list('resourceStatus', status)}
    ];
  }}

  static List<DropDownItem<String>> get statusItems => statusLabels.toDropDownItems();

  static List<String> get conditionLabels {{
    final l10n = LocaleNotifier().localizations;
    return [
{_dart_localized_list('resourceCondition', condition)}
    ];
  }}

  static List<DropDownItem<String>> get conditionItems => conditionLabels.toDropDownItems();
}}
"""


def _render_colors(enums: ModuleType) -> str:
    colors = "\n".join(f"  Color(0xff{color.lstrip('#').lower()})," for color in enums.PREFERRED_COLORS)
    return f"""{_DART_BANNER}
import 'package:flutter/material.dart';

const List<Color> preferredColors = [
{colors}
];
"""


def _render_connector(enums: ModuleType) -> str:
    def as_tuple(labels: Iterable[str]) -> str:
        return "(\n" + "".join(f'    "{label}",\n' for label in labels) + ")"

    presets = {key: template['label'] for key, template in enums.GRADE_SCALE_TEMPLATES.items()
               if key != enums.GRADE_SCALE_NONE}
    grade_scale_preset_names = "".join(f'    "{label}",\n' for label in presets.values())
    grade_scale_presets = "".join(f'    "{label}": {key},\n' for key, label in presets.items())

    return f"""{_PY_BANNER}
from typing import Final, Literal

RESOURCE_STATUSES: Final = {as_tuple(_labels(enums.RESOURCE_STATUS_CHOICES))}
RESOURCE_CONDITIONS: Final = {as_tuple(_labels(enums.CONDITION_CHOICES))}
UNGRADED: Final = "{enums.UNGRADED}"
NO_GRADE: Final = {enums.NO_GRADE}
RECURRENCE_HORIZON_YEARS: Final = {enums.RECURRENCE_HORIZON_YEARS}
GradeScalePreset = Literal[
{grade_scale_preset_names}]
GRADE_SCALE_PRESETS: Final[dict[GradeScalePreset, int]] = {{
{grade_scale_presets}}}
OAUTH_SCOPES: Final = {as_tuple(scope for scope, _ in enums.OAUTH_SCOPE_CHOICES)}
"""


def main() -> None:
    sys.path.insert(0, str(_REPO_ROOT))
    from helium.common import enums

    arb = json.loads(_FRONTEND_ARB.read_text(encoding="utf-8"))
    missing = (_missing_grade_scale_messages(arb, enums)
               + _missing_arb_messages(arb, "resourceStatus", _labels(enums.RESOURCE_STATUS_CHOICES))
               + _missing_arb_messages(arb, "resourceCondition", _labels(enums.CONDITION_CHOICES)))
    if missing:
        sys.exit(f"Add these messages, with a description, to {_FRONTEND_ARB.relative_to(_PROJECTS)}, "
                 "then run again:\n" + "\n".join(missing))

    for path, content in ((_FRONTEND_GRADE_SCALES, _render_grade_scales(enums)),
                          (_FRONTEND_RESOURCES, _render_resources(enums)),
                          (_FRONTEND_COLORS, _render_colors(enums)),
                          (_CONNECTOR_ENUMS, _render_connector(enums))):
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path.relative_to(_PROJECTS)}")


if __name__ == "__main__":
    main()
