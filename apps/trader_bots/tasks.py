import logging

from celery import shared_task

from apps.exchanges.models import ExchangeFuturesAsset
from apps.orders.models import FuturesOrder
from apps.trader_bots.models import TraderBot
from apps.trader_bots.services import AaxService, KucoinFuturesService

logger = logging.getLogger(__name__)


@shared_task()
def update_order_task(bot_id, order_id):
    logger.info(f'updating order, bot {bot_id}, {order_id}')

    bot = TraderBot.objects.get(id=bot_id)
    if bot.exchange.title == 'aax':
        order = FuturesOrder.objects.get(order_id=order_id)
        order_info = AaxService(
            api_key=bot.credential_data['api_key'],
            api_secret=bot.credential_data['api_secret']
        ).get_order(str(order_id)[:20])
        logger.info(f'updating order, response {str(order_info)}')
        if order_info['orderStatus'] == 3:
            order.is_active = True
            order.save()


@shared_task()
def close_position(bot_id, code_name, price):
    logger.info(f'closing position, bot {bot_id}, {code_name}')
    try:
        bot = TraderBot.objects.get(id=bot_id)
        exchange_service = {
            'aax': AaxService(
                api_key=bot.credential_data.get('api_key'),
                api_secret=bot.credential_data.get('api_secret')
            ),
            'kucoin': KucoinFuturesService(
                api_key=bot.credential_data.get('api_key'),
                api_secret=bot.credential_data.get('api_secret'),
                api_passphrase=bot.credential_data.get('api_passphrase')

            )
        }[bot.exchange.title]
        response = exchange_service.close_position(code_name)
        logger.info(f'closing position, response {str(response)}')
        if bot.exchange.title == 'aax':
            if response['code'] == 1:
                FuturesOrder.objects.filter(
                    user=bot.user,
                    exchange_futures_asset__exchange=bot.exchange,
                    exchange_futures_asset__code_name=code_name,
                    is_active=True).update(is_active=False, close_price=price)

        else:
            FuturesOrder.objects.filter(
                user=bot.user,
                exchange_futures_asset__exchange=bot.exchange,
                exchange_futures_asset__code_name=code_name,
                is_active=True).update(is_active=False, close_price=price)

    except Exception as e:
        logger.error(f'close position error bot {bot_id}, {code_name} : {e}')


@shared_task()
def create_order_task(bot_id, code_name, qty, side, leverage, price):
    bot = TraderBot.objects.get(id=bot_id)
    logger.info(f'creating order, bot:{bot_id}, {code_name}, {bot.exchange_id}, {qty}, {side}, {leverage}')
    try:
        asset = ExchangeFuturesAsset.objects.get(code_name=code_name, exchange_id=bot.exchange_id)
        close_position(bot_id, code_name, price)
        exchange_service = {
            'aax': AaxService(
                api_key=bot.credential_data.get('api_key'),
                api_secret=bot.credential_data.get('api_secret')
            ),
            'kucoin': KucoinFuturesService(
                api_key=bot.credential_data.get('api_key'),
                api_secret=bot.credential_data.get('api_secret'),
                api_passphrase=bot.credential_data.get('api_passphrase')

            )
        }[bot.exchange.title]
        order = exchange_service.create_order(asset, qty, side, leverage, bot.user, bot.exchange, price)
        logger.info(f'creating order, response {str(order)}')
        update_order_task.apply_async(args=(bot_id, order.order_id), countdown=3)
    except Exception as e:
        logger.error(f'creating order error bot {bot_id}, {code_name} : {e}')
