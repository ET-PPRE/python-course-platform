from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import HomepageContent, SiteData


@receiver(post_migrate)
def create_default_site_data(sender, **kwargs):
    if not SiteData.objects.exists():
        SiteData.objects.create()

    if not HomepageContent.objects.exists():
        HomepageContent.objects.create(
            title="Welcome to the Python Course",
            content="<p>Edit this homepage content using the admin panel.</p>",
            is_active=True
        )