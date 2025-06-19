from django.apps import AppConfig


class SiteDataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'site_data'

    def ready(self):
        import site_data.signals