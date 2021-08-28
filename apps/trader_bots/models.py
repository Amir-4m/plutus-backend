from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _


class TraderBot(models.Model):
    EXCHANGE_KUCOIN = 'kucoin'
    EXCHANGE_AAX = 'aax'

    EXCHANGE_LIST = (
        (EXCHANGE_KUCOIN, "Kucoin"),
        (EXCHANGE_AAX, "Axx"),

    )
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bots')
    exchange = models.CharField(_("exchange"), max_length=120, choices=EXCHANGE_LIST, default=EXCHANGE_KUCOIN)
    credential_data = models.JSONField(_("credential data"), default=dict)
