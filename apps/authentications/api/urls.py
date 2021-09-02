from django.urls import path

from .views import (
    RegisterAPIView, CustomTokenObtainPairView, CustomTokenRefreshView,
)

urlpatterns = [
    path('token/', CustomTokenObtainPairView.as_view(), name="token"),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name="token_refresh"),
    path('register/', RegisterAPIView.as_view(), name="register"),
]
