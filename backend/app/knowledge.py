from pathlib import Path

PROFILE = (Path(__file__).resolve().parent.parent / "content" / "profile.md").read_text()
