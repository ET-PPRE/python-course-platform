from .base import *

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv(
            'DB_NAME'
        ),
    }
}

if 'test' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': os.getenv('TEST_DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME':   os.getenv('TEST_DB_NAME',   ':memory:'),
    }

EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'
)

if 'test' in sys.argv:
    EMAIL_BACKEND = os.getenv('TEST_EMAIL_BACKEND',
                              'django.core.mail.backends.locmem.EmailBackend')