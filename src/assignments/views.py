from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from grader.forms import SubmissionForm
from grader.models import Submission
from grader.tasks import run_user_code

from .models import Assignment, Chapter

# Passing threshold for a "completed" assignment (percent)
PASSING_THRESHOLD = 80


def chapter_list(request):
    """
    Lists all chapters that have at least one published assignment. 
    Progress per chapter is computed from the user's latest
    submission per assignment: score >= PASSING_THRESHOLD => "passed".
    If no score is available, we fall back to any `assignment.completion` value.
    """
    query = (request.GET.get("q") or "").strip()

    # Only include chapters that have at least one published assignment
    chapters = (
        Chapter.objects.prefetch_related("assignments")
        .filter(assignments__publish_at__isnull=False, assignments__publish_at__lte=timezone.now(), status="active")
#        .filter(Q(assignments__publish_until__isnull=True) | Q(assignments__publish_until__gte=timezone.now()))
        .distinct().order_by("order")
    )

    # Apply per-chapter assignment filtering for the UI
    for chapter in chapters:
        published_qs = chapter.assignments.filter(
            publish_at__isnull=False,
            publish_at__lte=timezone.now(),
            status="active"
        )
        # .filter(
        #     Q(publish_until__isnull=True) |
        #     Q(publish_until__gte=timezone.now())
        # )
        if query:
            chapter.assignments_filtered = published_qs.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        else:
            chapter.assignments_filtered = published_qs
        
        # Determine exam and public result flags
        exams_qs = published_qs.filter(is_exam=True)
        chapter.has_exam = exams_qs.exists()
        chapter.has_unpublished_results = exams_qs.filter(
            publish_result_at__isnull=False, publish_result_at__gte=timezone.now()
        ).exists()
        chapter.published_qs = published_qs

    chapters = [ch for ch in chapters if ch.assignments_filtered.exists()]
    # Build chapter progress
    chapter_progress = {}

    # Collect all assignment ids across these chapters
    all_assignment_ids = []
    for ch in chapters:
        all_assignment_ids.extend(a.id for a in ch.assignments.all())

    latest_by_assignment = {}
    if request.user.is_authenticated and all_assignment_ids:
        # newest first; keep first seen per assignment_id
        subs = (
            Submission.objects.filter(
                user=request.user, assignment_id__in=all_assignment_ids
            )
            .order_by("-id")
            .values("assignment_id", "grade_score", "grade_total")
        )
        for s in subs:
            aid = s["assignment_id"]
            if aid not in latest_by_assignment:
                latest_by_assignment[aid] = s

    for ch in chapters:
        assigns = list(ch.published_qs)
        total = len(assigns)
        passed = 0
        points_achieved = 0
        points_available = 0

        for a in assigns:
            sub = latest_by_assignment.get(a.id)
            score = grade_total = 0
            if sub and sub.get("grade_total"):
                try:
                    pct = 100.0 * (
                        float(sub["grade_score"]) / float(sub["grade_total"])
                    )
                    score = float(sub["grade_score"] or 0)
                    grade_total = float(sub["grade_total"] or 0)
                except Exception:
                    pct = 0.0
                    score = grade_total = 0
            else:
                # fallback to any assignment-level completion field (0..100)
                pct = float(getattr(a, "completion", 0) or 0)

            if pct >= PASSING_THRESHOLD:
                passed += 1

            # Accumulate totals
            points_achieved += score
            points_available += grade_total
        
        pct_ch = int(round((passed / total) * 100)) if total else 0

        # Use pk (works even if the primary key is not named "id")
        chapter_progress[ch.pk] = {
            "pct": pct_ch, 
            "passed": passed, 
            "total": total,
            "points_achieved": points_achieved,
            "points_available": points_available,
            }

        # Also set attributes so existing templates (chapter.progress) keep working
        ch.progress = pct_ch
        ch.passed_count = passed
        ch.total_count = total
        ch.points_achieved = points_achieved
        ch.points_available = points_available

    return render(
        request,
        "assignments/chapter_list.html",
        {
            "chapters": chapters,
            "query": query,
            "chapter_progress": chapter_progress,
            "passing_threshold": PASSING_THRESHOLD,
        },
    )


