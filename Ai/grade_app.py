"""Streamlit Student Grade Calculator assignment."""

import math

import streamlit as st


def calculate_grade(mark: float) -> str:
    """Convert a mark from 0 to 100 into its corresponding letter grade."""
    if not math.isfinite(mark) or not 0 <= mark <= 100:
        raise ValueError("Mark must be between 0 and 100.")
    if mark >= 90:
        return "A"
    if mark >= 80:
        return "B"
    if mark >= 70:
        return "C"
    if mark >= 60:
        return "D"
    return "E"


def format_mark(mark: float) -> str:
    """Display whole-number marks without an unnecessary decimal point."""
    return str(int(mark)) if mark.is_integer() else f"{mark:g}"


def main() -> None:
    """Render the Streamlit user interface."""
    st.set_page_config(
        page_title="Student Grade Calculator",
        page_icon="🎓",
        layout="centered",
    )

    st.title("🎓 Student Grade Calculator")
    st.write("Enter a mark between 0 and 100 to calculate the letter grade.")

    mark_text = st.text_input(
        "Enter your mark (0-100)",
        placeholder="For example: 85",
    )

    if st.button("Calculate Grade", type="primary", use_container_width=True):
        cleaned_mark = mark_text.strip()

        if not cleaned_mark:
            st.warning("Please enter a mark before calculating the grade.")
        else:
            try:
                mark = float(cleaned_mark)
            except ValueError:
                st.error("Please enter a valid number, such as 85 or 92.5.")
            else:
                if not math.isfinite(mark) or not 0 <= mark <= 100:
                    st.error("The mark must be between 0 and 100.")
                else:
                    grade = calculate_grade(mark)
                    display_mark = format_mark(mark)
                    st.success(f"Mark: {display_mark} -> Grade: {grade}")

                    mark_column, grade_column = st.columns(2)
                    mark_column.metric("Mark", display_mark)
                    grade_column.metric("Grade", grade)

    st.divider()
    st.subheader("Grading Scale")
    st.table(
        [
            {"Mark range": "90-100", "Grade": "A"},
            {"Mark range": "80-89", "Grade": "B"},
            {"Mark range": "70-79", "Grade": "C"},
            {"Mark range": "60-69", "Grade": "D"},
            {"Mark range": "Below 60", "Grade": "E"},
        ]
    )


if __name__ == "__main__":
    main()
