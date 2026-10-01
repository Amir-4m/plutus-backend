import base64
import hashlib
import hmac
import json
import logging
import re
import time
import uuid
from urllib.parse import urlencode
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_UP

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

    @staticmethod
    def _ensure_decimal(value):
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError):
            return None

    @staticmethod
    def _format_decimal(value):
        decimal_value = KucoinFuturesService._ensure_decimal(value)
        if decimal_value is None:
            return None
        normalized = decimal_value.normalize()
        formatted = format(normalized, 'f')
        if '.' in formatted:
            formatted = formatted.rstrip('0').rstrip('.')
        return formatted or '0'

    def _auth_headers(self, method, request_path, body=''):
        now = int(time.time() * 1000)
        passphrase = base64.b64encode(
            hmac.new(self.api_secret.encode('utf-8'), self.api_passphrase.encode('utf-8'), hashlib.sha256).digest())
        str_to_sign = str(now) + method + request_path + body
        signature = base64.b64encode(
            hmac.new(self.api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
        return {
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(now),
            "KC-API-KEY": self.api_key,
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": '3',
            "Content-Type": "application/json",
        }

    @staticmethod
    def _quantize_to_step(value, step, rounding):
        return (value / step).to_integral_value(rounding=rounding) * step

    def get_contract(self, code_name):
        response = requests.get(f'{self.base_url}/api/v1/contracts/{code_name}')
        response.raise_for_status()
        return response.json().get('data') or {}

    def calculate_order_size(self, code_name, size_pct, price):
        """Convert a % of account equity into a number of contracts.

        Returns None when the size cannot be derived for this contract (caller should fall back
        to its fixed size), or Decimal('0') when the position would be smaller than one lot.
        """
        size_pct_decimal = self._ensure_decimal(size_pct)
        price_decimal = self._ensure_decimal(price)
        if not size_pct_decimal or size_pct_decimal <= 0 or not price_decimal or price_decimal <= 0:
            return None

        contract = self.get_contract(code_name)
        multiplier = self._ensure_decimal(contract.get('multiplier'))
        lot_size = self._ensure_decimal(contract.get('lotSize')) or Decimal('1')
        settle_currency = contract.get('settleCurrency') or 'USDT'
        if multiplier is None or multiplier <= 0 or contract.get('isInverse'):
            logger.warning('kucoin contract %s is not a linear contract, cannot size by equity', code_name)
            return None

        account = self.get_account_futures(settle_currency).get('data') or {}
        equity = self._ensure_decimal(account.get('accountEquity'))
        if equity is None or equity <= 0:
            logger.warning('kucoin account equity unavailable for %s: %s', settle_currency, account)
            return None

        notional = equity * size_pct_decimal / Decimal('100')
        size = self._quantize_to_step(notional / (price_decimal * multiplier), lot_size, ROUND_DOWN)
        logger.info(
            'kucoin order size for %s: equity=%s %s, size_pct=%s, price=%s, multiplier=%s -> %s contracts',
            code_name, equity, settle_currency, size_pct_decimal, price_decimal, multiplier, size
        )
        return max(size, Decimal('0'))

    def place_stop_loss(self, asset, position_side, stop_price):
        """Reduce-only stop on the exchange that closes the whole position if price crosses stop_price."""
        stop_decimal = self._ensure_decimal(stop_price)
        if stop_decimal is None or stop_decimal <= 0:
            return None

        contract = self.get_contract(asset.code_name)
        tick_size = self._ensure_decimal(contract.get('tickSize'))
        is_long = position_side == FuturesOrder.SIDE_LONG
        if tick_size and tick_size > 0:
            # round away from the market so the stop is never tighter than requested
            stop_decimal = self._quantize_to_step(stop_decimal, tick_size, ROUND_DOWN if is_long else ROUND_UP)

        endpoint = '/api/v1/orders'
        data = {
            "clientOid": str(uuid.uuid4()),
            "side": FuturesOrder.SIDE_SHORT if is_long else FuturesOrder.SIDE_LONG,
            "symbol": asset.code_name,
            "type": "market",
            "stop": "down" if is_long else "up",
            "stopPriceType": "TP",
            "stopPrice": self._format_decimal(stop_decimal),
            "closeOrder": True,
            "marginMode": "CROSS",
        }
        body = json.dumps(data)
        response = requests.post(
            url=f'{self.base_url}{endpoint}', headers=self._auth_headers('POST', endpoint, body), data=body
        )
        try:
            response.raise_for_status()
        except Exception:
            logger.error(
                'placing kucoin stop loss failed: status=%s, body=%s',
                response.status_code,
                response.text
            )
            raise
        response_data = response.json()
        logger.info('placing kucoin stop loss success: symbol=%s stop=%s payload=%s',
                    asset.code_name, data['stopPrice'], response_data)
        return response_data

    def cancel_stop_orders(self, code_name):
        endpoint = '/api/v1/stopOrders'
        request_path = f'{endpoint}?{urlencode({"symbol": code_name})}'
        response = requests.delete(
            url=f'{self.base_url}{request_path}', headers=self._auth_headers('DELETE', request_path)
        )
        response.raise_for_status()
        response_data = response.json()
        logger.info('cancel kucoin stop orders: symbol=%s payload=%s', code_name, response_data)
        return response_data

    def _fetch_top_of_book(self, symbol):
        endpoint = '/api/v1/level2/depth20'
        response = requests.get(f'{self.base_url}{endpoint}', params={'symbol': symbol})
        response.raise_for_status()
        payload = response.json() or {}
        data = payload.get('data') or {}
        asks = data.get('asks') or []
        bids = data.get('bids') or []

        def _extract_price(levels):
            if not levels:
                return None
            first_level = levels[0]
            if isinstance(first_level, (list, tuple)) and first_level:
                return self._ensure_decimal(first_level[0])
            if isinstance(first_level, dict):
                return self._ensure_decimal(first_level.get('price'))
            return None

        best_ask = _extract_price(asks)
        best_bid = _extract_price(bids)
        return best_bid, best_ask

    def _select_limit_price(self, symbol, side, fallback_price):
        fallback_decimal = self._ensure_decimal(fallback_price)
        try:
            best_bid, best_ask = self._fetch_top_of_book(symbol)
        except Exception as exc:
            logger.warning('kucoin orderbook unavailable for %s: %s', symbol, exc)
            if fallback_decimal is None:
                raise
            return fallback_decimal

        if side == FuturesOrder.SIDE_LONG:
            chosen = best_ask or fallback_decimal
        else:
            chosen = best_bid or fallback_decimal

        if chosen is None:
            raise ValueError(f'unable to determine limit price for {symbol}')
        return chosen

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

        limit_price = self._select_limit_price(asset.code_name, side, price)
        price_str = self._format_decimal(limit_price)

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
            "type": "limit",
            "price": price_str,
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
            open_price=float(limit_price),
            order_id=order_id,
            side=side,
            leverage=leverage,
            logs=str(response_data),
            is_active=True
        )

    def close_position(self, asset, user, exchange, price=0):
        result = self._submit_close_order(asset, user, exchange, price)
        # the position is flat (or never filled): drop the protective stop so it can't hit a later position
        try:
            self.cancel_stop_orders(asset.code_name)
        except Exception as exc:
            logger.error('cancel kucoin stop orders failed for %s: %s', asset.code_name, exc)
        return result

    def _submit_close_order(self, asset, user, exchange, price=0):
        position_response = self.get_position(asset.code_name)
        position_data = position_response.get('data') or []
        if isinstance(position_data, dict):
            position_data = [position_data]
        if not position_data:
            logger.info('no kucoin position to close for %s', asset.code_name)
            price_decimal = self._ensure_decimal(price)
            return {'response': position_response, 'price': float(price_decimal) if price_decimal else None}

        current_qty_raw = position_data[0].get('currentQty')
        current_qty = self._ensure_decimal(current_qty_raw)
        if current_qty is None or current_qty == 0:
            logger.info('kucoin position size is zero for %s', asset.code_name)
            price_decimal = self._ensure_decimal(price)
            return {'response': position_response, 'price': float(price_decimal) if price_decimal else None}

        close_side = FuturesOrder.SIDE_SHORT if current_qty > 0 else FuturesOrder.SIDE_LONG
        qty_to_close = current_qty.copy_abs()
        leverage_value = (
                position_data[0].get('currentLeverage')
                or position_data[0].get('maxLeverage')
                or position_data[0].get('leverage')
                or 1
        )
        limit_price = self._select_limit_price(asset.code_name, close_side, price)

        response_data = self.create_order(
            asset=asset,
            qty=qty_to_close,
            side=close_side,
            leverage=leverage_value or 1,
            user=user,
            exchange=exchange,
            price=limit_price,
            reduce_only=True,
            record_order=False
        )
        return {
            'response': response_data,
            'price': float(limit_price)
        }

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
        position_data = position_response.get('data') or []
        if isinstance(position_data, dict):
            position_data = [position_data]
        if not position_data:
            logger.info('no kucoin position to reduce for %s', asset.code_name)
            return position_response
        current_qty_raw = position_data[0].get('currentQty')

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

    @staticmethod
    def _ensure_decimal(value):
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError):
            return None

    @staticmethod
    def _format_decimal(value):
        decimal_value = AaxService._ensure_decimal(value)
        if decimal_value is None:
            return None
        normalized = decimal_value.normalize()
        formatted = format(normalized, 'f')
        if '.' in formatted:
            formatted = formatted.rstrip('0').rstrip('.')
        return formatted or '0'

    def _fetch_top_of_book(self, symbol):
        params = {'symbol': symbol}
        response = requests.get('https://api.aax.com/v2/market/orderbook', params=params)
        response.raise_for_status()
        payload = response.json() or {}
        data = payload.get('data') or {}
        asks = data.get('asks') or data.get('a') or []
        bids = data.get('bids') or data.get('b') or []

        def _extract_price(levels):
            if not levels:
                return None
            first_level = levels[0]
            if isinstance(first_level, (list, tuple)) and first_level:
                return self._ensure_decimal(first_level[0])
            if isinstance(first_level, dict):
                price_value = first_level.get('price') or first_level.get('p')
                return self._ensure_decimal(price_value)
            return None

        best_ask = _extract_price(asks)
        best_bid = _extract_price(bids)
        return best_bid, best_ask

    def _select_limit_price(self, symbol, side, fallback_price):
        fallback_decimal = self._ensure_decimal(fallback_price)
        try:
            best_bid, best_ask = self._fetch_top_of_book(symbol)
        except Exception as exc:
            logger.warning('aax orderbook unavailable for %s: %s', symbol, exc)
            if fallback_decimal is None:
                raise
            return fallback_decimal

        if side == FuturesOrder.SIDE_LONG:
            chosen = best_ask or fallback_decimal
        else:
            chosen = best_bid or fallback_decimal

        if chosen is None:
            raise ValueError(f'unable to determine limit price for {symbol}')
        return chosen

    def create_order(self, asset, qty, side, leverage, user, exchange, price=0, reduce_only=False, record_order=True):
        verb = 'POST'
        path = '/v2/futures/orders'
        nonce = str(int(1000 * time.time()))
        order_id = uuid.uuid4()
        order_side = {
            FuturesOrder.SIDE_LONG: "BUY",
            FuturesOrder.SIDE_SHORT: "SELL"
        }[side]
        limit_price = self._select_limit_price(asset.code_name, side, price)
        price_str = self._format_decimal(limit_price)
        qty_str = self._format_decimal(qty)
        data = {
            "orderType": "LIMIT",
            "symbol": asset.code_name,
            "orderQty": qty_str,
            "side": order_side,
            "clOrdID": str(order_id)[:20],
            "leverage": leverage,
            "price": price_str,
            "timeInForce": "GoodTillCancel"
        }
        if reduce_only:
            data["reduceOnly"] = True

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
            if not record_order:
                return response
            return FuturesOrder.objects.create(
                user=user,
                exchange_futures_asset=asset,
                open_price=float(limit_price),
                order_id=order_id,
                side=side,
                leverage=leverage,
                logs=str(response),
                is_active=False
            )
        return response

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

    def close_position(self, asset, user, exchange, price=0):
        position_response = self.get_open_position(asset.code_name)
        positions_data = position_response.get('data') or []
        if isinstance(positions_data, dict):
            positions_data = positions_data.get('positions') or positions_data.get('items') or [positions_data]
        if not positions_data:
            logger.info('no aax position to close for %s', asset.code_name)
            price_decimal = self._ensure_decimal(price)
            return {'response': position_response, 'price': float(price_decimal) if price_decimal else None}

        position = None
        for entry in positions_data:
            symbol_value = entry.get('symbol') or entry.get('symbolCode') or entry.get('contract')
            if not symbol_value or symbol_value != asset.code_name:
                continue
            position = entry
            break
        if position is None:
            position = positions_data[0]

        qty_keys = ['positionQty', 'currentQty', 'size', 'posQty', 'holdVol', 'positionAmt', 'openContract',
                    'openVolume']
        qty_raw = None
        for key in qty_keys:
            qty_raw = position.get(key)
            if qty_raw is not None:
                break
        qty_decimal = self._ensure_decimal(qty_raw)
        if qty_decimal is None or qty_decimal == 0:
            logger.info('aax position size is zero for %s', asset.code_name)
            price_decimal = self._ensure_decimal(price)
            return {'response': position_response, 'price': float(price_decimal) if price_decimal else None}

        side_raw = (position.get('positionSide') or position.get('posSide') or position.get('side') or '').lower()
        if side_raw in ('long', 'buy'):
            close_side = FuturesOrder.SIDE_SHORT
        elif side_raw in ('short', 'sell'):
            close_side = FuturesOrder.SIDE_LONG
        else:
            close_side = FuturesOrder.SIDE_SHORT if qty_decimal > 0 else FuturesOrder.SIDE_LONG

        limit_price = self._select_limit_price(asset.code_name, close_side, price)
        leverage_value = (
                position.get('leverage')
                or position.get('realLeverage')
                or position.get('currentLeverage')
                or 1
        )
        response_data = self.create_order(
            asset=asset,
            qty=qty_decimal.copy_abs(),
            side=close_side,
            leverage=leverage_value or 1,
            user=user,
            exchange=exchange,
            price=limit_price,
            reduce_only=True,
            record_order=False
        )
        return {
            'response': response_data,
            'price': float(limit_price)
        }

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
    def trade_on_strategy(strategies, side, code_name, action, price, order_id=None, size_pct=None, stop_price=None):
        from apps.trader_bots.tasks import (
            CREATE_ORDER_COUNTDOWN,
            close_position_task,
            create_order_task,
            reduce_position_task,
        )
        normalized_action = (action or '').lower()
        percent = TraderBotService._extract_tp_percent(action)
        if stop_price is not None and normalized_action == 'open':
            stop_on_wrong_side = (
                (side == FuturesOrder.SIDE_LONG and stop_price >= float(price))
                or (side == FuturesOrder.SIDE_SHORT and stop_price <= float(price))
            )
            if stop_on_wrong_side:
                logger.warning('ignoring stop %s on wrong side of %s entry at %s', stop_price, side, price)
                stop_price = None
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
                    kwargs={'size_pct': size_pct, 'stop_price': stop_price},
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