@login_required
def assignment_detail(request, chapter_slug, assignment_slug):
    assignment = get_object_or_404(
        Assignment, 
        chapter__slug=chapter_slug, 
        slug=assignment_slug, 
        publish_at__isnull=False, 
        publish_at__lte=timezone.now(), 
        status="active"
    )
    # if assignment.publish_until and assignment.publish_until < timezone.now():
    #     raise Http404("This assignment is no longer available.")

    # Ordered assignments in this chapter
    assignments = Assignment.objects.filter(
        chapter=assignment.chapter, 
        publish_at__isnull=False, 
        publish_at__lte=timezone.now(), 
        status="active"
    ).order_by("order", "id")

    # .filter(
    #     Q(publish_until__isnull=True) |
    #     Q(publish_until__gte=timezone.now())
    # )

    submission_open = (
        assignment.publish_until is None or
        assignment.publish_until >= timezone.now()
    )

    assignments_list = list(assignments)
    current_index = assignments_list.index(assignment)

    prev_assignment = assignments_list[current_index - 1] if current_index > 0 else None
    next_assignment = (
        assignments_list[current_index + 1]
        if current_index < len(assignments_list) - 1
        else None
    )

    assignment_number = assignment.order or (current_index + 1)

    submission = (
        Submission.objects.filter(user=request.user, assignment=assignment)
        .order_by("-id")
        .first()
    )

    if request.method == "POST":
        if not submission_open:
            messages.error(request, "⏰ The submission period has ended.")
            return redirect(
                "assignments:assignment-detail",
                chapter_slug=chapter_slug,
                assignment_slug=assignment_slug,
            )
        form = (
            SubmissionForm(request.POST, instance=submission)
            if submission
            else SubmissionForm(request.POST)
        )
        if form.is_valid():
            new_sub = form.save(commit=False)
            new_sub.user = request.user
            new_sub.assignment = assignment
            new_sub.run_status = "pending"
            new_sub.save()

            def _enqueue():
                async_result = run_user_code.delay(
                    new_sub.id,
                    code=new_sub.answer_script,
                    test_runner=assignment.test_runner or "",
                )
                Submission.objects.filter(pk=new_sub.id).update(
                    task_id=async_result.id
                )
                new_sub.save(update_fields=["run_status"])

            transaction.on_commit(_enqueue)

            return redirect(
                "assignments:assignment-detail",
                chapter_slug=chapter_slug,
                assignment_slug=assignment_slug,
            )
    else:
        form = SubmissionForm(instance=submission)

    return render(
        request,
        "assignments/assignment_detail.html",
        {
            "assignment": assignment,
            "form": form,
            "prev_assignment": prev_assignment,
            "next_assignment": next_assignment,
            "assignment_number": assignment_number,
            "submission": submission,
            "submission_open": submission_open,
            "publish_until": assignment.publish_until,
            "score": submission.grade_score if submission else None,
            "total": submission.grade_total if submission else assignment.points,
            "is_exam": assignment.is_exam,
        },
    )


def chapter_assignments(request, chapter_slug):
    """
    Page that lists all assignments for a single chapter.
    Supports optional ?q= filtering (title/description).
    """
    user = request.user
    query = (request.GET.get("q") or "").strip()
    chapter = get_object_or_404(Chapter, slug=chapter_slug)

    assignments_qs = chapter.assignments.filter(
        publish_at__isnull=False,
        publish_at__lte=timezone.now(),
        status="active"
    ).order_by("order", "id")

    # .filter(
    #     Q(publish_until__isnull=True) |
    #     Q(publish_until__gte=timezone.now())
    # )
    # Indicate if chapter has any exam assignments
    chapter.has_exam = assignments_qs.filter(is_exam=True).exists()

    if query:
        assignments_qs = assignments_qs.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    # Determine for each assignment whether results are public
    now = timezone.now()
    for assignment in assignments_qs:
        if assignment.is_exam and assignment.publish_result_at:
            assignment.show_output = now >= assignment.publish_result_at
        else:
            assignment.show_output = not assignment.is_exam  # Always visible for regular assignments

    # Latest score per assignment for current user
    user_scores = {}
    if user.is_authenticated:
        subs = (
            Submission.objects.filter(user=user, assignment__in=assignments_qs)
            .order_by("-id")
            .values("assignment_id", "grade_score", "grade_total")
        )
        for s in subs:
            aid = s["assignment_id"]
            if aid not in user_scores:
                user_scores[aid] = {
                    "grade_score": s["grade_score"],
                    "grade_total": s["grade_total"],
                }

    return render(
        request,
        "assignments/chapter_assignments.html",
        {
            "chapter": chapter,
            "assignments": assignments_qs,
            "query": query,
            "user_scores": user_scores,
        },
    )
