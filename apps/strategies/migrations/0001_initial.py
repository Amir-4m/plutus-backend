# Generated by Django 3.2.6 on 2021-08-30 13:55

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('trader_bots', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('exchanges', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Strategy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_time', models.DateTimeField(auto_now_add=True, verbose_name='created time')),
                ('updated_time', models.DateTimeField(auto_now=True, verbose_name='updated time')),
                ('title', models.CharField(max_length=120, verbose_name='title')),
                ('price', models.FloatField(verbose_name='price')),
                ('offer_price', models.FloatField(blank=True, null=True, verbose_name='offer price')),
                ('is_enable', models.BooleanField(default=True, verbose_name='is enable?')),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='strategies', to='exchanges.asset')),
            ],
        ),
        migrations.CreateModel(
            name='UserStrategy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_time', models.DateTimeField(auto_now_add=True, verbose_name='created time')),
                ('updated_time', models.DateTimeField(auto_now=True, verbose_name='updated time')),
                ('due_date', models.DateField(verbose_name='due date')),
                ('is_enable', models.BooleanField(default=False)),
                ('trade', models.BooleanField(default=False, verbose_name='trade permission')),
                ('leverage', models.IntegerField(default=1, verbose_name='leverage')),
                ('contracts', models.FloatField(default=1, verbose_name='contract')),
                ('strategy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_strategies', to='strategies.strategy')),
                ('trader_bot', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='user_strategies', to='trader_bots.traderbot')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_strategies', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
