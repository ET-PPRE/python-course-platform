from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse

from .models import HomepageContent, SiteData


@admin.register(SiteData)
class SiteDataAdmin(admin.ModelAdmin):
    list_display = ("site_name", "site_tagline")

    fieldsets = (
        ("General", {
            "fields": ("site_name", "site_tagline")
        }),
        ("Metadata", {
            "fields": ("name", "email")
        }),
        ("Footer", {
            "fields": ("footer_text", "copyright_text")
        }),
    )

    def has_add_permission(self, request):
        return not SiteData.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SiteData.objects.first()
        if obj:
            return HttpResponseRedirect(
                reverse("admin:site_data_sitedata_change", args=[obj.id])
            )
        return HttpResponseRedirect(reverse("admin:site_data_sitedata_add"))


@admin.register(HomepageContent)
class HomepageContentAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not HomepageContent.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = HomepageContent.objects.first()
        if obj:
            return HttpResponseRedirect(
                reverse("admin:site_data_homepagecontent_change", args=(obj.pk,))
            )
        return super().changelist_view(request, extra_context)
