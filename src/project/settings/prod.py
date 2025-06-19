from pathlib import Path
import os

from .base import *

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE':   os.getenv('DB_ENGINE',   'django.db.backends.postgresql'),
        'NAME':     os.getenv('DB_NAME'),
        'USER':     os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST':     os.getenv('DB_HOST',     'localhost'),
        'PORT':     os.getenv('DB_PORT',     '5432'),
    }
}

if 'test' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': os.getenv('TEST_DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME':   os.getenv('TEST_DB_NAME',   ':memory:'),
    }

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND')
if 'test' in sys.argv:
    EMAIL_BACKEND = os.getenv('TEST_EMAIL_BACKEND',
                              'django.core.mail.backends.locmem.EmailBackend')

if EMAIL_BACKEND != 'django.core.mail.backends.locmem.EmailBackend':
    EMAIL_HOST = os.getenv('EMAIL_HOST')
    EMAIL_PORT = os.getenv('EMAIL_PORT', 587)
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL')

# override log directory for production container
LOG_DIR = Path(os.environ.get("DJANGO_LOG_DIR", "/tmp/logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

# override logging file handler path
LOGGING['handlers']['file']['filename'] = LOG_DIR / 'allauth.log'