import base64
import hashlib
import hmac
import json
import logging
import re
import time
import uuid
from urllib.parse import urlencode
from decimal import Decimal, InvalidOperation, ROUND_DOWN

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

    def create_order(
        self,
        asset,
        qty,
        side,
        leverage,
        user,
        exchange,
        price=0,
        reduce_only=False,
        record_order=True,
    ):
        endpoint = f'/api/v1/orders'
        api_version = '3'
        now = int(time.time() * 1000)
        passphrase = base64.b64encode(
            hmac.new(self.api_secret.encode('utf-8'), self.api_passphrase.encode('utf-8'), hashlib.sha256).digest())
        order_id = uuid.uuid4()

        def _format_size(value):
            if isinstance(value, Decimal):
                formatted = format(value.normalize(), 'f')
            elif isinstance(value, float):
                formatted = format(Decimal(str(value)).normalize(), 'f')
            else:
                formatted = str(value)
            if '.' in formatted:
                formatted = formatted.rstrip('0').rstrip('.')
            return formatted or '0'

        data = {
            "clientOid": str(order_id),
            "leverage": leverage,
            "side": side,
            "size": _format_size(qty),
            "symbol": asset.code_name,
            "type": "market",
            # "price": str(price),
            'marginMode': 'CROSS'
        }
        if reduce_only:
            data['reduceOnly'] = True
        str_to_sign = str(now) + 'POST' + endpoint + json.dumps(data)
        signature = base64.b64encode(
            hmac.new(self.api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
        headers = {
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(now),
            "KC-API-KEY": self.api_key,
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": api_version
        }

        response = requests.post(url=f'{self.base_url}{endpoint}', headers=headers, json=data)
        try:
            response.raise_for_status()
        except Exception:
            logger.error(
                'creating kucoin order failed: status=%s, body=%s',
                response.status_code,
                response.text
            )
            raise
        response_data = response.json()
        logger.info(
            'creating kucoin order success: order_id=%s reduce_only=%s payload=%s',
            order_id,
            reduce_only,
            response_data
        )
        if not record_order:
            return response_data
        return FuturesOrder.objects.create(
            user=user,
            exchange_futures_asset=asset,
            open_price=float(price),
            order_id=order_id,
            side=side,
            leverage=leverage,
            logs=str(response_data),
            is_active=True
        )

    def close_position(self, code_name, price=0):
        endpoint = f'/api/v1/orders'
        api_version = '3'
        now = int(time.time() * 1000)
        passphrase = base64.b64encode(
            hmac.new(self.api_secret.encode('utf-8'), self.api_passphrase.encode('utf-8'), hashlib.sha256).digest())
        order_id = uuid.uuid4()

        data = {
            "clientOid": str(order_id),
            "closeOrder": True,
            "symbol": code_name,
            "type": "market",
            # "price": str(price),
        }
        str_to_sign = str(now) + 'POST' + endpoint + json.dumps(data)
        signature = base64.b64encode(
            hmac.new(self.api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
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

    def get_position(self, code_name):
        endpoint = '/api/v2/position'
        api_version = '3'
        now = int(time.time() * 1000)
        passphrase = base64.b64encode(
            hmac.new(self.api_secret.encode('utf-8'), self.api_passphrase.encode('utf-8'), hashlib.sha256).digest())

        params = {'symbol': code_name}
        query_string = urlencode(params)
        request_path = f'{endpoint}?{query_string}'
        str_to_sign = str(now) + 'GET' + request_path
        signature = base64.b64encode(
            hmac.new(self.api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
        headers = {
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(now),
            "KC-API-KEY": self.api_key,
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": api_version
        }

        response = requests.get(url=f'{self.base_url}{endpoint}', headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        logger.debug('kucoin position response for %s: %s', code_name, data)
        return data

    def reduce_position(
        self,
        asset,
        qty_percent,
        side,
        leverage,
        user,
        exchange,
        price=0,
        action_comment=None,
        alert_order_id=None,
    ):
        try:
            percent_decimal = Decimal(str(qty_percent))
        except (InvalidOperation, TypeError):
            logger.error('invalid qty_percent value provided for reduce_position: %s', qty_percent)
            return None

        position_response = self.get_position(asset.code_name)
        position_data = position_response.get('data') or {}
        current_qty_raw = position_data.get('currentQty')

        try:
            current_qty = Decimal(str(current_qty_raw))
        except (InvalidOperation, TypeError):
            logger.error('unable to parse currentQty from position response: %s', current_qty_raw)
            return None

        abs_qty = current_qty.copy_abs()
        if abs_qty == 0:
            logger.info('no active position to reduce for %s', asset.code_name)
            return position_response

        percent_ratio = percent_decimal / Decimal('100')
        qty_to_close = abs_qty * percent_ratio

        exponent = abs_qty.as_tuple().exponent
        quantize_unit = Decimal(1).scaleb(exponent) if exponent < 0 else Decimal('1')
        qty_to_close = qty_to_close.quantize(quantize_unit, rounding=ROUND_DOWN)

        if qty_to_close <= 0 and abs_qty > 0:
            qty_to_close = quantize_unit

        if qty_to_close <= 0:
            logger.info(
                'calculated qty to close is zero for %s (percent=%s, current_qty=%s)',
                asset.code_name,
                qty_percent,
                current_qty
            )
            return position_response

        qty_to_close = min(qty_to_close, abs_qty)

        response = self.create_order(
            asset=asset,
            qty=qty_to_close,
            side=side,
            leverage=leverage,
            user=user,
            exchange=exchange,
            price=price,
            reduce_only=True,
            record_order=False
        )
        logger.info(
            'reduce position order submitted: asset=%s percent=%s qty=%s side=%s comment=%s alert_order_id=%s response=%s',
            asset.code_name,
            qty_percent,
            format(qty_to_close.normalize(), 'f'),
            side,
            action_comment,
            alert_order_id,
            response
        )
        return response

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

        signature = hmac.new(self.api_secret.encode(), (str(nonce) + ':' + verb + path + json.dumps(data)).encode(),
                             hashlib.sha256).hexdigest()

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
        signature = hmac.new(self.api_secret.encode(), (str(nonce) + ':' + verb + path + data).encode(),
                             hashlib.sha256).hexdigest()

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
        signature = hmac.new(self.api_secret.encode(), (str(nonce) + ':' + verb + path + json.dumps(data)).encode(),
                             hashlib.sha256).hexdigest()

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
        signature = hmac.new(self.api_secret.encode(), (str(nonce) + ':' + verb + path + data).encode(),
                             hashlib.sha256).hexdigest()

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
    def _extract_tp_percent(action_comment):
        if not action_comment:
            return None
        match = re.search(r'pct=([0-9]+(?:\.[0-9]+)?)', action_comment)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    @staticmethod
    def trade_on_strategy(strategies, side, code_name, action, price, order_id=None):
        from apps.trader_bots.tasks import (
            CREATE_ORDER_COUNTDOWN,
            close_position_task,
            create_order_task,
            reduce_position_task,
        )
        normalized_action = (action or '').lower()
        percent = TraderBotService._extract_tp_percent(action)
        for strategy in strategies:
            if normalized_action == 'open':
                create_order_task.apply_async(
                    args=(
                        strategy.trader_bot.id,
                        code_name,
                        strategy.contracts,
                        side,
                        strategy.leverage,
                        float(price)
                    ),
                    countdown=CREATE_ORDER_COUNTDOWN
                )
            elif normalized_action == 'close' or (percent is None and 'close' in normalized_action):
                close_position_task.delay(
                    strategy.trader_bot.id,
                    code_name,
                    float(price)
                )
            elif percent is not None:
                reduce_position_task.delay(
                    strategy.trader_bot.id,
                    code_name,
                    side,
                    percent,
                    strategy.leverage,
                    float(price),
                    action,
                    order_id
                )
            else:
                logger.info(
                    'Unhandled strategy action received: action=%s, side=%s, code_name=%s, order_id=%s',
                    action,
                    side,
                    code_name,
                    order_id
                )
