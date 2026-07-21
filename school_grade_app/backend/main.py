from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(title="School Marks & Grade API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SubjectMark(BaseModel):
    subject: str = Field(min_length=1, max_length=50)
    marks: float = Field(ge=0, le=100)


class GradeRequest(BaseModel):
    student_name: str = Field(min_length=1, max_length=100)
    roll_number: str = Field(min_length=1, max_length=30)
    subjects: List[SubjectMark] = Field(min_length=1)


class SubjectResult(SubjectMark):
    grade: str
    status: str


class GradeResponse(BaseModel):
    student_name: str
    roll_number: str
    total_marks: float
    maximum_marks: int
    percentage: float
    overall_grade: str
    result: str
    subjects: List[SubjectResult]


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


def calculate_grade(data: GradeRequest) -> GradeResponse:
    normalized_names = [item.subject.strip().casefold() for item in data.subjects]
    if any(not name for name in normalized_names):
        raise HTTPException(status_code=422, detail="Subject names cannot be blank.")
    if len(normalized_names) != len(set(normalized_names)):
        raise HTTPException(status_code=422, detail="Subject names must be unique.")

    total = sum(item.marks for item in data.subjects)
    percentage = total / len(data.subjects)
    passed = all(item.marks >= 35 for item in data.subjects)
    subject_results = [
        SubjectResult(
            subject=item.subject.strip(),
            marks=round(item.marks, 2),
            grade=grade_for(item.marks),
            status="Pass" if item.marks >= 35 else "Fail",
        )
        for item in data.subjects
    ]
    return GradeResponse(
        student_name=data.student_name.strip(),
        roll_number=data.roll_number.strip(),
        total_marks=round(total, 2),
        maximum_marks=len(data.subjects) * 100,
        percentage=round(percentage, 2),
        overall_grade=grade_for(percentage) if passed else "F",
        result="Pass" if passed else "Fail",
        subjects=subject_results,
    )


@app.get("/")
def root():
    return {"message": "School Marks & Grade API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/calculate-grade", response_model=GradeResponse)
def create_grade(data: GradeRequest):
    return calculate_grade(data)
