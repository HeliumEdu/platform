from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0078_userclientactivity_connector'),
    ]

    operations = [
        migrations.RenameField(model_name='usersettings', old_name='material_color', new_name='resource_color'),
    ]
