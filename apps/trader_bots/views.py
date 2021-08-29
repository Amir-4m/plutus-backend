import logging

from django.db import transaction
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View

from apps.trader_bots.tasks import create_order_task, close_position

logger = logging.getLogger(__name__)


class WebHookView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(WebHookView, self).dispatch(request, *args, **kwargs)

    @transaction.atomic
    def post(self, request):
        payload = request.body
        logger.info(f'webhook called with data: {str(request.body)}')

        if payload['action'] == 'open':
            create_order_task.delay(
                payload['bot'],
                payload['exchange'],
                payload['qty'],
                payload['side'],
                payload['code_name'],
                payload['leverage'],
            )
        elif payload['action'] == 'close':
            close_position.delay(
                payload['bot'],
                payload['code_name'],
            )

        return HttpResponse('')
