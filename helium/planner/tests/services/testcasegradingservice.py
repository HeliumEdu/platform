from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.services import gradingservice
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, homeworkhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


class TestCaseGradingService(TestCase):
    pass

    # TODO: course group current grade

    # TODO: course group trending positive/negative

    # TODO: course current grade

    # TODO: course non weight examples
    # (25 + 75) / 2

    # (25 + 75 + 25 + 75) / 4

    # (25 + 75 + 25 + 75 + 100) / 5

    # (25 + 75 + 25 + 75 + 100 + 25 + 25) / 7

    # (80 + 90 + 25 + 75 + 100 + 25 + 25) / 7

    # (80 + 90 + 80 + 90 + 100 + 25 + 25) / 7

    # (80 + 90 + 100 + 25 + 25) / 5

    # TODO: course weighted examples
    # (((.5 * .3) + (0 * .6) + (0 * .1)) / .3) * 100

    # (((.5 * .3) + (.35 * .6) + (0 * .1)) / .9) * 100

    # ((.5 * .3) + (.35 * .6) + (.9 * .1)) * 100

    # ((.5625 * .3) + (.6 * .6) + (.675 * .1)) * 100

    # ((.5625 * .3) + (.825 * .6) + (.85 * .1)) * 100

    # ((.75 * .3) + (.825 * .6) + (.85 * .1)) * 100

    # TODO: course differing grade bases
    # Grade of 10/10 (100%)

    # Grade of 50/100 (50%)

    # Grade of 40/50 (100%)

    # Grade of 60/100 (50%)

    # Grade of 200/200 (100%)

    # This course has a total of 110 points (60.303030303030305)

    # TODO: course non weight grade points examples
    # ((25 * 30)) / 30

    # ((25 * 30) + (75 * 50)) / 80

    # ((25 * 30) + (75 * 50) + (50 * 20)) / 100

    # TODO: course weighted grade points examples
    # (25) / 1

    # (25 + 75) / 2

    # (25 + 75 + 50) / 3

    # TODO: course trending positive/negative

    # TODO: category current grade

    # TODO: category differing grade bases
    # Grade of 10/10 (100%)

    # Grade of 50/100 (50%)

    # Grade of 40/50 (100%)

    # Grade of 60/100 (50%)

    # Grade of 200/200 (100%)

    # This category has a total of 110 points (54.54545454545454)

    # This category has a total of 150 points (66.66666666666666)

    # TODO: category trending positive/negative
