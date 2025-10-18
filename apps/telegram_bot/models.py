from django.core.cache import caches
from django.db import models
from django.utils.translation import gettext_lazy as _


class TelegramUser(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    first_name = models.CharField(_("first name"), max_length=50, blank=True)
    last_name = models.CharField(_("last name"), max_length=50, blank=True)
    username = models.CharField(_("last name"), max_length=120, unique=True, blank=False, null=False)
    user_id = models.BigIntegerField(_("user id"), unique=True)
    is_enable = models.BooleanField(_("is enable?"), default=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.user_id}"

    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def session(self):
        session_cache = caches['session']
        ck = f'telegram_user_session_{self.user_id}'
        return session_cache.get(ck, {})
