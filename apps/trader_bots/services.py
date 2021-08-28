import hashlib
import hmac
import json
import time
import uuid

from django.contrib.auth.models import User
from apps.orders.models import FuturesOrder

import requests

# class KucoinFuturesService(object):
#     def __init__(self, sandbox=False):
#         super(KucoinFuturesService, self).__init__()
#         if sandbox:
#             self.base_url = 'https://api-sandbox-futures.kucoin.com'
#         else:
#             self.base_url = 'https://api-futures.kucoin.com'
#
#     def create_order(self):
#         # bot_properties = bot.credential_data
#         endpoint = f'/api/v1/orders'
#         symbol = 'XBTUSDTM'
#         api_key = '612a37dcbc85c200065aa39d'
#         api_version = '2'
#         api_passphrase = 'testapikey'
#         api_secret = '78f6c66f-4031-4957-a82a-a67ac4edb2aa'
#         now = int(time.time() * 1000)
#         passphrase = base64.b64encode(hmac.new(api_secret.encode('utf-8'), api_passphrase.encode('utf-8'), hashlib.sha256).digest())
#         order_id = uuid.uuid4()
#
#         data = {
#             "clientOid": str(order_id),
#             # "leverage": 5,
#             "side": "buy",
#             # "stop": "down",
#             "leverage": 5,
#             # "stopPrice": 48674,
#             # "stopPriceType": "MP",
#             "size": 35,
#             "symbol": "XBTUSDTM",
#             "type": "market",
#         }
#         str_to_sign = str(now) + 'POST' + endpoint + json.dumps(data)
#         signature = base64.b64encode(hmac.new(api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
#         headers = {
#             "KC-API-SIGN": signature,
#             "KC-API-TIMESTAMP": str(now),
#             "KC-API-KEY": api_key,
#             "KC-API-PASSPHRASE": passphrase,
#             "KC-API-KEY-VERSION": api_version
#         }
#
#         response = requests.post(url=f'{self.base_url}{endpoint}', headers=headers, json=data)
#         print(response.status_code)
#         print(response.json())
#
#     def get_order(self):
#         # bot_properties = bot.credential_data
#         endpoint = f'/api/v1/orders/612a8790fa1b4f000614a4aa'
#         symbol = 'XBTUSDTM'
#         api_key = '612a37dcbc85c200065aa39d'
#         api_version = '2'
#         api_passphrase = 'testapikey'
#         api_secret = '78f6c66f-4031-4957-a82a-a67ac4edb2aa'
#         now = int(time.time() * 1000)
#         passphrase = base64.b64encode(hmac.new(api_secret.encode('utf-8'), api_passphrase.encode('utf-8'), hashlib.sha256).digest())
#         order_id = uuid.uuid4()
#
#         data = {
#             "clientOid": order_id,
#             "leverage": 5,
#             "side": "buy",
#             "size": 3,
#             "symbol": "ETHUSDTM",
#             "type": "market",
#         }
#         str_to_sign = str(now) + 'GET' + endpoint
#         signature = base64.b64encode(hmac.new(api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
#         headers = {
#             "KC-API-SIGN": signature,
#             "KC-API-TIMESTAMP": str(now),
#             "KC-API-KEY": api_key,
#             "KC-API-PASSPHRASE": passphrase,
#             "KC-API-KEY-VERSION": api_version
#         }
#
#         response = requests.get(url=f'{self.base_url}{endpoint}', headers=headers)
#         print(response.status_code)
#         print(response.json())
#         return response
#
#     def get_orders(self):
#         # bot_properties = bot.credential_data
#         endpoint = f'/api/v1/orders'
#         symbol = 'XBTUSDTM'
#         api_key = '612a37dcbc85c200065aa39d'
#         api_version = '2'
#         api_passphrase = 'testapikey'
#         api_secret = '78f6c66f-4031-4957-a82a-a67ac4edb2aa'
#         now = int(time.time() * 1000)
#         passphrase = base64.b64encode(hmac.new(api_secret.encode('utf-8'), api_passphrase.encode('utf-8'), hashlib.sha256).digest())
#         order_id = uuid.uuid4()
#
#         data = {
#             "clientOid": order_id,
#             "leverage": 5,
#             "side": "buy",
#             "size": 3,
#             "symbol": "ETHUSDTM",
#             "type": "market",
#         }
#         str_to_sign = str(now) + 'GET' + endpoint
#         signature = base64.b64encode(hmac.new(api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
#         headers = {
#             "KC-API-SIGN": signature,
#             "KC-API-TIMESTAMP": str(now),
#             "KC-API-KEY": api_key,
#             "KC-API-PASSPHRASE": passphrase,
#             "KC-API-KEY-VERSION": api_version
#         }
#
#         response = requests.get(url=f'{self.base_url}{endpoint}', headers=headers)
#         print(response.status_code)
#         print(response.json())
#
#     def get_positions(self):
#         # bot_properties = bot.credential_data
#         endpoint = f'/api/v1/positions'
#         symbol = 'XBTUSDTM'
#         api_key = '612a37dcbc85c200065aa39d'
#         api_version = '2'
#         api_passphrase = 'testapikey'
#         api_secret = '78f6c66f-4031-4957-a82a-a67ac4edb2aa'
#         now = int(time.time() * 1000)
#         passphrase = base64.b64encode(hmac.new(api_secret.encode('utf-8'), api_passphrase.encode('utf-8'), hashlib.sha256).digest())
#         order_id = uuid.uuid4()
#
#         data = {
#             "clientOid": order_id,
#             "leverage": 5,
#             "side": "buy",
#             "size": 3,
#             "symbol": "ETHUSDTM",
#             "type": "market",
#         }
#         str_to_sign = str(now) + 'GET' + endpoint
#         signature = base64.b64encode(hmac.new(api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
#         headers = {
#             "KC-API-SIGN": signature,
#             "KC-API-TIMESTAMP": str(now),
#             "KC-API-KEY": api_key,
#             "KC-API-PASSPHRASE": passphrase,
#             "KC-API-KEY-VERSION": api_version
#         }
#
#         response = requests.get(url=f'{self.base_url}{endpoint}', headers=headers)
#         print(response.status_code)
#         print(response.json())


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
                open_price=response['data']['marketPrice'],
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
