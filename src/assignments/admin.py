from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import Assignment, Chapter


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title","chapter","publish_at","publish_until","status","is_exam")

    # Order assignments by chapter order then assignment order
    ordering = ("chapter__order", "order")

    exclude = ("test_runner","description","solution")

    # Make all fields read-only
    readonly_fields = ("chapter", "slug", "title", "description_pretty", "test_runner_pretty", "solution_pretty", 
    "points", "difficulty", "publish_at", "publish_until","is_exam","publish_result_at","order", "status","last_synced")
    list_filter = ("title", "chapter")

    def description_pretty(self, obj):
        return mark_safe(
            f'<div style="max-height:300px; overflow:auto;">{ obj.description }</div>'
        )
    description_pretty.short_description = "Description"

    def test_runner_pretty(self, obj):
        return mark_safe(
        f'<div style="max-height:300px; overflow:auto;"><pre style="white-space:pre;">{obj.test_runner}</pre></div>'
        )
    test_runner_pretty.short_description = "Test Runner"

    def solution_pretty(self, obj):
        return mark_safe(
        f'<div style="max-height:300px; overflow:auto;"><pre style="white-space:pre;">{obj.solution}</pre></div>'
        )
    solution_pretty.short_description = "Solution"

    # Disable add, change, and delete in admin
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("slug","title","order","status")

    # Order chapters by the 'order' field
    ordering = ("order",)

    # Make all fields read-only
    readonly_fields = ("slug", "title", "order", "book_url", "status")

    # # Disable add, change, and delete in admin
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False