import os
import subprocess
import sys


def test_cli_runs_without_required_arguments():
    script_path = os.path.join(os.path.dirname(__file__), "genai_grade_system_assignment.py")
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(script_path),
    )

    assert result.returncode == 0
    assert '"student_name": "Student"' in result.stdout
