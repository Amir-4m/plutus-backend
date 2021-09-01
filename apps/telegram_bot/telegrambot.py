import logging

from django.template import Template, Context
from telegram.ext import run_async

from . import texts, buttons
from .decorator import add_session
from .services import BotService
from ..alerts.models import StrategyAlert, AlertLog

logger = logging.getLogger(__name__)


@run_async
@add_session(clear=True)
def start(bot, update, session=None):
    user = session.get("user")
    bot.send_message(
        text=f"{texts.START_TEXT.format(user.first_name)}",
        chat_id=update.effective_user.id,
        reply_markup=buttons.start()
    )


@run_async
@add_session(clear=True)
def stop(bot, update, session):
    user = session.get("user")
    bot.send_message(
        chat_id=update.effective_user.id,
        text=f"{texts.STOP_TEXT.format(user.first_name)}"
    )


@run_async
@add_session()
def dispatcher(bot, update, session=None):
    user = session.get("user")
    text = update.message.text

    if text == texts.CREATE_ALERT_BUTTON:
        session['state'] = 'create_alert'
        bot.send_message(
            text=texts.CREATE_ALERT_TEXT,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )
    elif text == texts.STOP_ALERT_BUTTON:
        session['state'] = 'stop_alert'
        bot.send_message(
            text=texts.STOP_ALERT,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )

    elif text == texts.ALERT_LIST_BUTTON:
        try:
            logs = AlertLog.objects.filter(
                strategy_alert__extra_data__contains={'telegram_user_id': user.user_id},
            )[:15]
            if logs.count() > 0:
                t = Template(texts.ALERT_LIST)
                c = Context(dict(logs=logs))
                template = t.render(c)
            else:
                template = texts.NO_ALERT_EXISTS
            bot.send_message(
                text=template,
                chat_id=update.effective_user.id,
                reply_markup=buttons.start()
            )
        except Exception as e:
            logger.error(f'alert list error: {e}')
            bot.send_message(
                text=texts.ERROR_TEXT,
                chat_id=update.effective_user.id,
                reply_markup=buttons.start()
            )
    else:
        call_state_function(bot, update)
        return
    BotService.refresh_session(bot, update, session)


@run_async
@add_session
def call_state_function(bot, update, session):
    state = session.get('state')
    try:
        eval(state)(bot, update)
    except Exception:
        session.pop('state', None)  # refresh user state
        bot.send_message(chat_id=update.effective_user.id,
                         text=texts.WRONG_COMMAND,
                         reply_markup=buttons.start())


@run_async
@add_session()
def create_alert(bot, update, session=None):
    user = session.get("user")
    text = update.message.text
    try:
        logger.info(f'setting alert for {text}, {type(text)}')
        alert = StrategyAlert.objects.get(alert_key=text)
        alert.is_enable = True
        alert.extra_data['telegram_user_id'] = user.user_id
        alert.save()
        bot.send_message(
            text=texts.ALERT_CREATED_TEXT,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )
    except StrategyAlert.DoesNotExist:
        bot.send_message(
            text=texts.ALERT_NOT_EXISTS_TEXT,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )
    except Exception as e:
        logger.error(f'create_alert error: {e}')
        bot.send_message(
            text=texts.ERROR_TEXT,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )

    BotService.refresh_session(bot, update, session)


@run_async
@add_session()
def stop_alert(bot, update, session=None):
    text = update.message.text
    try:
        alert = StrategyAlert.objects.get(alert_key=text)
        alert.is_enable = False
        alert.save()
        bot.send_message(
            text=texts.STOP_ALERT_BUTTON,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )
    except StrategyAlert.DoesNotExist:
        bot.send_message(
            text=texts.ALERT_NOT_EXISTS_TEXT,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )
    except Exception as e:
        logger.error(f'stop_alert error: {e}')
        bot.send_message(
            text=texts.ERROR_TEXT,
            chat_id=update.effective_user.id,
            reply_markup=buttons.start()
        )

    BotService.refresh_session(bot, update, session)
