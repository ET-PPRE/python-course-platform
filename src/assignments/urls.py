from django.urls import path
from . import views

app_name = 'assignments'

urlpatterns = [
    path('', views.chapter_list, name='chapter-list'),

    # NEW route for the page that lists all assignments in a chapter
    path(
        '<slug:chapter_slug>/assignments/',
        views.chapter_assignments,
        name='chapter-assignments'
    ),

    path(
        '<slug:chapter_slug>/<slug:assignment_slug>/',
        views.assignment_detail,
        name='assignment-detail'
    ),
]
