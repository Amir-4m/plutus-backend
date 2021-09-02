from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings

from apps.authentications.models import EmailVerification
from apps.authentications.tasks import send_email_verification


class LifeTimeTokenSerializer:

    def validate(self, attrs):
        # adding lifetime to data
        data = super().validate(attrs)
        data['lifetime'] = int(api_settings.ACCESS_TOKEN_LIFETIME.total_seconds())
        # data['company'] = self.context
        return data


class LifeTimeTokenObtainSerializer(LifeTimeTokenSerializer, TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super(LifeTimeTokenObtainSerializer, self).validate(attrs)
        return data


class LifeTimeTokenRefreshSerializer(LifeTimeTokenSerializer, TokenRefreshSerializer):
    pass


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField()
    username = serializers.CharField()
    password = serializers.CharField(max_length=100, write_only=True)
    confirm_password = serializers.CharField(max_length=100, write_only=True)

    def validate_password(self, value):
        if value != self.initial_data['confirm_password']:
            raise ValidationError(_('entered passwords are not the same.'))
        password_validation.validate_password(value)
        return value

    def validate_email(self, value):
        if User.objects.filter(email__icontains=value.lower()).exists():
            raise ValidationError(_('this email has been already registered.'))
        return value

    def validate_username(self, value):
        if User.objects.filter(username__icontains=value.lower()).exists():
            raise ValidationError(_('this username has been already registered.'))
        return value

    def create(self, validated_data):
        name = validated_data['first_name']
        sure_name = validated_data['last_name']
        email = validated_data['email'].lower()
        username = validated_data['username'].lower()
        password = validated_data['password']
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=name,
            last_name=sure_name
        )
        verification = EmailVerification.objects.create(user=user, email=user.email)
        send_email_verification.delay(verification.pk)
        return user

    def update(self, instance, validated_data):
        pass
