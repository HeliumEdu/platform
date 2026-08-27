from unittest import mock

from celery import current_task
from django.test import TestCase

from conf.celery import app
from helium.common.utils import metricutils, taskutils


@app.task(bind=True)
def _failing_task(self):
    metricutils.task_start('probe.failing', priority='high')

    raise ValueError('boom')


@app.task(bind=True)
def _unstarted_task(self):
    raise ValueError('boom')


class TestCaseMetricsTask(TestCase):
    def test_every_task_inherits_the_metrics_base(self):
        # THEN
        self.assertTrue(issubclass(app.Task, taskutils.MetricsTask))

    @mock.patch('helium.common.utils.metricutils.increment')
    def test_failure_reports_under_the_name_the_body_started_with(self, mock_increment):
        # WHEN
        _failing_task.apply(throw=False)

        # THEN
        failed = [c for c in mock_increment.call_args_list if c.args and c.args[0] == 'task.failed']
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0].kwargs['extra_tags'],
                         ['name:probe.failing', 'priority:high', 'exception:ValueError'])

    @mock.patch('helium.common.utils.metricutils.increment')
    def test_failure_without_task_start_reports_nothing(self, mock_increment):
        # WHEN
        _unstarted_task.apply(throw=False)

        # THEN
        failed = [c for c in mock_increment.call_args_list if c.args and c.args[0] == 'task.failed']
        self.assertEqual(failed, [])


class TestCaseStashMetrics(TestCase):
    def test_task_start_stashes_its_metrics_on_the_request(self):
        # GIVEN
        seen = {}

        @app.task(bind=True)
        def _t(self):
            metrics = metricutils.task_start('probe.stash', priority='low')
            seen['stashed'] = getattr(self.request, 'helium_metrics', None)
            seen['returned'] = metrics

        # WHEN
        _t.apply()

        # THEN
        self.assertIsNotNone(seen['stashed'])
        self.assertEqual(seen['stashed'], seen['returned'])
        self.assertEqual(seen['stashed']['Task-Metric-ID'], 'probe.stash')

    def test_task_start_outside_a_task_does_not_raise(self):
        # GIVEN
        self.assertFalse(bool(current_task))

        # WHEN
        metrics = metricutils.task_start('probe.no-task', priority='low')

        # THEN
        self.assertEqual(metrics['Task-Metric-ID'], 'probe.no-task')


class TestCaseEveryTaskIsInstrumented(TestCase):
    def test_every_task_starts_its_metrics(self):
        # GIVEN
        import ast
        import glob

        # WHEN
        uninstrumented = []
        for path in sorted(glob.glob('helium/*/tasks.py')):
            tree = ast.parse(open(path).read())
            for node in tree.body:
                if not isinstance(node, ast.FunctionDef):
                    continue
                if not any('app' in ast.dump(d) and 'task' in ast.dump(d) for d in node.decorator_list):
                    continue
                calls = {n.func.attr for n in ast.walk(node)
                         if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
                if 'task_start' not in calls:
                    uninstrumented.append(f'{path}:{node.name}')

        # THEN
        self.assertEqual(uninstrumented, [])
