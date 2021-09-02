from django.contrib.auth.models import User
from rest_framework import generics

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    RegisterSerializer, LifeTimeTokenObtainSerializer, LifeTimeTokenRefreshSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = LifeTimeTokenObtainSerializer


class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = LifeTimeTokenRefreshSerializer


class RegisterAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
