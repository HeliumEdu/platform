__copyright__ = "Copyright 2018, Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

from helium.planner.models import MaterialGroup


def given_material_group_exists(user, title='Test Material Group', shown_on_calendar=True):
    material_group = MaterialGroup.objects.create(title=title,
                                                  shown_on_calendar=shown_on_calendar,
                                                  user=user)

    return material_group


def verify_material_group_matches_data(test_case, material_group, data):
    test_case.assertEqual(material_group.title, data['title'])
    test_case.assertEqual(material_group.shown_on_calendar, data['shown_on_calendar'])
    test_case.assertEqual(material_group.get_user().pk, data['user'])
