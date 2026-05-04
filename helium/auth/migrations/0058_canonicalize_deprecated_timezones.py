from django.db import migrations

# IANA renamed or merged these zones into the canonical replacements below.
# We're rewriting any stored values so that subsequent migration 0059 can
# narrow ``UserSettings.time_zone`` choices to canonical zones only.

CANONICALIZATION = {
    'America/Godthab': 'America/Nuuk',
    'America/Montreal': 'America/Toronto',
    'America/Nipigon': 'America/Toronto',
    'America/Pangnirtung': 'America/Iqaluit',
    'America/Rainy_River': 'America/Winnipeg',
    'America/Santa_Isabel': 'America/Tijuana',
    'America/Thunder_Bay': 'America/Toronto',
    'America/Yellowknife': 'America/Edmonton',
    'Asia/Choibalsan': 'Asia/Ulaanbaatar',
    'Asia/Chongqing': 'Asia/Shanghai',
    'Asia/Harbin': 'Asia/Shanghai',
    'Asia/Kashgar': 'Asia/Urumqi',
    'Asia/Rangoon': 'Asia/Yangon',
    'Australia/Currie': 'Australia/Hobart',
    'Etc/UTC': 'UTC',
    'Europe/Kiev': 'Europe/Kyiv',
    'Europe/Uzhgorod': 'Europe/Kyiv',
    'Europe/Zaporozhye': 'Europe/Kyiv',
    'Pacific/Enderbury': 'Pacific/Kanton',
    'Pacific/Johnston': 'Pacific/Honolulu',
}


def canonicalize_deprecated_timezones(apps, schema_editor):
    UserSettings = apps.get_model('helium_auth', 'UserSettings')

    for old, new in CANONICALIZATION.items():
        updated = UserSettings.objects.filter(time_zone=old).update(time_zone=new)
        if updated:
            print(f'  canonicalized {updated} row(s): {old} -> {new}')


class Migration(migrations.Migration):
    dependencies = [
        ('helium_auth', '0057_alter_usersettings_time_zone'),
    ]

    operations = [
        migrations.RunPython(
            canonicalize_deprecated_timezones,
            migrations.RunPython.noop,
        ),
    ]
