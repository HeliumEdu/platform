from helium.common import enums
from helium.planner.models import Resource


def given_resource_exists(resource_group, title='📘 Test Material', status=enums.SHIPPED, condition=enums.BROKEN,
                          website='http://www.material.com', price='9.99',
                          courses=None):
    if courses is None:
        courses = []

    resource = Resource.objects.create(title=title,
                                       status=status,
                                       condition=condition,
                                       website=website,
                                       price=price,
                                       resource_group=resource_group)
    for course in courses:
        resource.courses.add(course)

    return resource


def verify_resource_matches_data(test_case, resource, data):
    if data['courses'] is None:
        data['courses'] = []

    test_case.assertEqual(resource.title, data['title'])
    test_case.assertEqual(resource.status, data['status'])
    test_case.assertEqual(resource.condition, data['condition'])
    test_case.assertEqual(resource.website, data['website'])
    test_case.assertEqual(resource.price, data['price'])
    test_case.assertEqual(resource.resource_group.pk, int(data.get('resource_group', data.get('resource_group'))))
    for course_id in data['courses']:
        test_case.assertTrue(resource.courses.filter(pk=course_id).exists())
