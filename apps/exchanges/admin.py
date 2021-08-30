from django.contrib import admin

from apps.exchanges.models import Asset, Exchange


class InlineAsset(admin.TabularInline):
    model = Exchange.futures_assets.through
    raw_id_fields = ['asset']
    extra = 0


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'created_time', 'updated_time')


@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_enable', 'created_time', 'updated_time')
    inlines = [
        InlineAsset
    ]
