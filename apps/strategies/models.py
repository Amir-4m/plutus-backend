from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _

from apps.exchanges.models import Asset
from apps.trader_bots.models import TraderBot


class Strategy(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    title = models.CharField(_("title"), max_length=120)
    price = models.FloatField(_('price'))
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name='strategies')
    offer_price = models.FloatField(_('offer price'), null=True, blank=True)
    is_enable = models.BooleanField(_('is enable?'), default=True)

    def __str__(self):
        return f'{self.id}-{self.title}'


class UserStrategy(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_strategies')
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name='user_strategies')
    due_date = models.DateField(_('due date'))
    is_enable = models.BooleanField(default=False)
    trade = models.BooleanField(_('trade permission'), default=False)
    trader_bot = models.ForeignKey(TraderBot, on_delete=models.PROTECT, related_name='user_strategies', null=True, blank=True)
    leverage = models.IntegerField(_('leverage'), default=1)
    contracts = models.FloatField(_('contract'), default=1)

    def __str__(self):
        return f'{self.id}-{self.user.email}-{self.strategy.title}'
