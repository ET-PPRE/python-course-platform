# settings/celery_settings.py

# Where your Celery workers connect for tasks (the broker)
CELERY_BROKER_URL = "redis://redis:6379/0"

# Where Celery stores task results (can use same as broker, or another Redis DB)
CELERY_RESULT_BACKEND = "redis://redis:6379/1"

# Recommended serialization options (safe for most cases)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Set to your local time zone, or leave as UTC
CELERY_TIMEZONE = "Europe/Berlin"
