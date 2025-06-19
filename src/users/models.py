from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from users.managers import UserProfileManager


class UserProfile(AbstractUser):
    username = None  # REMOVE username field
    email = models.EmailField(_("email address"), max_length=255, unique=True)

    objects = UserProfileManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
