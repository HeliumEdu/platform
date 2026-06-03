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
        'tags': ['auth', 'auth.register', 'auth.token.api', 'auth.token.jwt'],
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


def add_enum_descriptions(result, generator, request, public):
    """
    Inject ``x-enumDescriptions`` into every schema location that Redoc renders for each enum
    declared in ``ENUM_NAME_OVERRIDES``:

    1. The named component itself (``components/schemas/FooEnum``) — picked up when a user
       browses a component schema directly.
    2. Any property schema that references the component via ``allOf``/``oneOf``/``anyOf`` —
       required because Redoc does not propagate ``x-enumDescriptions`` from a ``$ref`` target
       into the inline field view inside an operation.
    """
    from drf_spectacular.settings import spectacular_settings

    name_to_desc = {
        name: {str(v): label for v, label in choices}
        for name, choices in spectacular_settings.ENUM_NAME_OVERRIDES.items()
    }

    schemas = result.get('components', {}).get('schemas', {})
    for name, desc in name_to_desc.items():
        if name in schemas:
            schemas[name]['x-enumDescriptions'] = desc

    def _inject_refs(node):
        if isinstance(node, dict):
            if 'x-enumDescriptions' not in node:
                for combinator in ('allOf', 'oneOf', 'anyOf'):
                    for sub in node.get(combinator) or []:
                        if not isinstance(sub, dict):
                            continue
                        ref = sub.get('$ref', '')
                        component_name = ref.rsplit('/', 1)[-1] if ref else ''
                        if component_name in name_to_desc:
                            node['x-enumDescriptions'] = name_to_desc[component_name]
                            break
                    if 'x-enumDescriptions' in node:
                        break
            for v in node.values():
                _inject_refs(v)
        elif isinstance(node, list):
            for item in node:
                _inject_refs(item)

    _inject_refs(result)
    return result


def add_tag_groups(result, generator, request, public):
    result['x-tagGroups'] = TAG_GROUPS
    return result


def order_security(result, generator, request, public):
    rank = {'apiToken': 0, 'jwtAuth': 1}
    for path in result.get('paths', {}).values():
        if not isinstance(path, dict):
            continue
        for op in path.values():
            if isinstance(op, dict) and 'security' in op:
                op['security'].sort(key=lambda s: rank.get(next(iter(s), ''), 99))
    return result
