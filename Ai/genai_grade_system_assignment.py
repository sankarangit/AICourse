from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

DEFAULT_STUDENT_NAME = "Student"
DEFAULT_ROLL_NUMBER = "001"
DEFAULT_SUBJECTS = ["Math", "English", "Science"]


@dataclass
class SubjectMark:
    subject: str
    marks: float


@dataclass
class GradeResult:
    student_name: str
    roll_number: str
    total_marks: float
    maximum_marks: int
    percentage: float
    overall_grade: str
    result: str
    subjects: List[dict]

    def to_dict(self) -> dict:
        return asdict(self)


def grade_for(mark: float) -> str:
    if mark >= 90:
        return "A+"
    if mark >= 80:
        return "A"
    if mark >= 70:
        return "B"
    if mark >= 60:
        return "C"
    if mark >= 50:
        return "D"
    if mark >= 35:
        return "E"
    return "F"


def calculate_grade(student_name: str, roll_number: str, subjects: List[SubjectMark]) -> GradeResult:
    if not student_name.strip():
        raise ValueError("Student name cannot be empty.")
    if not roll_number.strip():
        raise ValueError("Roll number cannot be empty.")
    if not subjects:
        raise ValueError("At least one subject is required.")

    normalized_subjects = [item.subject.strip().casefold() for item in subjects]
    if any(not name for name in normalized_subjects):
        raise ValueError("Subject names cannot be blank.")
    if len(normalized_subjects) != len(set(normalized_subjects)):
        raise ValueError("Subject names must be unique.")

    total_marks = sum(item.marks for item in subjects)
    percentage = total_marks / len(subjects)
    passed = all(item.marks >= 35 for item in subjects)

    subject_results = []
    for item in subjects:
        subject_results.append(
            {
                "subject": item.subject.strip(),
                "marks": round(item.marks, 2),
                "grade": grade_for(item.marks),
                "status": "Pass" if item.marks >= 35 else "Fail",
            }
        )

    overall_grade = grade_for(percentage) if passed else "F"
    result = "Pass" if passed else "Fail"

    return GradeResult(
        student_name=student_name.strip(),
        roll_number=roll_number.strip(),
        total_marks=round(total_marks, 2),
        maximum_marks=len(subjects) * 100,
        percentage=round(percentage, 2),
        overall_grade=overall_grade,
        result=result,
        subjects=subject_results,
    )


def parse_subjects(raw_subjects: Optional[List[str]]) -> List[SubjectMark]:
    if not raw_subjects:
        return []

    parsed: List[SubjectMark] = []
    for entry in raw_subjects:
        if ":" not in entry:
            raise ValueError(f"Invalid subject format: {entry}. Use Subject:Marks")
        subject, marks_text = entry.split(":", 1)
        try:
            marks = float(marks_text.strip())
        except ValueError as exc:
            raise ValueError(f"Invalid marks for subject {subject}: {marks_text}") from exc
        parsed.append(SubjectMark(subject=subject.strip(), marks=marks))
    return parsed


def load_subjects_from_json(path: str) -> List[SubjectMark]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    subjects = payload.get("subjects", [])
    return [SubjectMark(subject=item["subject"], marks=float(item["marks"])) for item in subjects]


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate school grades using the GenAI grade system assignment")
    parser.add_argument("--student-name", help="Student name")
    parser.add_argument("--roll-number", help="Roll number")
    parser.add_argument("--subjects", nargs="+", help="Example: Math:90 English:80 Science:70")
    parser.add_argument("--json-file", help="Optional JSON file containing a subjects list")
    parser.add_argument("--output-json", help="Optional file path to write the final result")
    args = parser.parse_args()

    student_name = args.student_name or DEFAULT_STUDENT_NAME
    roll_number = args.roll_number or DEFAULT_ROLL_NUMBER

    if args.json_file and args.subjects:
        raise SystemExit("Use either --subjects or --json-file, not both.")

    if args.json_file:
        subjects = load_subjects_from_json(args.json_file)
    elif args.subjects:
        subjects = parse_subjects(args.subjects)
    else:
        subjects = [SubjectMark(subject=name, marks=75.0) for name in DEFAULT_SUBJECTS]

    result = calculate_grade(student_name, roll_number, subjects)
    print(json.dumps(result.to_dict(), indent=2))

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        print(f"\nSaved result to {args.output_json}")


if __name__ == "__main__":
    main()
