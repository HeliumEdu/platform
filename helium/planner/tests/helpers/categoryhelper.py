__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

from helium.planner.models import Category


def given_category_exists(course, title='📊 Test Category 1', weight=0, color='#4986e7'):
    category = Category.objects.create(title=title,
                                       weight=weight,
                                       color=color,
                                       course=course)

    return category


def verify_category_matches_data(test_case, category, data):
    test_case.assertEqual(category.title, data['title'])
    test_case.assertEqual(category.weight, float(data['weight']))
    test_case.assertEqual(category.color, data['color'])
    test_case.assertEqual(float(category.average_grade), float(data['average_grade']))
    test_case.assertEqual(category.grade_by_weight, float(data['grade_by_weight']))
    test_case.assertEqual(category.trend, data['trend'])
    if 'course' in data:
        test_case.assertEqual(category.course.pk, int(data['course']))
