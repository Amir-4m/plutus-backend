from telegram import KeyboardButton, ReplyKeyboardMarkup
from . import texts


def start():
    buttons = [
        [KeyboardButton(texts.CREATE_ALERT_BUTTON)],
        [KeyboardButton(texts.STOP_ALERT_BUTTON)],
        [KeyboardButton(texts.ALERT_LIST_BUTTON)]

    ]

    return ReplyKeyboardMarkup(buttons, one_time_keyboard=True)
