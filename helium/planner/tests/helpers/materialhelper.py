__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.7"

from helium.common import enums
from helium.planner.models import Material


def given_material_exists(material_group, title='📘 Test Material', status=enums.SHIPPED, condition=enums.BROKEN,
                          website='http://www.material.com', price='9.99', details='Return by 7/1',
                          courses=None):
    if courses is None:
        courses = []

    material = Material.objects.create(title=title,
                                       status=status,
                                       condition=condition,
                                       website=website,
                                       price=price,
                                       details=details,
                                       material_group=material_group)
    for course in courses:
        material.courses.add(course)

    return material


def verify_material_matches_data(test_case, material, data):
    if data['courses'] is None:
        data['courses'] = []

    test_case.assertEqual(material.title, data['title'])
    test_case.assertEqual(material.status, data['status'])
    test_case.assertEqual(material.condition, data['condition'])
    test_case.assertEqual(material.website, data['website'])
    test_case.assertEqual(material.price, data['price'])
    test_case.assertEqual(material.details, data['details'])
    test_case.assertEqual(material.material_group.pk, int(data['material_group']))
    for course_id in data['courses']:
        test_case.assertTrue(material.courses.filter(pk=course_id).exists())
