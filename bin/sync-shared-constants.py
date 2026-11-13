#!/usr/bin/env python3

"""
Write the platform constants that the frontend and connector mirror, so they can't drift.

Reads ``helium/common/enums.py`` and writes:

* ``projects/frontend/lib/utils/grade_scale_constants.dart`` — the grade scale templates (``GRADE_SCALE_TEMPLATES``).
* ``projects/frontend/lib/utils/resource_constants.dart`` — resource status and condition labels
  (``RESOURCE_STATUS_CHOICES``, ``CONDITION_CHOICES``).
* ``projects/frontend/lib/utils/preferred_colors.dart`` — the course color palette (``PREFERRED_COLORS``).
* ``projects/connector/helium_connector/platform_enums.py`` — resource status and condition labels, the ungraded
  sentinels, and the recurrence horizon.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PROJECTS = _REPO_ROOT.parent
_FRONTEND_UTILS = _PROJECTS / "frontend" / "lib" / "utils"
_FRONTEND_GRADE_SCALES = _FRONTEND_UTILS / "grade_scale_constants.dart"
_FRONTEND_RESOURCES = _FRONTEND_UTILS / "resource_constants.dart"
_FRONTEND_COLORS = _FRONTEND_UTILS / "preferred_colors.dart"
_CONNECTOR_ENUMS = _PROJECTS / "connector" / "helium_connector" / "platform_enums.py"

_DART_BANNER = ("// AUTO-GENERATED — DO NOT EDIT.\n"
                "// Written from platform/helium/common/enums.py by:\n"
                "//   platform/bin/sync-shared-constants.py\n")
_PY_BANNER = ("# AUTO-GENERATED — DO NOT EDIT.\n"
              "# Written from platform/helium/common/enums.py by:\n"
              "#   platform/bin/sync-shared-constants.py\n")


def _dart_string(value):
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'").replace("$", "\\$") + "'"


def _dart_number(value):
    return repr(float(value))


def _labels(choices):
    labels = [label for _, label in sorted(choices)]
    if [value for value, _ in sorted(choices)] != list(range(len(labels))):
        raise ValueError(f"Choices must be numbered 0..n-1 to mirror as a list: {choices}")
    return labels


def _render_grade_scales(enums):
    labels = "\n".join(f"    {key}: {_dart_string(template['label'])},"
                       for key, template in enums.GRADE_SCALE_TEMPLATES.items())
    scales = []
    for key, template in enums.GRADE_SCALE_TEMPLATES.items():
        bands = "".join(f"\n      GradeScaleBandModel(minGrade: {_dart_number(band['min_grade'])}, "
                        f"gradePoint: {_dart_number(band['grade_point'])}, label: {_dart_string(band['label'])}),"
                        for band in template["scale"])
        scales.append(f"    {key}: [{bands}\n    ]," if bands else f"    {key}: [],")
    return f"""{_DART_BANNER}
import 'package:heliumapp/data/models/drop_down_item.dart';
import 'package:heliumapp/data/models/planner/grade_scale_band_model.dart';

class GradeScaleTemplate {{
  GradeScaleTemplate._();

  static const int none = {enums.GRADE_SCALE_NONE};

  static const int custom = -1;

  static const Map<int, String> labels = {{
{labels}
  }};

  static const Map<int, List<GradeScaleBandModel>> scales = {{
{chr(10).join(scales)}
  }};

  static String summaryLabel(int template) =>
      template == custom ? 'Custom' : labels[template]!;

  static List<DropDownItem<int>> get items => [
    for (final entry in labels.entries)
      DropDownItem(id: entry.key, value: entry.key, label: entry.value),
  ];

  static DropDownItem<int> get customItem =>
      DropDownItem(id: custom, value: custom, label: 'Custom');
}}
"""


def _render_resources(enums):
    status = "\n".join(f"    {_dart_string(label)}," for label in _labels(enums.RESOURCE_STATUS_CHOICES))
    condition = "\n".join(f"    {_dart_string(label)}," for label in _labels(enums.CONDITION_CHOICES))
    return f"""{_DART_BANNER}
import 'package:heliumapp/data/models/drop_down_item.dart';
import 'package:heliumapp/utils/dropdown_extensions.dart';

class ResourceConstants {{
  static final List<String> status = [
{status}
  ];
  static final List<DropDownItem<String>> statusItems = status
      .toDropDownItems();

  static final List<String> condition = [
{condition}
  ];
  static final List<DropDownItem<String>> conditionItems = condition
      .toDropDownItems();
}}
"""


def _render_colors(enums):
    colors = "\n".join(f"  Color(0xff{color.lstrip('#').lower()})," for color in enums.PREFERRED_COLORS)
    return f"""{_DART_BANNER}
import 'package:flutter/material.dart';

const List<Color> preferredColors = [
{colors}
];
"""


def _render_connector(enums):
    def as_tuple(labels):
        return "(\n" + "".join(f'    "{label}",\n' for label in labels) + ")"

    return f"""{_PY_BANNER}
from typing import Final

RESOURCE_STATUSES: Final = {as_tuple(_labels(enums.RESOURCE_STATUS_CHOICES))}
RESOURCE_CONDITIONS: Final = {as_tuple(_labels(enums.CONDITION_CHOICES))}
UNGRADED: Final = "{enums.UNGRADED}"
NO_GRADE: Final = {enums.NO_GRADE}
RECURRENCE_HORIZON_YEARS: Final = {enums.RECURRENCE_HORIZON_YEARS}
"""


def main():
    sys.path.insert(0, str(_REPO_ROOT))
    from helium.common import enums

    for path, content in ((_FRONTEND_GRADE_SCALES, _render_grade_scales(enums)),
                          (_FRONTEND_RESOURCES, _render_resources(enums)),
                          (_FRONTEND_COLORS, _render_colors(enums)),
                          (_CONNECTOR_ENUMS, _render_connector(enums))):
        path.write_text(content)
        print(f"Wrote {path.relative_to(_PROJECTS)}")


if __name__ == "__main__":
    main()
