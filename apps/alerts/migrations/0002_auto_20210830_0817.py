# Generated by Django 3.2.6 on 2021-08-30 08:17

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='platform',
            old_name='platform',
            new_name='platform_type',
        ),
        migrations.AddField(
            model_name='strategyalert',
            name='alert_key',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='alert key'),
        ),
        migrations.AddField(
            model_name='strategyalert',
            name='trade',
            field=models.BooleanField(default=False, verbose_name='trade permission'),
        ),
        migrations.AlterField(
            model_name='strategyalert',
            name='is_enable',
            field=models.BooleanField(default=False, verbose_name='is enable'),
        ),
    ]
