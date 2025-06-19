import os
import subprocess

import yaml
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from git import Repo
from path import Path

from .models import Assignment, Chapter

REPO_URL   = os.environ["REPO_URL"]

BRANCH     = os.environ.get("REPO_BRANCH")

TOC_FILE_NAME     = os.environ.get("TOC_FILE_NAME")

LOCAL_PATH = Path(settings.PYTHON_COURSE_REPO)                # "/app/python_course_repo"

toc_target = os.getenv("TOC_BOOK_BUILD", "build-main")

# print(f"DEBUG: LOCAL repo path is → {LOCAL_PATH}")

TOC_PATH   = LOCAL_PATH / TOC_FILE_NAME

def clone_or_pull_repo():

    if not LOCAL_PATH.exists():                                 # If not create one.
        LOCAL_PATH.makedirs()

    git_dir = LOCAL_PATH / ".git"                           # Build the filesystem path to the .git metadata folder inside your cloned repository. Decision factor for clone/pull

    if git_dir.is_dir():                          # already cloned → pull latest. This is done by seeing the .git file in the cloned folder
        repo = Repo(str(LOCAL_PATH))
        origin = repo.remotes.origin
        origin.fetch()
        # Reset local branch to match the remote exactly
        repo.git.reset("--hard", f"origin/{BRANCH}")

    else:                                               # fresh clone if the .git file is not there
        Repo.clone_from(REPO_URL, str(LOCAL_PATH), branch = BRANCH)


@shared_task
def sync_assignments_repo():

    clone_or_pull_repo()

    # Path to theory book folder
    book_dir = LOCAL_PATH / "book"

    # Build the JupyterBook if folder exists
    if book_dir.is_dir():
        print("JupyterBook build started")
        result = subprocess.run(
            ["make", toc_target],
            cwd=book_dir,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("JupyterBook build successful")
        else:
            print("JupyterBook build failed")
            print("STDOUT:\n", result.stdout)
            print("STDERR:\n", result.stderr)
    
    # Read TOC file and copy its content to models
    toc = yaml.safe_load((TOC_PATH).open(encoding="utf-8"))

    repo_chapters = set()
    repo_assignments = set()

    for chap in toc.get("chapters", []):

        repo_chapters.add(chap["slug"])

        book_field = chap.get("book", None)

        if book_field:
            book_path = LOCAL_PATH / "book" / "_build" / "html" / Path(book_field).with_suffix(".html")

            if book_path.is_file():
                book_url = Path(book_field).with_suffix(".html")
                print(book_url)
            else:
                book_url = None
        else:
            book_url = None

        chapter_obj, _ = Chapter.objects.update_or_create(
            slug=chap["slug"],
            defaults={
                "title": chap.get("title", chap["slug"].replace("_", " ").title()),
                "order": chap.get("order", 0),
                "book_url": book_url,
                "status": "active",
            }
        )

        for a in chap.get("assignments", []):

            repo_assignments.add((chap["slug"], a["slug"]))
            
            desc_path = LOCAL_PATH / chap["slug"] / a["slug"] / "description.html"

            desc_content = desc_path.open(encoding="utf-8").read() if desc_path.is_file() else ""

            test_path = LOCAL_PATH / chap["slug"] / a["slug"] / "test_runner.py"

            test_content = test_path.open(encoding="utf-8").read() if test_path.is_file() else ""

            solution_path = LOCAL_PATH / chap["slug"] / a["slug"] / "solution.py"

            solution_content = solution_path.open(encoding="utf-8").read() if solution_path.is_file() else ""

            try:
                raw_publish_at = a.get("publish_at")

                if raw_publish_at:
                    dt = parse_datetime(raw_publish_at)

                    if dt is not None:
                        # If datetime is naive (no timezone info), make it aware
                        if timezone.is_naive(dt):
                            publish_at = timezone.make_aware(dt)
                        else:
                            publish_at = dt
                    else:
                        # parse_datetime returned None (invalid format)
                        print(f"Invalid datetime format for '{a['slug']}': {raw_publish_at}")
                        publish_at = None
                else:
                    publish_at = None
                    
                # publish_at = parse_datetime(a.get("publish_at")) if a.get("publish_at") else None
            except Exception as e:
                print(f"Invalid publish_at in assignment '{a['slug']}': {e}")
                publish_at = None

            try:
                raw_publish_until = a.get("publish_until")

                if raw_publish_until:
                    dt = parse_datetime(raw_publish_until)

                    if dt is not None:
                        # If datetime is naive (no timezone info), make it aware
                        if timezone.is_naive(dt):
                            publish_until = timezone.make_aware(dt)
                        else:
                            publish_until = dt
                    else:
                        # parse_datetime returned None (invalid format)
                        print(f"Invalid datetime format for '{a['slug']}': {raw_publish_until}")
                        publish_until = None
                else:
                    publish_until = None

            except Exception as e:
                print(f"Invalid publish_until in assignment '{a['slug']}': {e}")
                publish_until = None

            try:
                raw_publish_result_at = a.get("publish_result_at")

                if raw_publish_result_at:
                    dt = parse_datetime(raw_publish_result_at)

                    if dt is not None:
                        # If datetime is naive (no timezone info), make it aware
                        if timezone.is_naive(dt):
                            publish_result_at = timezone.make_aware(dt)
                        else:
                            publish_result_at = dt
                    else:
                        # parse_datetime returned None (invalid format)
                        print(f"Invalid datetime format for '{a['slug']}': {raw_publish_result_at}")
                        publish_result_at = None
                else:
                    publish_result_at = None

            except Exception as e:
                print(f"Invalid publish_until in assignment '{a['slug']}': {e}")
                publish_result_at = None

            Assignment.objects.update_or_create(
                chapter=chapter_obj,
                slug=a["slug"],
                defaults={
                    "title":       a.get("title", a["slug"].replace("-", " ").title()),
                    "order":       a.get("order", 0),
                    "description": desc_content,
                    "test_runner": test_content,
                    "solution":    solution_content,
                    "points":      a.get("points", 0),
                    "difficulty":  a.get("difficulty", "Easy"),
                    "publish_at": publish_at,
                    "publish_until": publish_until,
                    "publish_result_at": publish_result_at,
                    "is_exam":      a.get("is_exam", False),
                    "status":      "active",
                }
            )

    existing_chapters = set(Chapter.objects.values_list("slug", flat=True))
    missing_chapters = existing_chapters - repo_chapters
    if missing_chapters:
        Chapter.objects.filter(slug__in=missing_chapters).update(status="deleted")
        Assignment.objects.filter(chapter__slug__in=missing_chapters).update(status="deleted")
        print(f"Archived chapters: {', '.join(missing_chapters)}")

    existing_assignments = set(Assignment.objects.values_list("chapter__slug", "slug"))
    missing_assignments = existing_assignments - repo_assignments
    if missing_assignments:
        for chap_slug, ass_slug in missing_assignments:
            Assignment.objects.filter(chapter__slug=chap_slug, slug=ass_slug).update(status="deleted")
        print(f"Archived assignments: {', '.join(f'{c}/{a}' for c, a in missing_assignments)}")

    chap_active = Chapter.objects.filter(status="active").count()
    chap_deleted = Chapter.objects.filter(status="deleted").count()
    assn_active = Assignment.objects.filter(status="active").count()
    assn_deleted = Assignment.objects.filter(status="deleted").count()

    print(
        f"Sync completed successfully.\n"
        f"Chapters — Active: {chap_active}, Deleted: {chap_deleted}\n"
        f"Assignments — Active: {assn_active}, Deleted: {assn_deleted}"
    )