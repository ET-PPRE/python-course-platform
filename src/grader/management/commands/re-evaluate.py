import os
from pathlib import Path

from django.core.management.base import BaseCommand

from grader.models import Submission
from grader.tasks import run_user_code


class Command(BaseCommand):
    help = "Re-run autograder for selected submissions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--assignment",
            type=int,
            help="Only re-evaluate submissions for a specific assignment ID.",
        )
        parser.add_argument(
            "--user",
            type=int,
            help="Only re-evaluate submissions for a specific user ID.",
        )
    def handle(self, *args, **options):
        assignment_id = options.get("assignment")
        user_id = options.get("user")

        qs = Submission.objects.all()
        if assignment_id:
            qs = qs.filter(assignment_id=assignment_id)
        if user_id:
            qs = qs.filter(user_id=user_id)
        
        for sub in qs:
            code = sub.answer_script
            assignment_dir = Path(os.environ.get("LOCAL_PATH", "/app/python_course_repo"))
            print("Assignment:", sub.assignment.slug)
            print(f"Sub ID: {sub.id}")

            test_file = assignment_dir / sub.assignment.chapter.slug / sub.assignment.slug / "test_runner.py"
            try:
                test_runner = test_file.read_text(encoding="utf-8")
            except Exception as e:
                print(e)
                test_runner = ""
            
            res = run_user_code.delay(sub.id, code, test_runner).get()
            sub.grade_score = res["grading"]["score"]
            print("Score:", sub.grade_score)
            sub.grade_total = res["grading"]["total"]
            print("Total:", sub.grade_total)
            sub.result_output = res["grading"]["output"]
            print("Output:", sub.result_output)

            sub.save()

        print(self.style.SUCCESS("Done."))
