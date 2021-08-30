import logging

from django.db import transaction
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View

from apps.alerts.services import AlertService
from apps.exchanges.models import Asset, ExchangeFuturesAsset
from apps.strategies.models import Strategy
from apps.trader_bots.services import TraderBotService

logger = logging.getLogger(__name__)


class WebHookView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(WebHookView, self).dispatch(request, *args, **kwargs)

    @transaction.atomic
    def post(self, request):
        payload = request.body
        logger.info(f'webhook called with data: {str(request.body)}')
        strategy_title = payload.get('strategy')
        try:
            strategy = Strategy.objects.get(title=strategy_title, is_enable=True, asset__symbol=payload['symbol'])
            exchange_asset = ExchangeFuturesAsset.objects.get(asset=strategy.asset, exchange__title=payload['exchange'])
            pos_side = payload['side']
            if payload['side'] == 'buy' and payload['action'] == 'close':
                pos_side = 'sell'
            elif payload['side'] == 'sell' and payload['action'] == 'close':
                pos_side = 'buy'

            context = {
                'symbol': exchange_asset.asset.symbol,
                'action': f'{payload["action"]} {pos_side} position',
                'price': payload['price'],
                'exchange': exchange_asset.exchange.title
            }
            AlertService.send_alert(strategy, context)
            user_strategies = strategy.user_strategies.select_related('trader_bot').filter(
                is_enable=True,
                trade=True,
                trade__isnull=False,
                trader_bot__exchange=exchange_asset.exchange
            )
            TraderBotService.trade_on_strategy(
                user_strategies,
                payload['side'],
                payload['code_name'],
                payload['action'],
                payload['price']
            )

        except Strategy.DoesNotExist:
            logger.error(f'webhook, strategy with title {strategy_title} does not exist or is not enable')
        except Exception as e:
            logger.error(f'webhook, error send alert: {e}')

        return HttpResponse('')
