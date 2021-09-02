from django.conf import settings
from django.core.mail import send_mail


class AuthenticationService(object):
    @staticmethod
    def send_verification_email(email, uuid):
        link = f'{settings.ORIGIN_URL}{uuid}/'
        email_from = settings.EMAIL_HOST_USER
        recipient_list = [email, ]
