import json
from collections import Counter

from django.urls import reverse
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Category, Course, CourseGroup
from helium.planner.services import gradingservice
from helium.planner.tests.helpers import categoryhelper, coursegrouphelper, coursehelper, homeworkhelper

_seq = [0]
CALLS = Counter()
_ORIG = {}


def _instrument():
    for name in ('recalculate_category_grade', 'recalculate_course_grade',
                 'recalculate_course_group_grade'):
        if name in _ORIG:
            continue
        _ORIG[name] = getattr(gradingservice, name)

        def make(n):
            def spy(*a, **kw):
                CALLS[n[:22]] += 1
                return _ORIG[n](*a, **kw)
            return spy
        setattr(gradingservice, name, make(name))


class TestCaseTmpGradeAudit(APITestCase):
    def setUp(self):
        _instrument()

    def _fixture(self, hw=3):
        _seq[0] += 1
        user = userhelper.given_a_user_exists_and_is_authenticated(
            self.client, username=f'u{_seq[0]}', email=f'u{_seq[0]}@e.com')
        cg = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(cg)
        cat = categoryhelper.given_category_exists(course, title='k0', weight=100)
        for _ in range(hw):
            homeworkhelper.given_homework_exists(course, category=cat,
                                                 current_grade='90/100', completed=True)
        return user, cg, course, cat

    def _run(self, label, action, setup=None):
        user, cg, course, cat = self._fixture()
        extra = setup(course, cg) if setup else None
        CALLS.clear()
        status = action(user, cg, course, cat) if extra is None else action(user, cg, course, cat, extra)
        counts = dict(CALLS)
        after = {
            'cat': Category.objects.filter(pk=cat.pk).values_list('average_grade', flat=True).first(),
            'course': Course.objects.filter(pk=course.pk).values_list('current_grade', flat=True).first(),
            'group': CourseGroup.objects.filter(pk=cg.pk).values_list('overall_grade', flat=True).first(),
        }
        # recompute from scratch over whatever survives
        for c in Category.objects.for_user(user.pk):
            _ORIG['recalculate_category_grade'](c.pk)
        for c in Course.objects.for_user(user.pk):
            _ORIG['recalculate_course_grade'](c.pk)
        for g in CourseGroup.objects.for_user(user.pk):
            _ORIG['recalculate_course_group_grade'](g.pk)
        truth = {
            'cat': Category.objects.filter(pk=cat.pk).values_list('average_grade', flat=True).first(),
            'course': Course.objects.filter(pk=course.pk).values_list('current_grade', flat=True).first(),
            'group': CourseGroup.objects.filter(pk=cg.pk).values_list('overall_grade', flat=True).first(),
        }
        stale = [k for k in after if after[k] != truth[k]]
        verdict = 'OK' if not stale else f'*** STALE {[(k, after[k], truth[k]) for k in stale]} ***'
        code = getattr(status, 'status_code', '-')
        print(f'  {label:<26} http={code} recalcs={sum(counts.values()):<4} {verdict}')

    def test_all_entry_points(self):
        print('\n--- final-state correctness + recalculation count, per entry point ---')

        def hw_url(cg, course, pk=None):
            k = {'course_group': cg.pk, 'course': course.pk}
            return (reverse('planner_coursegroups_courses_homework_detail', kwargs={**k, 'pk': pk})
                    if pk else reverse('planner_coursegroups_courses_homework_list', kwargs=k))

        self._run('POST homework', lambda u, cg, c, k: self.client.post(
            hw_url(cg, c), json.dumps({'title': 'n', 'all_day': False, 'show_end_time': True,
                                       'start': '2026-05-08T16:00:00Z', 'end': '2026-05-08T18:00:00Z',
                                       'priority': 65, 'current_grade': '50/100', 'completed': True,
                                       'category': k.pk, 'course': c.pk}),
            content_type='application/json'))

        self._run('PATCH homework grade', lambda u, cg, c, k: self.client.patch(
            hw_url(cg, c, c.homework.first().pk), json.dumps({'current_grade': '10/100'}),
            content_type='application/json'))

        self._run('DELETE homework', lambda u, cg, c, k: self.client.delete(
            hw_url(cg, c, c.homework.first().pk)))

        self._run('PATCH homework category',
                  lambda u, cg, c, k, other: self.client.patch(
                      hw_url(cg, c, c.homework.first().pk),
                      json.dumps({'category': other.pk}), content_type='application/json'),
                  setup=lambda c, cg: categoryhelper.given_category_exists(c, title='k1', weight=50))

        self._run('PUT category weight', lambda u, cg, c, k: self.client.put(
            reverse('planner_coursegroups_courses_categories_detail',
                    kwargs={'course_group': cg.pk, 'course': c.pk, 'pk': k.pk}),
            json.dumps({'title': k.title, 'weight': 50, 'course': c.pk}),
            content_type='application/json'))

        self._run('DELETE category',
                  lambda u, cg, c, k, _: self.client.delete(
                      reverse('planner_coursegroups_courses_categories_detail',
                              kwargs={'course_group': cg.pk, 'course': c.pk, 'pk': k.pk})),
                  setup=lambda c, cg: categoryhelper.given_category_exists(c, title='survivor', weight=50))

        self._run('DELETE course',
                  lambda u, cg, c, k, _: self.client.delete(
                      reverse('planner_coursegroups_courses_detail',
                              kwargs={'course_group': cg.pk, 'pk': c.pk})),
                  setup=lambda c, cg: coursehelper.given_course_exists(cg, title='survivor'))

        self._run('DELETE course group', lambda u, cg, c, k: self.client.delete(
            reverse('planner_coursegroups_detail', kwargs={'pk': cg.pk})))
