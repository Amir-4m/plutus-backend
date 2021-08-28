from django.contrib import admin

from apps.assets.models import Asset


@admin.register(Asset)
class FuturesOrderAdmin(admin.ModelAdmin):
    list_display = ('code_name', 'exchange')
