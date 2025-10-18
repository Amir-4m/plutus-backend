import base64
import hashlib
import hmac
import json
import logging
import time
import uuid
from urllib.parse import urlencode
import requests

from apps.orders.models import FuturesOrder

logger = logging.getLogger(__name__)


class KucoinFuturesService(object):
    def __init__(self, api_key, api_secret, api_passphrase, sandbox=False):
        super(KucoinFuturesService, self).__init__()
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase

        if sandbox:
            self.base_url = 'https://api-sandbox-futures.kucoin.com'
        else:
            self.base_url = 'https://api-futures.kucoin.com'

    def create_order(self, asset, qty, side, leverage, user, exchange, price=0):
        endpoint = f'/api/v1/orders'
        api_version = '3'
        now = int(time.time() * 1000)
        passphrase = base64.b64encode(hmac.new(self.api_secret.encode('utf-8'), self.api_passphrase.encode('utf-8'), hashlib.sha256).digest())
        order_id = uuid.uuid4()

        data = {
            "clientOid": str(order_id),
            "leverage": leverage,
            "side": side,
            "size": qty,
            "symbol": asset.code_name,
            "type": "limit",
            'marginMode': 'CROSS'
        }
        str_to_sign = str(now) + 'POST' + endpoint + json.dumps(data)
        signature = base64.b64encode(hmac.new(self.api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
        headers = {
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(now),
            "KC-API-KEY": self.api_key,
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": api_version
        }

        response = requests.post(url=f'{self.base_url}{endpoint}', headers=headers, json=data)
        logger.info(f'creating kucoin order: {response.json()}')
        response.raise_for_status()
        response = response.json()
        return FuturesOrder.objects.create(
            user=user,
            exchange_futures_asset=asset,
            open_price=float(price),
            order_id=order_id,
            side=side,
            leverage=leverage,
            logs=str(response),
            is_active=True
        )

    def close_position(self, code_name):
        endpoint = f'/api/v1/orders'
        api_version = '3'
        now = int(time.time() * 1000)
        passphrase = base64.b64encode(hmac.new(self.api_secret.encode('utf-8'), self.api_passphrase.encode('utf-8'), hashlib.sha256).digest())
        order_id = uuid.uuid4()

        data = {
            "clientOid": str(order_id),
            "closeOrder": True,
            "symbol": code_name,
            "type": "limit",
        }
        str_to_sign = str(now) + 'POST' + endpoint + json.dumps(data)
        signature = base64.b64encode(hmac.new(self.api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
        headers = {
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(now),
            "KC-API-KEY": self.api_key,
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": api_version
        }

        response = requests.post(url=f'{self.base_url}{endpoint}', headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def get_account_futures(self, currency=None):
        endpoint = '/api/v1/account-overview'
        api_version = '3'
        now = int(time.time() * 1000)
        passphrase = base64.b64encode(
            hmac.new(self.api_secret.encode('utf-8'), self.api_passphrase.encode('utf-8'), hashlib.sha256).digest()
        )

        params = {}
        if currency:
            params['currency'] = currency

        query_string = urlencode(params)
        request_path = endpoint if not query_string else f'{endpoint}?{query_string}'
        str_to_sign = str(now) + 'GET' + request_path
        signature = base64.b64encode(
            hmac.new(self.api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest()
        )
        headers = {
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(now),
            "KC-API-KEY": self.api_key,
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": api_version
        }

        response = requests.get(f'{self.base_url}{request_path}', headers=headers)
        response.raise_for_status()
        return response.json()


class AaxService(object):
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

    def create_order(self, asset, qty, side, leverage, user, exchange, price=0):
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
        response = requests.post(f'https://api.aax.com/v2/futures/orders', json=data, headers=headers)
        response.raise_for_status()
        response = response.json()
        if response['code'] == 1:
            return FuturesOrder.objects.create(
                user=user,
                exchange_futures_asset=asset,
                open_price=float(price),
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
        response = requests.get('https://api.aax.com/v2/futures/position', params=params, headers=headers)
        response.raise_for_status()
        response = response.json()
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
        response = requests.post('https://api.aax.com/v2/futures/position/close', json=data, headers=headers)
        response.raise_for_status()
        response = response.json()
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
        response = requests.get('https://api.aax.com/v2/futures/orders', params=params, headers=headers)
        response.raise_for_status()
        response = response.json()
        return response


class TraderBotService(object):
    @staticmethod
    def trade_on_strategy(strategies, side, code_name, action, price):
        from apps.trader_bots.tasks import create_order_task, close_position
        for strategy in strategies:
            if action == 'open':
                create_order_task.apply_async(
                    args=(
                        strategy.trader_bot.id,
                        code_name,
                        strategy.contracts,
                        side,
                        strategy.leverage,
                        float(price)
                    ),
                    countdown=10
                )
            elif action == 'close':
                close_position.delay(
                    strategy.trader_bot.id,
                    code_name,
                    float(price)
                )
