from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _


class Strategy(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    title = models.CharField(_("title"), max_length=120)
    code_name = models.CharField(_('code_name'), max_length=120)
    price = models.FloatField(_('price'))
    offer_price = models.FloatField(_('offer price'), null=True, blank=True)
    is_enable = models.BooleanField(_('is enable?'), default=True)


class UserStrategy(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_strategies')
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name='user_strategies')
    due_date = models.DateField(_('due date'))
    is_enable = models.BooleanField(default=False)
