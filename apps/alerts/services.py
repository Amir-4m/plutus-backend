from django.template import Template, Context

from apps.alerts import texts
from apps.alerts.models import StrategyAlert, Platform
from apps.telegram_bot.tasks import send_telegram_alert


class AlertService(object):
    @staticmethod
    def send_alert(strategy, context):
        alerts = StrategyAlert.objects.filter(user_strategy__strategy=strategy, is_enable=True)
        text = Template(texts.ALERT_TEXT).render(Context(context))
        for alert in alerts:
            if alert.platform.platform_type == Platform.PLATFORM_TELEGRAM:
                send_telegram_alert.delay(alert.id, text)
