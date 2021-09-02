from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _

from apps.exchanges.models import ExchangeFuturesAsset


class FuturesOrder(models.Model):
    SIDE_SHORT = 'sell'
    SIDE_LONG = 'buy'

    SIDE_LIST = (
        (SIDE_SHORT, "Short"),
        (SIDE_LONG, "Long"),

    )
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='futures_orders')
    exchange_futures_asset = models.ForeignKey(ExchangeFuturesAsset, on_delete=models.PROTECT, related_name='futures_orders')
    open_price = models.FloatField(_('open price'))
    close_price = models.FloatField(_('close price'), null=True, blank=True)
    leverage = models.IntegerField(_('leverage'), default=1)
    order_id = models.UUIDField(_('order id'), unique=True)
    side = models.CharField(_('position side'), choices=SIDE_LIST, null=True, max_length=10)
    is_active = models.BooleanField(_('is active'), default=True)
    logs = models.TextField(_('logs'), null=True, blank=True)

    def __str__(self):
        return f'{self.user.email}-{self.exchange_futures_asset.asset.symbol}'
