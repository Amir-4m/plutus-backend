from django.contrib import admin

from apps.trader_bots.models import TraderBot


@admin.register(TraderBot)
class TraderBotAdmin(admin.ModelAdmin):
    list_display = ('exchange', 'user')
