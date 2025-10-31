# Generated manually for adding when_added and when_updated fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='when_added',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        # Note: null=True is temporary for existing rows. Will be populated automatically for new rows.
        migrations.AddField(
            model_name='post',
            name='when_updated',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

