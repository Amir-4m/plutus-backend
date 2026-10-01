import hmac
import json
import logging

from django.conf import settings
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


def _optional_float(value):
    if value in (None, ''):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class WebHookView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(WebHookView, self).dispatch(request, *args, **kwargs)

    @transaction.atomic
    def post(self, request):
        logger.info(f'webhook called with data: {str(request.body)}')
        try:
            payload = json.loads(request.body)
        except (TypeError, ValueError) as e:
            logger.error(f'webhook, invalid json payload: {e}')
            return HttpResponse('invalid payload', status=400)
        if not isinstance(payload, dict):
            logger.error('webhook, payload is not a json object')
            return HttpResponse('invalid payload', status=400)

        expected_secret = settings.STRATEGY_WEBHOOK_SECRET
        if expected_secret:
            received_secret = str(payload.get('secret') or '')
            if not hmac.compare_digest(received_secret.encode(), expected_secret.encode()):
                logger.error('webhook, rejected: missing or invalid secret')
                return HttpResponse('forbidden', status=403)
        else:
            logger.warning('webhook, STRATEGY_WEBHOOK_SECRET is not set; accepting unauthenticated webhook')

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
                exchange_asset.code_name,
                payload['action'],
                payload['price'],
                payload.get('ID'),
                size_pct=_optional_float(payload.get('size_pct')),
                stop_price=_optional_float(payload.get('stop')),
            )

        except Strategy.DoesNotExist:
            logger.error(f'webhook, strategy with title {strategy_title} does not exist or is not enable')
        except Exception as e:
            logger.error(f'webhook, error send alert: {e}')

        return HttpResponse('')
