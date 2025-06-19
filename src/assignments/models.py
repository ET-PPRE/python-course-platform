from django.db import models
from django.utils import timezone


class Chapter(models.Model):
    slug  = models.SlugField(max_length=30,primary_key=True)        # intro_to_python
    title = models.CharField(max_length=200)                        # Intro to Python
    order = models.PositiveIntegerField(default=0, db_index=True)   # sort order
    book_url = models.URLField(blank=True, null=True)               # intro_to_python/intro_to_python.html
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("deleted", "Deleted")],
        default="active",
    )

    def __str__(self):
        return self.title

class Assignment(models.Model):
    chapter     = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    slug        = models.SlugField(max_length=30)                               # “assignment-01”
    title       = models.CharField(max_length=200)                              # from front-matter or filename
    description = models.TextField()                                            # holds the rendered Markdown
    test_runner = models.TextField(blank=True)
    solution    = models.TextField(blank=True)
    order       = models.PositiveIntegerField(default=0, db_index=True)         # to order within a chapter
    points      = models.FloatField(default=0)
    difficulty  = models.CharField(
        max_length=20,
        choices=[("Easy", "Easy"), ("Intermediate", "Intermediate"), ("Hard", "Hard")],
        default="Easy",
    )
    publish_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Users can see this assignment only after this time"
    )
    publish_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Users cannot see this assignment after this time"
    )
    publish_result_at = models.DateTimeField(null=True, blank=True, help_text="When to show test results")
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("deleted", "Deleted")],
        default="active",
    )
    is_exam = models.BooleanField(default=False)
    last_synced = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = (("chapter", "slug"),)        # each slug is unique per chapter
        ordering        = ["chapter__order", "order"]   # default sort

    def __str__(self):
        # shows “intro_to_python/assignment-01”
        return f"{self.chapter.slug}/{self.slug}"

    @property
    def is_published(self):
        return self.publish_at and self.publish_at <= timezone.now()