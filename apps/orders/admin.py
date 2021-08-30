from django.contrib import admin

from apps.orders.models import FuturesOrder


@admin.register(FuturesOrder)
class FuturesOrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'exchange_futures_asset', 'is_active')
