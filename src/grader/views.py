from celery.result import AsyncResult
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Submission


def _coalesce_payload(result_obj):
    """Return a normalized dict no matter what the Celery result shape is."""
    if isinstance(result_obj, dict):
        return result_obj
    return {}


@login_required
def submission_status(request, submission_id):
    sub = get_object_or_404(Submission, pk=submission_id, user=request.user)

    assignment = sub.assignment
    show_output = True
    deadline_passed = False

    if assignment.is_exam and assignment.publish_result_at:
        show_output = timezone.now() >= assignment.publish_result_at
    
    if assignment.is_exam and assignment.publish_until:
        deadline_passed = timezone.now() >= assignment.publish_until

    context = {
        "state": "NONE",
        "status": sub.run_status,
        # Phase A (student program output)
        "user_stdout": "",
        "user_stderr": "",
        "user_exit_code": None,
        # Phase B (grading output)
        "grade_pct": None,
        "score": None,
        "total": None,
        "test_output": "",
        "test_errors": [],
        "show_output": show_output,
        "deadline_passed": deadline_passed,
        "is_exam": assignment.is_exam,
        "result_output": sub.result_output,
        "publish_result_at": assignment.publish_result_at,
    }

    context["test_output"] = sub.result_output or context.get("test_output", "")
    context["grade_pct"] = sub.grade_score and sub.grade_total and round(100.0 * sub.grade_score / sub.grade_total, 2) or context.get("grade_pct", None)
    context["score"] = sub.grade_score if sub.grade_score is not None else context.get("score", None)
    context["total"] = sub.grade_total if sub.grade_total is not None else context.get("total", None)

    if not sub.task_id:
        return render(request, "grader/_run_result.html", context)

    res = AsyncResult(sub.task_id)
    state = res.state
    context["state"] = state

    # Pending / running
    if state in ("PENDING", "RETRY", "STARTED") and sub.run_status != "success":
        if sub.run_status != "pending":
            Submission.objects.filter(pk=sub.pk).update(run_status="pending")
        context["status"] = "pending"
        return render(request, "grader/_run_result.html", context)

    # Failure
    if state == "FAILURE":
        context["status"] = "error"
        info = _coalesce_payload(res.info)
        user = info.get("user", {})
        grading = info.get("grading", {})

        context["user_stdout"] = user.get("stdout", info.get("stdout", ""))
        context["user_stderr"] = user.get("stderr", info.get("stderr", str(res.info)))
        context["user_exit_code"] = user.get("exit_code")

        score = grading.get("score")
        total = grading.get("total")

        context["grade_pct"] = grading.get("grade_pct")
        context["score"] = score
        context["total"] = total
        context["test_output"] = grading.get("output", "")
        context["test_errors"] = grading.get("errors", [])

        updates = {
            "run_status": "error",
            "test_output": context["test_output"],
        }

        if score is not None:
            updates["grade_score"] = score

        if total is not None:
            updates["grade_total"] = total

        Submission.objects.filter(pk=sub.pk).update(**updates)
        
        return render(request, "grader/_run_result.html", context, status=286)

    # Success
    if state == "SUCCESS":
        payload = _coalesce_payload(res.result) or _coalesce_payload(res.info)

        user = payload.get("user", {})
        grading = payload.get("grading", {})

        context["status"] = payload.get("status", "success")

        context["user_stdout"] = user.get("stdout", payload.get("stdout", ""))
        context["user_stderr"] = user.get("stderr", payload.get("stderr", ""))
        context["user_exit_code"] = user.get("exit_code")

        score = grading.get("score")
        total = grading.get("total")

        context["grade_pct"] = grading.get("grade_pct")
        context["score"] = score
        context["total"] = total
        context["test_output"] = grading.get("output", "")
        context["test_errors"] = grading.get("errors", [])
        context["images"] = payload.get("images", [])

        updates = {
            "run_status": "success",
            "result_output": context["test_output"],
        }
        
        if score is not None:
            updates["grade_score"] = score

        if total is not None:
            updates["grade_total"] = total

        if updates:
            Submission.objects.filter(pk=sub.pk).update(**updates)

        return render(request, "grader/_run_result.html", context, status=286)

    # Fallback
    return render(request, "grader/_run_result.html", context)
