from django.contrib import admin

from .models import Strategy, UserStrategy


@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'is_enable', 'created_time', 'updated_time')


@admin.register(UserStrategy)
class UserStrategyAdmin(admin.ModelAdmin):
    list_display = ('user', 'strategy', 'trade', 'due_date', 'leverage', 'contracts', 'is_enable')
