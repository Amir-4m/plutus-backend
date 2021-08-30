from django.db import models
from django.utils.translation import ugettext_lazy as _


def upload_exchange_logo(instance, file_name):
    if file_name:
        return f'assets/exchanges/logos/{instance.title.replace(" ", "_").lower()}.{file_name.split(".")[-1]}'


class Asset(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    symbol = models.CharField(_('symbol'), max_length=50, unique=True)
    ascending_trend = models.BooleanField(_('is in an ascending trend?'), default=True)


class Exchange(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    title = models.CharField(_('title'), max_length=120, unique=True)
    logo = models.ImageField(_('logo'), null=True, blank=True, upload_to=upload_exchange_logo)
    futures_assets = models.ManyToManyField(Asset, related_name='exchanges', through='ExchangeFuturesAsset')
    is_enable = models.BooleanField(_('is enable'), default=True)


class ExchangeFuturesAsset(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE, related_name='exchange_futures_assets')
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='exchange_futures_assets')
    code_name = models.CharField(_('code name'), max_length=50)

    class Meta:
        unique_together = ('exchange', 'asset', 'code_name')
