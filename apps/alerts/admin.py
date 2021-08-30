from django.contrib import admin
from .models import Platform, StrategyAlert, AlertLog


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ('platform_type', 'is_enable', 'created_time', 'updated_time')


@admin.register(StrategyAlert)
class StrategyAlertAdmin(admin.ModelAdmin):
    list_display = ('user_strategy', 'platform', 'alert_key', 'is_enable', 'created_time', 'updated_time')


@admin.register(AlertLog)
class AlertLogAdmin(admin.ModelAdmin):
    list_display = ('strategy_alert', 'created_time')
