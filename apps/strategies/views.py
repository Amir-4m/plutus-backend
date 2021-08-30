import logging

from django.db import transaction
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View

from apps.alerts.services import AlertService
from apps.strategies.models import Strategy
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
        bot = payload.get('bot')
        strategy_title = payload.get('strategy')
        if strategy_title:
            try:
                strategy = Strategy.objects.get(title=strategy_title, is_enable=True)
                pos_side = payload['side']
                if payload['side'] == 'buy' and payload['action'] == 'close':
                    pos_side = 'sell'
                elif payload['side'] == 'sell' and payload['action'] == 'close':
                    pos_side = 'buy'

                context = {
                    'symbol': payload['symbol'],
                    'action': f'{payload["action"]} {pos_side} position',
                    'price': payload['price'],
                    'exchange': payload['exchange']
                }
                AlertService.send_alert(strategy, context)

            except Strategy.DoesNotExist:
                logger.error(f'webhook, strategy with title {strategy_title} does not exist or is not enable')
            except Exception as e:
                logger.error(f'webhook, error send alert: {e}')
        if bot:
            if payload['action'] == 'open':
                create_order_task.delay(
                    bot,
                    payload['exchange'],
                    payload['qty'],
                    payload['side'],
                    payload['code_name'],
                    payload['leverage'],
                )
            elif payload['action'] == 'close':
                close_position.delay(
                    bot,
                    payload['code_name'],
                )

        return HttpResponse('')
