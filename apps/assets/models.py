from django.db import models
from django.utils.translation import ugettext_lazy as _


class Asset(models.Model):
    EXCHANGE_KUCOIN = 'kucoin'
    EXCHANGE_AAX = 'aax'

    EXCHANGE_LIST = (
        (EXCHANGE_KUCOIN, "Kucoin"),
        (EXCHANGE_AAX, "Aax")
    )
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    symbol = models.CharField(_('symbol'), max_length=50)
    pair = models.CharField(_('pair'), max_length=50)
    price = models.FloatField(_('price'), null=True, blank=True)
    code_name = models.CharField(_('code name'), max_length=120)
    exchange = models.CharField(_('exchange'), max_length=120, choices=EXCHANGE_LIST, default=EXCHANGE_AAX)
    ascending_trend = models.BooleanField(_('is in an ascending trend?'), default=True)

    class Meta:
        unique_together = ('code_name', 'exchange')
