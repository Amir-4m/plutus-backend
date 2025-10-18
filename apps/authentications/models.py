import uuid
from django.utils.translation import gettext_lazy as _
from django.db import models


class EmailVerification(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    uuid = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False, unique=True)
    user = models.ForeignKey(verbose_name=_('User'), to='auth.User', on_delete=models.CASCADE, related_name='verifications')
    email = models.EmailField(verbose_name=_('Email'))
    is_used = models.BooleanField(verbose_name='Used?', default=False)

    class Meta:
        unique_together = ('email', 'user')
