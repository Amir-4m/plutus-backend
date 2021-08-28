from django.urls import path
from .views import WebHookView

app_name = "trader_bots"

urlpatterns = [
    path('webhook', WebHookView.as_view(), name='webhook'),

]
