__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"


def strip_enum_int_bounds(result, generator, request, public):
    """
    Drop redundant ``minimum`` / ``maximum`` keys from any property schema that already
    references an enum component. Django's ``PositiveIntegerField`` carries int64 bounds
    that drf-spectacular emits alongside the enum ``$ref``, producing nonsense ranges like
    ``0 .. 9223372036854775807`` next to an enum with only a handful of valid values.
    """

    def _has_enum_ref(schema):
        if not isinstance(schema, dict):
            return False
        if 'enum' in schema:
            return True
        for combinator in ('allOf', 'oneOf', 'anyOf'):
            for sub in schema.get(combinator) or []:
                ref = sub.get('$ref') if isinstance(sub, dict) else None
                if ref and ref.endswith('Enum'):
                    return True
        return False

    def _walk(node):
        if isinstance(node, dict):
            if _has_enum_ref(node):
                node.pop('minimum', None)
                node.pop('maximum', None)
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(result.get('components', {}).get('schemas', {}))
    return result


TAG_GROUPS = [
    {
        'name': 'Authentication',
        'tags': ['auth', 'auth.register', 'auth.token'],
    },
    {
        'name': 'Planner',
        'tags': [
            'planner.coursegroup',
            'planner.course',
            'planner.courseschedule',
            'planner.category',
            'planner.homework',
            'planner.event',
            'planner.reminder',
            'planner.materialgroup',
            'planner.material',
            'planner.attachment',
            'planner.note',
            'planner.grades',
        ],
    },
    {
        'name': 'Feeds',
        'tags': ['feed.externalcalendar', 'feed.private'],
    },
    {
        'name': 'Import / Export',
        'tags': ['importexport'],
    },
    {
        'name': 'Meta',
        'tags': ['info'],
    },
]


def add_tag_groups(result, generator, request, public):
    result['x-tagGroups'] = TAG_GROUPS
    return result
