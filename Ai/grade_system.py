"""Student Grade System.

Accepts a mark between 0 and 100 and prints the corresponding letter grade.
Uses only the Python standard library.
"""


def calculate_grade(mark: float) -> str:
    """Return the letter grade for a valid mark between 0 and 100."""
    if not 0 <= mark <= 100:
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
    """Display whole-number marks without a decimal point."""
    return str(int(mark)) if mark.is_integer() else str(mark)


def main() -> None:
    """Read a mark from the terminal and display its grade."""
    user_input = input("Enter your mark (0-100): ").strip()

    try:
        mark = float(user_input)
    except ValueError:
        print("Invalid input. Please enter a numeric mark between 0 and 100.")
        return

    try:
        grade = calculate_grade(mark)
    except ValueError as error:
        print(f"Invalid input. {error}")
        return

    print(f"Mark: {format_mark(mark)} -> Grade: {grade}")


if __name__ == "__main__":
    main()