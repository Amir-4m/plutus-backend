import hashlib
import hmac
import json
import time
import uuid
import requests

from apps.orders.models import FuturesOrder


class AaxService(object):
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

    def create_order(self, asset, qty, side, leverage, user):
        verb = 'POST'
        path = '/v2/futures/orders'
        nonce = str(int(1000 * time.time()))
        order_id = uuid.uuid4()
        order_side = {
            FuturesOrder.SIDE_LONG: "BUY",
            FuturesOrder.SIDE_SHORT: "SELL"
        }[side]
        data = {
            "orderType": "MARKET",
            "symbol": asset.code_name,
            "orderQty": qty,
            "side": order_side,
            "clOrdID": str(order_id)[:20],
            "leverage": leverage
        }

        signature = hmac.new(self.api_secret.encode(), (str(nonce) + ':' + verb + path + json.dumps(data)).encode(), hashlib.sha256).hexdigest()

        nonce = str(int(1000 * time.time()))
        headers = {
            'X-ACCESS-NONCE': nonce,
            'X-ACCESS-KEY': self.api_key,
            'X-ACCESS-SIGN': signature,
        }
        response = requests.post(f'https://api.aax.com/v2/futures/orders', json=data, headers=headers).json()
        if response['code'] == 1:
            return FuturesOrder.objects.create(
                user=user,
                asset=asset,
                open_price=float(response['data']['marketPrice']),
                order_id=order_id,
                side=side,
                leverage=leverage,
                logs=str(response),
                is_active=False
            )

    def get_open_position(self, code_name):
        verb = 'GET'
        path = f'/v2/futures/position?symbol={code_name}'
        nonce = str(int(1000 * time.time()))
        data = ''
        signature = hmac.new(self.api_secret.encode(), (str(nonce) + ':' + verb + path + data).encode(), hashlib.sha256).hexdigest()

        params = {
            "symbol": code_name
        }
        headers = {
            'X-ACCESS-NONCE': nonce,
            'X-ACCESS-KEY': self.api_key,
            'X-ACCESS-SIGN': signature,
        }
        response = requests.get('https://api.aax.com/v2/futures/position', params=params, headers=headers).json()
        return response

    def close_position(self, code_name):
        verb = 'POST'
        path = f'/v2/futures/position/close'
        nonce = str(int(1000 * time.time()))
        data = {
            'symbol': code_name
        }
        signature = hmac.new(self.api_secret.encode(), (str(nonce) + ':' + verb + path + json.dumps(data)).encode(), hashlib.sha256).hexdigest()

        headers = {
            'X-ACCESS-NONCE': nonce,
            'X-ACCESS-KEY': self.api_key,
            'X-ACCESS-SIGN': signature,
        }
        response = requests.post('https://api.aax.com/v2/futures/position/close', json=data, headers=headers).json()
        return response

    def get_order(self, order_id):
        verb = 'GET'
        path = f'/v2/futures/orders?clOrdID={order_id}'
        nonce = str(int(1000 * time.time()))
        params = {
            'clOrdID': order_id
        }
        data = ''
        signature = hmac.new(self.api_secret.encode(), (str(nonce) + ':' + verb + path + data).encode(), hashlib.sha256).hexdigest()

        headers = {
            'X-ACCESS-NONCE': nonce,
            'X-ACCESS-KEY': self.api_key,
            'X-ACCESS-SIGN': signature,
        }
        response = requests.get('https://api.aax.com/v2/futures/orders', params=params, headers=headers).json()
        return response


class TraderBotService(object):
    @staticmethod
    def trade_on_strategy(strategies, side, code_name, action, price):
        from apps.trader_bots.tasks import create_order_task, close_position
        for strategy in strategies:
            if action == 'open':
                create_order_task.delay(
                    strategy.trader_bot.id,
                    code_name,
                    strategy.contracts,
                    side,
                    strategy.leverage
                )
            elif action == 'close':
                close_position.delay(
                    strategy.trader_bot.id,
                    code_name,
                    float(price)
                )
