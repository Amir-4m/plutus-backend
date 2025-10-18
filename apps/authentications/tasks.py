import logging

from .models import EmailVerification
from .services import AuthenticationService

logger = logging.getLogger(__name__)


def send_email_verification(verification_pk):
    """
    sends email verification link to user
    :param verification_pk: EmailVerification object primary key
    """
    try:
        obj = EmailVerification.objects.get(pk=verification_pk)
        AuthenticationService.send_verification_email(obj.email, verification_pk)
    except EmailVerification.DoesNotExist:
        logger.error(f'sending email verification failed due to: EmailVerification with pk {verification_pk} does not exists!')
    except Exception as e:
        logger.error(f'sending email verification failed due to: {e}')
