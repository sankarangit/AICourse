from backend.main import GradeRequest, SubjectMark, calculate_grade, grade_for


def test_grade_boundaries():
    assert grade_for(90) == "A+"
    assert grade_for(80) == "A"
    assert grade_for(35) == "E"
    assert grade_for(34.99) == "F"


def test_calculation_pass():
    request = GradeRequest(
        student_name="Anita",
        roll_number="12",
        subjects=[SubjectMark(subject="Math", marks=90), SubjectMark(subject="English", marks=80)],
    )
    result = calculate_grade(request)
    assert result.total_marks == 170
    assert result.percentage == 85
    assert result.overall_grade == "A"
    assert result.result == "Pass"


def test_one_failed_subject_fails_overall():
    request = GradeRequest(
        student_name="Ravi",
        roll_number="13",
        subjects=[SubjectMark(subject="Math", marks=100), SubjectMark(subject="English", marks=30)],
    )
    result = calculate_grade(request)
    assert result.percentage == 65
    assert result.overall_grade == "F"
    assert result.result == "Fail"
