from django.contrib import admin
from django.utils.safestring import mark_safe
from import_export import fields, resources
from import_export.admin import ExportMixin
from import_export.formats.base_formats import CSV, JSON, XLSX

from .models import Submission


class SubmissionResource(resources.ModelResource):
    user = fields.Field(attribute='user', column_name='User')
    assignment = fields.Field(attribute='assignment', column_name='Assignment')
    score = fields.Field(attribute='grade_score', column_name='Score')
    chapter = fields.Field(attribute='assignment.chapter', column_name='Chapter')

    # Define a custom method to display user's first and last name
    def dehydrate_user(self, submission):
        user = submission.user
        if user.first_name or user.last_name:
            return f"{user.first_name} {user.last_name}".strip()
        return user.username  # Fallback to username if no names exist

    def dehydrate_assignment(self, submission):
        assignment = submission.assignment
        if assignment is not None: 
            return assignment.title
        return ''  

    def dehydrate_chapter(self, submission):
        chapter = submission.assignment.chapter
        if chapter is not None: 
            return chapter.title
        return ''  

    class Meta:
        model = Submission
        fields = ('user', 'chapter', 'assignment', 'score')


class SubmissionAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = SubmissionResource
    fields = ("user", "user_first_name", "user_last_name", "assignment", "answer_script_pretty", "result_output", "task_id", "run_status", "grade_score", "grade_total", "updated_at")
    formats = [XLSX, CSV, JSON]
    list_display = ("user__first_name", "user__last_name", "assignment__title", "assignment__chapter", "updated_at", "grade_score", "grade_total", "run_status")
    ordering = ("-updated_at",)
    list_filter = ("user__last_name", "assignment")

    exclude = ("answer_script",)

    # Make all fields read-only
    readonly_fields = ("user", "user_first_name", "user_last_name", "assignment", "answer_script_pretty", "result_output", "task_id", "run_status", "grade_score", "grade_total", "updated_at")

    def answer_script_pretty(self, obj):
        return mark_safe(
            f'<div style="max-height:300px; overflow:auto;"><pre style="white-space:pre;">{obj.answer_script}</pre></div>'
        )
    answer_script_pretty.short_description = "answer_script"   

    def user_first_name(self, obj):
        return obj.user.first_name
    user_first_name.short_description = "First name"

    def user_last_name(self, obj):
        return obj.user.last_name
    user_last_name.short_description = "Last name" 

    # Disable add, change, and delete in admin
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(Submission, SubmissionAdmin)
