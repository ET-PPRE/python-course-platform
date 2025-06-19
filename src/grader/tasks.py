# tasks.py
import base64
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from celery import shared_task, states
from celery.exceptions import SoftTimeLimitExceeded

from grader.models import Submission

SANDBOX_IMAGE = "python-course-platform-sandbox:3.12"

# Resource limits
CPU_LIMIT = "1"
MEM_LIMIT = "256m"
PIDS_LIMIT = "128"
TMPFS_OPTS = "rw,nosuid,nodev,noexec,size=64m"
TIMEOUT_USER = 10
TIMEOUT_TESTS = 10
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2 MB
MAX_IMAGE_COUNT = 3

# Shared dir mapping:
# - Inside Celery container: GRADER_HOST_DIR (default: /grader)
# - On the host (Docker daemon filesystem): GRADER_BIND_DIR (default: /var/tmp/grader)
CONTAINER_SHARED_ROOT = os.environ.get("GRADER_HOST_DIR", "/grader")
HOST_SHARED_ROOT = os.environ.get("GRADER_BIND_DIR", "/var/tmp/grader")

def _container_to_host_path(container_path: str) -> str:
    c_root = Path(CONTAINER_SHARED_ROOT).resolve()
    h_root = Path(HOST_SHARED_ROOT).resolve()
    p = Path(container_path).resolve()
    try:
        rel = p.relative_to(c_root)
    except Exception:
        print(f"[DEBUG] Path {p} is not under container shared root {c_root}; passing through to daemon.")
        return str(p)
    host_path = h_root / rel
    return str(host_path)

