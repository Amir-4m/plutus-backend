from django.contrib import admin

from .models import TelegramUser


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'username', 'user_id', 'is_enable', 'created_time', 'updated_time')
