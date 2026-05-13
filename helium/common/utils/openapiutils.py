__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

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
