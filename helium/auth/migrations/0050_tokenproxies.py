__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0049_userclientactivity'),
        ('token_blacklist', '0013_alter_blacklistedtoken_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='OutstandingTokenProxy',
            fields=[],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('token_blacklist.outstandingtoken',),
        ),
        migrations.CreateModel(
            name='BlacklistedTokenProxy',
            fields=[],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('token_blacklist.blacklistedtoken',),
        ),
    ]
