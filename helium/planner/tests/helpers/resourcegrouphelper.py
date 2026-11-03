from helium.planner.models import ResourceGroup


def given_resource_group_exists(user, title='📚 Test Material Group', shown_on_calendar=True):
    resource_group = ResourceGroup.objects.create(title=title,
                                                  shown_on_calendar=shown_on_calendar,
                                                  user=user)

    return resource_group


def verify_resource_group_matches_data(test_case, resource_group, data):
    test_case.assertEqual(resource_group.title, data['title'])
    test_case.assertEqual(resource_group.shown_on_calendar, data['shown_on_calendar'])
    test_case.assertEqual(resource_group.get_user().pk, data['user'])
