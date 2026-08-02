import os
from datetime import datetime, timezone
from pathlib import Path

# Everything below is per-deployment content: swap the files in content/ (and the env vars
# in .env) to point Relay at a different person/profile without touching app code.
CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

CANDIDATE_NAME = os.environ.get("CANDIDATE_NAME", "Your Name")

PROFILE = (CONTENT_DIR / "profile.md").read_text()
SYSTEM_PROMPT_TEMPLATE = (CONTENT_DIR / "system_prompt.md").read_text()

RESUME_FILE = os.environ.get("RESUME_FILE", "resume-editorial.pdf")
_resume_path = CONTENT_DIR / RESUME_FILE
_resume_stat = _resume_path.stat()

RESUME_INFO = {
    "name": CANDIDATE_NAME,
    "format": "PDF",
    "updated": datetime.fromtimestamp(_resume_stat.st_mtime, tz=timezone.utc).strftime("%b %Y"),
    "size": f"{_resume_stat.st_size // 1024} KB",
    "url": f"/static/{RESUME_FILE}",
}
