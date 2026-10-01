import json
from unittest import mock

from django.test import TestCase, override_settings

from apps.exchanges.models import Asset, Exchange, ExchangeFuturesAsset
from apps.strategies.models import Strategy


@override_settings(STRATEGY_WEBHOOK_SECRET='s3cret')
class WebHookViewTests(TestCase):
    def setUp(self):
        asset = Asset.objects.create(symbol='BTC')
        exchange = Exchange.objects.create(title='kucoin')
        ExchangeFuturesAsset.objects.create(exchange=exchange, asset=asset, code_name='XBTUSDTM')
        Strategy.objects.create(title='TOP1', price=0, asset=asset)

    def _post(self, **overrides):
        payload = {
            'strategy': 'TOP1', 'symbol': 'BTC', 'exchange': 'kucoin',
            'side': 'buy', 'action': 'open', 'price': 60000, 'ID': 'x', 'secret': 's3cret',
        }
        payload.update(overrides)
        return self.client.post('/strategies/webhook', data=json.dumps(payload), content_type='application/json')

    @mock.patch('apps.strategies.views.TraderBotService.trade_on_strategy')
    def test_rejects_wrong_or_missing_secret(self, trade):
        self.assertEqual(self._post(secret='nope').status_code, 403)
        self.assertEqual(self._post(secret=None).status_code, 403)
        trade.assert_not_called()

    def test_rejects_invalid_json(self):
        response = self.client.post('/strategies/webhook', data='{"price": {{strategy.order.price}}}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 400)

    @mock.patch('apps.strategies.views.TraderBotService.trade_on_strategy')
    def test_passes_size_pct_and_stop(self, trade):
        response = self._post(size_pct=12.5, stop=58000)
        self.assertEqual(response.status_code, 200)
        _, kwargs = trade.call_args
        self.assertEqual(kwargs['size_pct'], 12.5)
        self.assertEqual(kwargs['stop_price'], 58000.0)

    @mock.patch('apps.strategies.views.TraderBotService.trade_on_strategy')
    def test_size_pct_and_stop_are_optional(self, trade):
        self._post(side='sell', action='close')
        _, kwargs = trade.call_args
        self.assertIsNone(kwargs['size_pct'])
        self.assertIsNone(kwargs['stop_price'])
