import json
from unittest import mock

from django.test import TestCase, override_settings

from apps.exchanges.models import Asset, Exchange, ExchangeFuturesAsset
from apps.strategies import views
from apps.strategies.models import Strategy

_run_in_background = views._run_in_background


@override_settings(STRATEGY_WEBHOOK_SECRET='s3cret')
@mock.patch('apps.strategies.views._run_in_background', side_effect=views._handle_webhook)
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
    def test_rejects_wrong_or_missing_secret(self, trade, background):
        self.assertEqual(self._post(secret='nope').status_code, 403)
        self.assertEqual(self._post(secret=None).status_code, 403)
        trade.assert_not_called()

    @mock.patch('apps.strategies.views.TraderBotService.trade_on_strategy')
    def test_secret_is_not_logged(self, trade, background):
        with self.assertLogs('apps.strategies.views', level='INFO') as logs:
            self._post()
            self.client.post('/strategies/webhook', data='{"secret": "s3cret", "price": {{x}}}',
                             content_type='application/json')
        output = '\n'.join(logs.output)
        self.assertNotIn('s3cret', output)
        self.assertIn('"secret": "***"', output)

    def test_rejects_invalid_json(self, background):
        response = self.client.post('/strategies/webhook', data='{"price": {{strategy.order.price}}}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 400)

    @mock.patch('apps.strategies.views.TraderBotService.trade_on_strategy')
    def test_passes_size_pct_and_stop(self, trade, background):
        response = self._post(size_pct=12.5, stop=58000)
        self.assertEqual(response.status_code, 200)
        _, kwargs = trade.call_args
        self.assertEqual(kwargs['size_pct'], 12.5)
        self.assertEqual(kwargs['stop_price'], 58000.0)

    @mock.patch('apps.strategies.views.TraderBotService.trade_on_strategy')
    def test_size_pct_and_stop_are_optional(self, trade, background):
        self._post(side='sell', action='close')
        _, kwargs = trade.call_args
        self.assertIsNone(kwargs['size_pct'])
        self.assertIsNone(kwargs['stop_price'])

    @mock.patch('apps.strategies.views.TraderBotService.trade_on_strategy')
    @mock.patch('apps.strategies.views.threading.Thread')
    def test_responds_before_processing(self, thread, trade, background):
        background.side_effect = _run_in_background
        response = self._post()
        self.assertEqual(response.status_code, 200)
        thread.assert_called_once_with(target=views._process_webhook, args=(mock.ANY,), name='strategy-webhook')
        thread.return_value.start.assert_called_once()
        trade.assert_not_called()
