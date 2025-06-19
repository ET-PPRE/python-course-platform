import logging

from allauth.account.signals import (
    email_confirmed,
    password_changed,
    password_reset,
    user_logged_in,
    user_logged_out,
    user_signed_up,
)
from django.dispatch import receiver

logger = logging.getLogger(__name__)

@receiver(user_signed_up)
def log_user_signed_up(request, user, **kwargs):
    logger.info(f"New signup: {user.email} (ID={user.pk})")

@receiver(email_confirmed)
def log_email_confirmed(request, email_address, **kwargs):
    user = email_address.user
    logger.info(f"Email confirmed for {user.email} (ID={user.pk})")

@receiver(user_logged_in)
def log_user_logged_in(request, user, **kwargs):
    logger.info(f"User login: {user.email} (ID={user.pk})")

@receiver(user_logged_out)
def log_user_logged_out(request, user, **kwargs):
    logger.info(f"User logged out: {user.email} (ID={user.pk})")

@receiver(password_reset)
def log_password_reset(request, user, **kwargs):
    logger.info(f"Password reset for user: {user.email} (ID={user.pk})")

@receiver(password_changed)
def log_password_changed(request, user, **kwargs):
    logger.info(f"Password changed for user: {user.email} (ID={user.pk})")