import os

import pandas as pd
import requests
import streamlit as st


API_URL = os.getenv("GRADE_API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="School Grade Calculator", page_icon=":school:", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(145deg, #f4f8ff, #eefbf7); }
    .block-container { max-width: 1050px; padding-top: 2rem; }
    .hero { color: white; padding: 1.8rem 2rem; border-radius: 20px; margin-bottom: 1.3rem;
            background: linear-gradient(120deg, #173f73, #147d78); box-shadow: 0 12px 30px rgba(23,63,115,.18); }
    .hero h1 { margin: 0; font-size: 2.15rem; }
    .hero p { margin: .45rem 0 0; color: #dcecff; }
    div[data-testid="stForm"] { background: rgba(255,255,255,.95); border: 1px solid #dce7f2;
            border-radius: 18px; padding: 1.3rem 1.5rem 1.5rem; box-shadow: 0 8px 25px rgba(32,70,110,.08); }
    div[data-testid="stMetric"] { background: white; border: 1px solid #dbe7f0;
            border-radius: 14px; padding: 1rem; box-shadow: 0 5px 15px rgba(32,70,110,.06); }
    .stFormSubmitButton > button { border-radius: 10px; min-height: 3rem; font-weight: 700; }
    </style>
    <div class="hero"><h1>School Marks & Grade Calculator</h1>
    <p>Calculate subject grades, total marks, percentage, and the final result.</p></div>
    """,
    unsafe_allow_html=True,
)

with st.form("grade_form"):
    st.subheader("Student information")
    left, right = st.columns(2)
    student_name = left.text_input("Student name")
    roll_number = right.text_input("Roll number")
    subject_count = st.number_input("Number of subjects", min_value=1, max_value=12, value=5)

    default_subjects = ["English", "Mathematics", "Science", "Social Science", "Computer Science"]
    subjects = []
    st.subheader("Subject marks")
    st.caption("Enter marks out of 100. The pass mark for every subject is 35.")
    for index in range(int(subject_count)):
        name_col, mark_col = st.columns([2, 1])
        default_name = default_subjects[index] if index < len(default_subjects) else f"Subject {index + 1}"
        subject = name_col.text_input("Subject", value=default_name, key=f"subject_{index}")
        marks = mark_col.number_input(
            "Marks", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key=f"marks_{index}"
        )
        subjects.append({"subject": subject, "marks": marks})

    submitted = st.form_submit_button("Calculate grade", type="primary", use_container_width=True)

if submitted:
    if not student_name.strip() or not roll_number.strip():
        st.error("Please enter the student name and roll number.")
    elif any(not item["subject"].strip() for item in subjects):
        st.error("Please enter every subject name.")
    else:
        payload = {
            "student_name": student_name.strip(),
            "roll_number": roll_number.strip(),
            "subjects": subjects,
        }
        try:
            response = requests.post(f"{API_URL}/calculate-grade", json=payload, timeout=10)
            if response.ok:
                result = response.json()
                if result["result"] == "Pass":
                    st.success(f"Result: {result['result']}")
                else:
                    st.error("Result: Fail")

                col1, col2, col3 = st.columns(3)
                col1.metric("Total", f"{result['total_marks']} / {result['maximum_marks']}")
                col2.metric("Percentage", f"{result['percentage']}%")
                col3.metric("Overall grade", result["overall_grade"])

                st.progress(float(result["percentage"]) / 100, text=f"Overall score: {result['percentage']}%")

                table = pd.DataFrame(result["subjects"]).rename(
                    columns={"subject": "Subject", "marks": "Marks", "grade": "Grade", "status": "Status"}
                )
                st.dataframe(table, hide_index=True, use_container_width=True)
            else:
                detail = response.json().get("detail", "Unable to calculate the grade.")
                st.error(str(detail))
        except requests.RequestException:
            st.error("Cannot connect to the FastAPI server. Start the API first, then try again.")

with st.expander("Grade scale"):
    st.markdown("**A+**: 90-100 | **A**: 80-89 | **B**: 70-79 | **C**: 60-69 | **D**: 50-59 | **E**: 35-49 | **F**: below 35")
