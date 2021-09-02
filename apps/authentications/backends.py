from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .models import EmailVerification

UserModel = get_user_model()


class EmailAuthBackend(ModelBackend):

    def user_can_authenticate(self, user):
        """
        Reject users with is_verified=False and is_active=False.
        """
        is_active = getattr(user, 'is_active', None)
        is_verified = EmailVerification.objects.filter(user=user, email=user.email, is_used=True).exists()

        return is_verified and (is_active or is_active is None)

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get('email')
        if username is None or password is None:
            return
        try:
            user = UserModel.objects.get(email=username.lower())
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).
            UserModel().set_password(password)
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
