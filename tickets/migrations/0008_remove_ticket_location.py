from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0007_migrate_locations_and_subtypes'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ticket',
            name='location',
        ),
    ]
