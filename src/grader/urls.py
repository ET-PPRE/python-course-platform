from django.urls import path
from .views import submission_status

app_name = 'grader'

urlpatterns = [
    path(
      "submissions/<int:submission_id>/status/",
      submission_status,
      name="submission-status",
    ),
]