import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _


class Platform(models.Model):
    PLATFORM_EMAIL = 0
    PLATFORM_TELEGRAM = 1
    PLATFORM_LIST = (
        (PLATFORM_TELEGRAM, _('Telegram')),
        (PLATFORM_EMAIL, _('Email'))
    )

    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    platform_type = models.IntegerField(_('platform'), choices=PLATFORM_LIST, default=PLATFORM_EMAIL)
    is_enable = models.BooleanField(_('is enable'), default=True)
    extra_data = models.JSONField(_('extra data'), default=dict)

    def __repr__(self):
        return f'{self.platform_type}'


class StrategyAlert(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    user_strategy = models.ForeignKey('strategies.UserStrategy', on_delete=models.CASCADE, related_name='alerts')
    platform = models.ForeignKey(Platform, on_delete=models.PROTECT, related_name='alerts')
    alert_key = models.UUIDField(_('alert key'), default=uuid.uuid4, unique=True, editable=False)
    is_enable = models.BooleanField(_('is enable'), default=False)
    extra_data = models.JSONField(_('extra data'), default=dict)

    def __repr__(self):
        return f'{self.id}-{self.user_strategy}-{self.platform}'


class AlertLog(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    strategy_alert = models.ForeignKey(StrategyAlert, related_name='logs', on_delete=models.CASCADE)
    log = models.TextField(_('log'), null=True, blank=True)

    def __repr__(self):
        return f'{self.id}-{self.strategy_alert}'
