import logging

from celery import shared_task
from django.conf import settings
from telegram import Bot
from telegram.utils.request import Request

from apps.alerts.models import StrategyAlert, AlertLog
from apps.telegram_bot import buttons

logger = logging.getLogger(__name__)

bot = Bot(
    token=settings.TELEGRAM_BOT['TOKEN'],
    request=Request(con_pool_size=4, connect_timeout=3.05, read_timeout=27)
)


@shared_task()
def send_telegram_alert(strategy_alert_id, log):
    try:
        alert = StrategyAlert.objects.get(id=strategy_alert_id, is_enable=True)
        bot.send_message(
            text=log,
            chat_id=alert.extra_data['telegram_user_id'],
            reply_markup=buttons.start()
        )
        AlertLog.objects.create(strategy_alert=alert, log=log)
    except Exception as e:
        logger.error(f'sending telegram alert error: {e}')
