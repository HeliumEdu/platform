"""
Helper for MaterialGroup models in testing.
"""

from helium.planner.models import MaterialGroup

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


def given_material_group_exists(user, title='Test Material Group', shown_on_calendar=True):
    material_group = MaterialGroup.objects.create(title=title,
                                                  shown_on_calendar=shown_on_calendar,
                                                  user=user)

    return material_group


def verify_material_group_matches_data(test_case, material_group, data):
    test_case.assertEqual(material_group.title, data['title'])
    test_case.assertEqual(material_group.shown_on_calendar, data['shown_on_calendar'])
    test_case.assertEqual(material_group.get_user().pk, data['user'])
