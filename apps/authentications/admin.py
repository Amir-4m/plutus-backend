from django.contrib import admin
from .models import EmailVerification


@admin.register(EmailVerification)
class VerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'is_used', 'created_time', 'updated_time')
    search_fields = ('email', 'user__username')
    list_filter = ('is_used',)
