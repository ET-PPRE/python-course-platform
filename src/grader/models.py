from django.conf import settings
from django.db import models

from assignments.models import Assignment


class Submission(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    answer_script    = models.TextField(help_text="The user’s submitted solution")
    result_output = models.TextField(blank=True, null=True, help_text="Full test runner output")
    task_id = models.CharField(max_length=255, blank=True, null=True)
    run_status = models.CharField(
        max_length=20,
        choices=[("pending","pending"),("success","success"),("error","error")],
        default="pending",
    )

    grade_score = models.FloatField(blank=True, null=True)
    grade_total = models.FloatField(blank=True, null=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("user", "assignment"),)
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.username} → {self.assignment} @ {self.updated_at:%Y-%m-%d %H:%M}"
