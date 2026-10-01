import json
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase

from apps.exchanges.models import Asset, Exchange, ExchangeFuturesAsset
from apps.trader_bots.models import TraderBot
from apps.trader_bots.services import KucoinFuturesService, TraderBotService
from apps.trader_bots.tasks import create_order_task

CONTRACT = {'multiplier': 0.001, 'lotSize': 1, 'tickSize': 0.1, 'settleCurrency': 'USDT', 'isInverse': False}


def _response(payload):
    return mock.Mock(json=mock.Mock(return_value=payload), raise_for_status=mock.Mock())


class KucoinFuturesServiceTests(TestCase):
    def setUp(self):
        self.service = KucoinFuturesService('key', 'secret', 'pass')
        self.asset = SimpleNamespace(code_name='XBTUSDTM')

    def test_calculate_order_size_from_equity(self):
        with mock.patch.object(self.service, 'get_contract', return_value=CONTRACT), \
                mock.patch.object(self.service, 'get_account_futures',
                                  return_value={'data': {'accountEquity': 10000}}):
            # 10000 * 20% = 2000 USDT / (60000 * 0.001) = 33.3 -> 33 contracts
            self.assertEqual(self.service.calculate_order_size('XBTUSDTM', 20, 60000), Decimal('33'))
            # 10000 * 0.5% = 50 USDT -> below one contract
            self.assertEqual(self.service.calculate_order_size('XBTUSDTM', 0.5, 60000), Decimal('0'))

    def test_calculate_order_size_inverse_contract_returns_none(self):
        with mock.patch.object(self.service, 'get_contract', return_value={**CONTRACT, 'isInverse': True}):
            self.assertIsNone(self.service.calculate_order_size('XBTUSDM', 20, 60000))

    @mock.patch('apps.trader_bots.services.requests.post')
    def test_place_stop_loss_for_long_rounds_down(self, post):
        post.return_value = _response({'code': '200000'})
        with mock.patch.object(self.service, 'get_contract', return_value=CONTRACT):
            self.service.place_stop_loss(self.asset, 'buy', 58123.456)
        body = json.loads(post.call_args.kwargs['data'])
        self.assertEqual(body['side'], 'sell')
        self.assertEqual(body['stop'], 'down')
        self.assertEqual(body['stopPrice'], '58123.4')
        self.assertTrue(body['closeOrder'])

    @mock.patch('apps.trader_bots.services.requests.post')
    def test_place_stop_loss_for_short_rounds_up(self, post):
        post.return_value = _response({'code': '200000'})
        with mock.patch.object(self.service, 'get_contract', return_value=CONTRACT):
            self.service.place_stop_loss(self.asset, 'sell', 61000.01)
        body = json.loads(post.call_args.kwargs['data'])
        self.assertEqual(body['side'], 'buy')
        self.assertEqual(body['stop'], 'up')
        self.assertEqual(body['stopPrice'], '61000.1')

    def test_close_position_cancels_stop_orders_even_when_flat(self):
        with mock.patch.object(self.service, 'get_position', return_value={'data': {'currentQty': 0}}), \
                mock.patch.object(self.service, 'cancel_stop_orders') as cancel:
            self.service.close_position(self.asset, None, None, 60000)
        cancel.assert_called_once_with('XBTUSDTM')

    def test_reduce_position_without_position_is_noop(self):
        with mock.patch.object(self.service, 'get_position', return_value={'data': []}), \
                mock.patch.object(self.service, 'create_order') as create:
            self.service.reduce_position(self.asset, 50, 'sell', 1, None, None, 60000)
        create.assert_not_called()


class CreateOrderTaskTests(TestCase):
    def setUp(self):
        user = User.objects.create(username='u', email='u@example.com')
        exchange = Exchange.objects.create(title='kucoin')
        asset = Asset.objects.create(symbol='BTC')
        ExchangeFuturesAsset.objects.create(exchange=exchange, asset=asset, code_name='XBTUSDTM')
        self.bot = TraderBot.objects.create(user=user, exchange=exchange, credential_data={
            'api_key': 'k', 'api_secret': 's', 'api_passphrase': 'p'})

    @mock.patch.object(KucoinFuturesService, 'place_stop_loss')
    @mock.patch.object(KucoinFuturesService, 'cancel_stop_orders')
    @mock.patch.object(KucoinFuturesService, 'create_order')
    @mock.patch.object(KucoinFuturesService, 'calculate_order_size', return_value=Decimal('33'))
    def test_uses_equity_size_and_places_stop(self, size, create, cancel, stop):
        create.return_value = SimpleNamespace(order_id='abc')
        create_order_task(self.bot.id, 'XBTUSDTM', 1, 'buy', 1, 60000, size_pct=20, stop_price=58000)
        self.assertEqual(create.call_args.args[1], Decimal('33'))
        cancel.assert_called_once_with('XBTUSDTM')
        self.assertEqual(stop.call_args.args[1:], ('buy', 58000))

    @mock.patch.object(KucoinFuturesService, 'create_order')
    @mock.patch.object(KucoinFuturesService, 'calculate_order_size', return_value=Decimal('0'))
    def test_skips_order_below_one_lot(self, size, create):
        create_order_task(self.bot.id, 'XBTUSDTM', 1, 'buy', 1, 60000, size_pct=0.1)
        create.assert_not_called()

    @mock.patch.object(KucoinFuturesService, 'place_stop_loss')
    @mock.patch.object(KucoinFuturesService, 'create_order')
    @mock.patch.object(KucoinFuturesService, 'calculate_order_size')
    def test_without_size_pct_uses_fixed_contracts(self, size, create, stop):
        create.return_value = SimpleNamespace(order_id='abc')
        create_order_task(self.bot.id, 'XBTUSDTM', 3, 'buy', 1, 60000)
        size.assert_not_called()
        stop.assert_not_called()
        self.assertEqual(create.call_args.args[1], 3)


class TradeOnStrategyTests(TestCase):
    @mock.patch('apps.trader_bots.tasks.create_order_task.apply_async')
    def test_drops_stop_on_wrong_side(self, apply_async):
        user_strategy = SimpleNamespace(trader_bot=SimpleNamespace(id=1), contracts=1, leverage=1)
        TraderBotService.trade_on_strategy([user_strategy], 'buy', 'XBTUSDTM', 'open', 60000,
                                           size_pct=10, stop_price=61000)
        self.assertIsNone(apply_async.call_args.kwargs['kwargs']['stop_price'])
        TraderBotService.trade_on_strategy([user_strategy], 'sell', 'XBTUSDTM', 'open', 60000,
                                           size_pct=10, stop_price=61000)
        self.assertEqual(apply_async.call_args.kwargs['kwargs']['stop_price'], 61000)
