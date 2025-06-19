from django.db import models
from tinymce.models import HTMLField


class SiteData(models.Model):
    site_name = models.CharField(max_length=200, default="Python Programming - WiSe 2024-2025")
    site_tagline = models.CharField(max_length=255, blank=True)

    name = models.CharField(max_length=100, blank=True, help_text="Site owner or contact person")
    email = models.EmailField(blank=True, help_text="Contact email address")

    footer_text = models.TextField(blank=True)
    copyright_text = models.CharField(max_length=255, default="© Python-2025")

    def __str__(self):
        return "Site Data"

    class Meta:
        verbose_name = "Site Data"
        verbose_name_plural = "Site Data"

class HomepageContent(models.Model):
    title = models.CharField(max_length=200, default="Homepage Title")
    content = HTMLField()
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.pk and HomepageContent.objects.exists():
            raise Exception("Only one HomepageContent instance is allowed.")
        super().save(*args, **kwargs)

    def __str__(self):
        return "Homepage Content"

    class Meta:
        verbose_name = "Homepage Content"
        verbose_name_plural = "Homepage Content"
