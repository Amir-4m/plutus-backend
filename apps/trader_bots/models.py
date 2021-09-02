from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _

from apps.exchanges.models import Exchange


class TraderBot(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bots')
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE, related_name='trader_bots')
    credential_data = models.JSONField(_("credential data"), default=dict)

    class Meta:
        unique_together = ('user', 'exchange')

    def __str__(self):
        return f'{self.id}-{self.user.email}-{self.exchange.title}'
