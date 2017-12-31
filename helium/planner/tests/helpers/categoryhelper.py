from helium.planner.models import Category

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


def given_category_exists(course, title='Test Category', weight=15, color='#4986e7'):
    category = Category.objects.create(title=title,
                                       weight=weight,
                                       color=color,
                                       course=course)

    return category


def verify_category_matches_data(test_case, category, data):
    test_case.assertEqual(category.title, data['title'])
    test_case.assertEqual(category.weight, float(data['weight']))
    test_case.assertEqual(category.color, data['color'])
    test_case.assertEqual(category.average_grade, float(data['average_grade']))
    test_case.assertEqual(category.grade_by_weight, float(data['grade_by_weight']))
    test_case.assertEqual(category.trend, data['trend'])
    if 'course' in data:
        test_case.assertEqual(category.course.pk, int(data['course']))
