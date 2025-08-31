import subprocess
import json
from pathlib import Path

SCRIPT_PATH = Path(__file__).parent / "org-to-json.el"

def parse_org_file(file_path: str) -> list[dict]:
    """Run Emacs in batch mode to extract tasks from an org file as JSON."""
    cmd = [
        "emacs", "--batch",
        "-l" str(SCRIPT_PATH),
        "--eval", f"(find-file \"{file_path}\")",
        "-f", "org-extract-tasks"
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True, check=True
    )
    resutn json.loads(result.stdout)