def run_in_sandbox(args, host_workdir_container, rw_mount=False, timeout=8, env=None):
    host_mount = _container_to_host_path(host_workdir_container)
    mount_flag = f"{host_mount}:/work:{'rw' if rw_mount else 'ro'},Z"

    env_args = []
    if env:
        for k, v in env.items():
            env_args += ["-e", f"{k}={v}"]

    cmd = [
        "docker", "run", "--rm",
        "--network", "none",
#        "--cpus", CPU_LIMIT,
        "--memory", MEM_LIMIT,
        "--pids-limit", PIDS_LIMIT,
        "--tmpfs", f"/tmp:{TMPFS_OPTS}",
        "-e", "MPLBACKEND=Agg",
        "-v", mount_flag,
        "-w", "/work",
        *env_args,
        SANDBOX_IMAGE,
        "run", "python",
        *args,
    ]
    print(f"[DEBUG] Host mount for sandbox: {host_mount} -> /work")
    print(f"[DEBUG] Running sandbox command: {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

def encode_images_for_ui(work_c: Path):
    supported_exts = {".png", ".jpg", ".jpeg", ".svg"}
    images = []

    for file in sorted(work_c.iterdir()):
        if file.suffix.lower() not in supported_exts:
            continue

        if len(images) >= MAX_IMAGE_COUNT:
            print(f"[DEBUG] Reached max image count ({MAX_IMAGE_COUNT}), skipping {file.name}")
            break

        try:
            image_data = file.read_bytes()
        except Exception as e:
            print(f"[DEBUG] Error reading {file.name}: {e}")
            continue

        if len(image_data) > MAX_IMAGE_SIZE:
            print(f"[DEBUG] Skipping {file.name}: too large ({len(image_data)} bytes)")
            continue

        try:
            b64 = base64.b64encode(image_data).decode("utf-8")
            images.append({
                "name": file.name,
                "data_uri": f"data:image/{file.suffix[1:]};base64,{b64}",
            })
            print(f"[DEBUG] Captured image: {file.name} ({len(image_data)} bytes)")
        except Exception as e:
            print(f"[DEBUG] Error encoding {file.name}: {e}")
            continue

    return images

@shared_task(bind=True, soft_time_limit=max(TIMEOUT_USER, TIMEOUT_TESTS) + 5)
def run_user_code(self, submission_id: int, code: str, test_runner: str):
    print(f"[DEBUG] Starting run_user_code for submission {submission_id}")

    try:
        Path(CONTAINER_SHARED_ROOT).mkdir(parents=True, exist_ok=True)
        print(f"[DEBUG] Ensured container shared root exists: {CONTAINER_SHARED_ROOT}")
    except Exception as e:
        print(f"[DEBUG] Could not ensure container shared root: {e}")

    host_tmp_container = tempfile.mkdtemp(prefix=f"sub_{submission_id}_", dir=CONTAINER_SHARED_ROOT)
    print(f"[DEBUG] Using shared host dir for mount (container path): {host_tmp_container}")

    host_tmp_host = _container_to_host_path(host_tmp_container)
    print(f"[DEBUG] Equivalent host path seen by Docker daemon: {host_tmp_host}")

    work_c = Path(host_tmp_container)
    # work_h = Path(host_tmp_host)

    # Locate assignment directory and copy additional files like CSVs and TXTs
    try:
        sub = Submission.objects.select_related("assignment__chapter").get(pk=submission_id)
        assignment_dir = Path(os.environ.get("LOCAL_PATH", "/app/python_course_repo")) / sub.assignment.chapter.slug / sub.assignment.slug

        # Copy any .csv or .txt files in the assignment folder
        for file in assignment_dir.glob("*"):
            if file.suffix in [".csv", ".txt"]:
                shutil.copy(file, work_c / file.name)
                print(f"[DEBUG] Copied file to sandbox: {file.name}")
    except Exception as e:
        print(f"[DEBUG] Could not copy CSV/TXT files to sandbox: {e}")

    user_file = work_c / "user_submission.py"
    tests_file = work_c / "test_runner.py"
    user_file.write_text(code, encoding="utf-8")
    tests_file.write_text(test_runner, encoding="utf-8")
    print("[DEBUG] Wrote user_submission.py and test_runner.py")
    try:
        print("[DEBUG] Container view of work dir contents:")
        for p in work_c.iterdir():
            print(f"   - {p.name} ({p.stat().st_size} bytes)")
    except Exception as e:
        print(f"[DEBUG] Could not list container work dir: {e}")

    # Phase A: run submitted code
    print("[DEBUG] Phase A: Running user code")
    try:
        proc_user = run_in_sandbox(
            ["user_submission.py"],
            host_workdir_container=host_tmp_container,
            rw_mount=True,
            timeout=TIMEOUT_USER,
            env=None,
        )
    except subprocess.TimeoutExpired:
        print("[DEBUG] User code timed out")
        proc_user = None

    if proc_user is None:
        user_stdout = ""
        user_stderr = "Timed out while running the student program."
        user_exit = -1
    else:
        print(f"[DEBUG] User code exit={proc_user.returncode}")
        print(f"[DEBUG] User stdout:\n{proc_user.stdout}")
        print(f"[DEBUG] User stderr:\n{proc_user.stderr}")
        user_stdout = proc_user.stdout
        user_stderr = proc_user.stderr
        user_exit = proc_user.returncode
    
    # === Capture image outputs ===
    image_files = encode_images_for_ui(work_c)

    # print(f"[DEBUG] Total images captured: {len(image_files)}")
    # for img in image_files:
    #     print(f"[DEBUG] - {img['name']} ({len(img['data_uri'])} characters)")

    # Phase B: run the test runner (prints JSON)
    print("[DEBUG] Phase B: Running test runner")
    grading = {"score": 0, "total": 0, "output": "", "errors": ["No results"]}
    try:
        proc_tests = run_in_sandbox(
            ["test_runner.py"],
            host_workdir_container=host_tmp_container,
            rw_mount=True,
            timeout=TIMEOUT_TESTS,
            env=None,
        )
        print(f"[DEBUG] Test runner exit={proc_tests.returncode}")
        print(f"[DEBUG] Test runner stdout:\n{proc_tests.stdout}")
        print(f"[DEBUG] Test runner stderr:\n{proc_tests.stderr}")

        stdout_json = (proc_tests.stdout or "").strip()
        if stdout_json:
            try:
                data = json.loads(stdout_json)
                print(f"[DEBUG] Parsed JSON: {data}")
                score = float(data.get("score", 0))
                total = float(data.get("total", 0)) or 0.0
                output = str(data.get("output", "")).strip()
                errors = list(data.get("errors", [])) if isinstance(data.get("errors", []), list) else []
                grading = {"score": score, "total": total, "output": output, "errors": errors}
            except Exception as parse_err:
                print(f"[DEBUG] Failed to parse JSON: {parse_err}")
                grading = {
                    "score": 0,
                    "total": 0,
                    "output": stdout_json,
                    "errors": [f"Failed to parse test JSON: {parse_err}", (proc_tests.stderr or "").strip()],
                }
        else:
            print("[DEBUG] Test runner produced no stdout")
            grading = {
                "score": 0,
                "total": 0,
                "output": "",
                "errors": ["Test runner produced no output", (proc_tests.stderr or "").strip()],
            }

    except subprocess.TimeoutExpired:
        print("[DEBUG] Test runner timed out")
        grading = {"score": 0, "total": 0, "output": "", "errors": ["Timed out while running tests."]}

    score = float(grading.get("score", 0) or 0)
    total = float(grading.get("total", 0) or 0)
    grade_pct = round(100.0 * score / total, 2) if total > 0 else 0.0
    print(f"[DEBUG] Computed grade_pct={grade_pct}")

    payload = {
        "status": "success",
        "user": {"stdout": user_stdout, "stderr": user_stderr, "exit_code": user_exit},
        "grading": {"grade_pct": grade_pct, **grading},
        "images": image_files,
    }

    # print(f"[DEBUG] Final payload: {payload}")
    self.update_state(state=states.SUCCESS, meta=payload)

    # Cleanup
    try:
        shutil.rmtree(host_tmp_container, ignore_errors=True)
        print(f"[DEBUG] Cleaned up temp dir (container path) {host_tmp_container}")
    except Exception as e:
        print(f"[DEBUG] Failed to cleanup temp dir: {e}")

    return payload