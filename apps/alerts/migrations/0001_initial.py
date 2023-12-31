# Generated by Django 3.2.6 on 2021-08-30 13:55

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('strategies', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Platform',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_time', models.DateTimeField(auto_now_add=True, verbose_name='created time')),
                ('updated_time', models.DateTimeField(auto_now=True, verbose_name='updated time')),
                ('platform_type', models.CharField(choices=[(1, 'Telegram'), (0, 'Email')], default=0, max_length=50, verbose_name='platform')),
                ('is_enable', models.BooleanField(default=True, verbose_name='is enable')),
                ('extra_data', models.JSONField(default=dict, verbose_name='extra data')),
            ],
        ),
        migrations.CreateModel(
            name='StrategyAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_time', models.DateTimeField(auto_now_add=True, verbose_name='created time')),
                ('updated_time', models.DateTimeField(auto_now=True, verbose_name='updated time')),
                ('alert_key', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='alert key')),
                ('is_enable', models.BooleanField(default=False, verbose_name='is enable')),
                ('extra_data', models.JSONField(default=dict, verbose_name='extra data')),
                ('platform', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='alerts', to='alerts.platform')),
                ('user_strategy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='strategies.userstrategy')),
            ],
        ),
        migrations.CreateModel(
            name='AlertLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_time', models.DateTimeField(auto_now_add=True, verbose_name='created time')),
                ('log', models.TextField(blank=True, null=True, verbose_name='log')),
                ('strategy_alert', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='alerts.strategyalert')),
            ],
        ),
    ]
