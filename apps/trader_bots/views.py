import logging

from django.db import transaction
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View

logger = logging.getLogger(__name__)


class WebHookView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(WebHookView, self).dispatch(request, *args, **kwargs)

    @transaction.atomic
    def post(self, request):
        payload = request.body
        print(payload)
        return HttpResponse('')
