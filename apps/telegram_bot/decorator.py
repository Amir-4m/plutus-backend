from .services import BotService


def add_session(view_func=None, clear=False):
    def inner(function):
        def params(*args, **kwargs):
            user_session = BotService.refresh_session(*args, **kwargs, clear=clear)
            return function(*args, **kwargs, session=user_session)

        return params

    if view_func:
        return inner(view_func)
    return inner
