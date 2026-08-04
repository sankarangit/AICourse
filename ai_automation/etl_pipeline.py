"""
Student CSV ETL Automation

ETL Steps:
1. Load configuration
2. Load the input CSV
3. Validate CSV columns
4. Read student records
5. Perform basic Python cleaning
6. Clean each record using OpenAI
7. Validate the cleaned record
8. Create the final cleaned CSV
9. Create a failed-records CSV
10. Display the ETL summary
"""

# ============================================================
# STEP 1: IMPORT REQUIRED LIBRARIES
# ============================================================

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# STEP 2: CONFIGURE FILE PATHS AND SETTINGS
# ============================================================

INPUT_FILE = "student_sample_50_records.csv"
OUTPUT_FILE = "students_cleaned.csv"
FAILED_FILE = "students_failed.csv"

# You can change the model if required.
MODEL_NAME = "gpt-5-mini"

EXPECTED_COLUMNS = [
    "Student_ID",
    "Name",
    "Email",
    "Phone",
    "Course",
    "Fee_Paid",
    "City",
    "Enrolled_Date",
]


# ============================================================
# STEP 3: LOAD OPENAI API KEY
# ============================================================

load_dotenv()

# Getting the API key using your requested environment variable.
openapi_key = os.getenv("OpenAPI_API_Key")

if not openapi_key:
    raise ValueError(
        "OpenAPI_API_Key was not found.\n"
        "Create a .env file and add:\n"
        "OpenAPI_API_Key=your_actual_openai_api_key"
    )

client = OpenAI(api_key=openapi_key)


# ============================================================
# STEP 4: DEFINE THE OPENAI CLEANING INSTRUCTIONS
# ============================================================

SYSTEM_INSTRUCTIONS = """
You are a data-cleaning system for student registration records.

Clean the supplied student record according to these rules:

1. Return only one valid JSON object.
2. Return exactly these fields:
   Student_ID
   Name
   Email
   Phone
   Course
   Fee_Paid
   City
   Enrolled_Date

3. Remove leading, trailing and unnecessary spaces.
4. Convert Student_ID to uppercase.
5. Convert Name to proper title case.
6. Convert Email to lowercase and remove spaces.
7. Keep only digits in Phone.
8. Correct obvious spelling mistakes in Course and City.
9. Convert Course and City to title case.
10. Convert Fee_Paid to true or false.
11. Convert Enrolled_Date to YYYY-MM-DD.
12. Do not invent missing personal information.
13. If a text value cannot be safely corrected, return an empty string.
14. If Fee_Paid cannot be determined, return false.
15. Do not include markdown, code blocks, notes or explanations.
"""


# ============================================================
# STEP 5: LOAD THE INPUT CSV FILE
# ============================================================

def load_csv(file_path: str) -> pd.DataFrame:
    """
    Load the CSV file and keep every column as text.

    dtype=str prevents:
    - Phone numbers becoming integers
    - Leading zeroes being removed
    - Student IDs being changed
    """

    input_path = Path(file_path)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file was not found: {input_path.resolve()}"
        )

    try:
        dataframe = pd.read_csv(
            input_path,
            dtype=str,
            keep_default_na=False,
            encoding="utf-8",
        )
    except UnicodeDecodeError:
        # Retry for CSV files saved using some Windows applications.
        dataframe = pd.read_csv(
            input_path,
            dtype=str,
            keep_default_na=False,
            encoding="latin-1",
        )

    if dataframe.empty:
        raise ValueError("The input CSV file is empty.")

    print(f"Input file loaded: {input_path.resolve()}")
    print(f"Number of records: {len(dataframe)}")

    return dataframe


# ============================================================
# STEP 6: VALIDATE THE CSV COLUMNS
# ============================================================

def validate_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Verify that all expected columns are present.
    """

    # Remove spaces from CSV column headings.
    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    missing_columns = [
        column
        for column in EXPECTED_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "The following required columns are missing: "
            + ", ".join(missing_columns)
        )

    # Retain only the required columns and maintain their order.
    return dataframe[EXPECTED_COLUMNS].copy()


# ============================================================
# STEP 7: PERFORM BASIC PYTHON CLEANING
# ============================================================

def normalize_fee_paid(value: Any) -> Any:
    """
    Convert common Fee_Paid values into true or false.

    Unclear values are left unchanged so OpenAI can evaluate them.
    """

    text = str(value).strip().lower()

    true_values = {
        "true",
        "yes",
        "y",
        "1",
        "paid",
        "completed",
        "done",
    }

    false_values = {
        "false",
        "no",
        "n",
        "0",
        "not paid",
        "unpaid",
        "pending",
    }

    if text in true_values:
        return True

    if text in false_values:
        return False

    return text


def basic_clean_record(record: dict[str, Any]) -> dict[str, Any]:
    """
    Perform deterministic cleaning before calling OpenAI.

    This reduces token usage and gives OpenAI a cleaner input.
    """

    cleaned_record = {}

    # Remove unnecessary spaces from every value.
    for key, value in record.items():
        if value is None:
            cleaned_record[key] = ""
        else:
            cleaned_record[key] = re.sub(
                r"\s+",
                " ",
                str(value).strip(),
            )

    cleaned_record["Student_ID"] = (
        cleaned_record["Student_ID"]
        .replace(" ", "")
        .upper()
    )

    cleaned_record["Name"] = (
        cleaned_record["Name"]
        .title()
    )

    cleaned_record["Email"] = (
        cleaned_record["Email"]
        .replace(" ", "")
        .lower()
    )

    cleaned_record["Phone"] = re.sub(
        r"\D",
        "",
        cleaned_record["Phone"],
    )

    cleaned_record["Course"] = (
        cleaned_record["Course"]
        .title()
    )

    cleaned_record["City"] = (
        cleaned_record["City"]
        .title()
    )

    cleaned_record["Fee_Paid"] = normalize_fee_paid(
        cleaned_record["Fee_Paid"]
    )

    return cleaned_record


# ============================================================
# STEP 8: EXTRACT JSON FROM THE OPENAI RESPONSE
# ============================================================

def extract_json(response_text: str) -> dict[str, Any]:
    """
    Convert the OpenAI response into a Python dictionary.

    It also removes markdown code fences if the model returns them.
    """

    if not response_text:
        raise ValueError("OpenAI returned an empty response.")

    cleaned_text = response_text.strip()

    cleaned_text = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned_text,
        flags=re.IGNORECASE,
    )

    cleaned_text = re.sub(
        r"\s*```$",
        "",
        cleaned_text,
    )

    try:
        parsed_data = json.loads(cleaned_text)
    except json.JSONDecodeError:
        # Try to locate the first complete-looking JSON object.
        json_match = re.search(
            r"\{.*\}",
            cleaned_text,
            flags=re.DOTALL,
        )

        if not json_match:
            raise ValueError(
                f"OpenAI did not return valid JSON: {cleaned_text}"
            )

        parsed_data = json.loads(json_match.group())

    if not isinstance(parsed_data, dict):
        raise ValueError(
            "OpenAI response must be one JSON object."
        )

    return parsed_data


# ============================================================
# STEP 9: CLEAN ONE RECORD USING OPENAI
# ============================================================

def clean_with_openai(
    record: dict[str, Any],
    max_retries: int = 3,
) -> dict[str, Any]:
    """
    Send one student record to OpenAI for intelligent cleaning.

    Retry automatically when a temporary error occurs.
    """

    input_message = (
        "Clean this student record:\n"
        + json.dumps(
            record,
            ensure_ascii=False,
        )
    )

    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.responses.create(
                model=MODEL_NAME,
                instructions=SYSTEM_INSTRUCTIONS,
                input=input_message,
            )

            return extract_json(response.output_text)

        except Exception as error:
            last_error = error

            if attempt < max_retries:
                wait_seconds = attempt * 2

                print(
                    f"  OpenAI attempt {attempt} failed. "
                    f"Retrying..."
                )

                time.sleep(wait_seconds)

    raise RuntimeError(
        f"OpenAI cleaning failed after {max_retries} attempts: "
        f"{last_error}"
    )


# ============================================================
# STEP 10: VALIDATE AND STANDARDIZE THE CLEANED RECORD
# ============================================================

def convert_to_boolean(value: Any) -> bool:
    """
    Convert the returned Fee_Paid value into a Python Boolean.
    """

    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    return text in {
        "true",
        "yes",
        "y",
        "1",
        "paid",
    }


def standardize_date(value: Any) -> str:
    """
    Validate and convert the date into YYYY-MM-DD.

    Pandas is used as a fallback when OpenAI returns another
    recognizable date format.
    """

    text = str(value).strip()

    if not text:
        return ""

    # First check the expected format.
    try:
        parsed_date = datetime.strptime(
            text,
            "%Y-%m-%d",
        )

        return parsed_date.strftime("%Y-%m-%d")

    except ValueError:
        pass

    # Try to interpret other common formats.
    try:
        parsed_date = pd.to_datetime(
            text,
            dayfirst=True,
            errors="raise",
        )

        return parsed_date.strftime("%Y-%m-%d")

    except Exception:
        return ""


def validate_cleaned_record(
    record: dict[str, Any],
) -> dict[str, Any]:
    """
    Ensure that OpenAI returned the required fields and formats.
    """

    missing_fields = [
        field
        for field in EXPECTED_COLUMNS
        if field not in record
    ]

    if missing_fields:
        raise ValueError(
            "OpenAI response is missing fields: "
            + ", ".join(missing_fields)
        )

    validated_record = {
        "Student_ID": str(
            record.get("Student_ID", "")
        ).strip().upper(),

        "Name": str(
            record.get("Name", "")
        ).strip().title(),

        "Email": str(
            record.get("Email", "")
        ).strip().replace(" ", "").lower(),

        "Phone": re.sub(
            r"\D",
            "",
            str(record.get("Phone", "")),
        ),

        "Course": str(
            record.get("Course", "")
        ).strip().title(),

        "Fee_Paid": convert_to_boolean(
            record.get("Fee_Paid", False)
        ),

        "City": str(
            record.get("City", "")
        ).strip().title(),

        "Enrolled_Date": standardize_date(
            record.get("Enrolled_Date", "")
        ),
    }

    # Basic email format validation.
    email = validated_record["Email"]

    if email and not re.match(
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        email,
    ):
        raise ValueError(
            f"Invalid email returned: {email}"
        )

    # Basic phone validation.
    phone = validated_record["Phone"]

    if phone and not 8 <= len(phone) <= 15:
        raise ValueError(
            f"Invalid phone number returned: {phone}"
        )

    if not validated_record["Student_ID"]:
        raise ValueError("Student_ID cannot be empty.")

    return validated_record


# ============================================================
# STEP 11: READ AND PROCESS ALL STUDENT RECORDS
# ============================================================

def process_students(
    dataframe: pd.DataFrame,
) -> tuple[list[dict], list[dict]]:
    """
    Process every student record.

    Successful records and failed records are kept separately.
    """

    cleaned_records = []
    failed_records = []

    total_records = len(dataframe)

    for index, row in dataframe.iterrows():
        record_number = index + 1
        original_record = row.to_dict()

        print(
            f"Processing record "
            f"{record_number}/{total_records}..."
        )

        try:
            # First perform basic deterministic cleaning.
            python_cleaned_record = basic_clean_record(
                original_record
            )

            # Send the partially cleaned record to OpenAI.
            ai_cleaned_record = clean_with_openai(
                python_cleaned_record
            )

            # Validate and standardize the OpenAI output.
            final_record = validate_cleaned_record(
                ai_cleaned_record
            )

            cleaned_records.append(final_record)

            print(
                f"  Success: "
                f"{final_record['Student_ID']}"
            )

        except Exception as error:
            failed_record = original_record.copy()

            failed_record["Row_Number"] = record_number
            failed_record["Error"] = str(error)

            failed_records.append(failed_record)

            print(
                f"  Failed: {error}"
            )

    return cleaned_records, failed_records


# ============================================================
# STEP 12: REMOVE DUPLICATE STUDENT RECORDS
# ============================================================

def remove_duplicates(
    cleaned_records: list[dict],
) -> tuple[list[dict], int]:
    """
    Remove duplicate records based on Student_ID.

    The first occurrence is retained.
    """

    if not cleaned_records:
        return [], 0

    cleaned_dataframe = pd.DataFrame(cleaned_records)

    original_count = len(cleaned_dataframe)

    cleaned_dataframe = cleaned_dataframe.drop_duplicates(
        subset=["Student_ID"],
        keep="first",
    )

    duplicate_count = original_count - len(cleaned_dataframe)

    return (
        cleaned_dataframe.to_dict(orient="records"),
        duplicate_count,
    )


# ============================================================
# STEP 13: CREATE THE FINAL CLEANED CSV
# ============================================================

def create_output_csv(
    records: list[dict],
    output_file: str,
) -> None:
    """
    Write successfully cleaned records into the final CSV file.
    """

    output_dataframe = pd.DataFrame(
        records,
        columns=EXPECTED_COLUMNS,
    )

    output_dataframe.to_csv(
        output_file,
        index=False,
        encoding="utf-8",
    )

    print(
        f"\nFinal cleaned CSV created: "
        f"{Path(output_file).resolve()}"
    )


# ============================================================
# STEP 14: CREATE THE FAILED-RECORDS CSV
# ============================================================

def create_failed_csv(
    failed_records: list[dict],
    failed_file: str,
) -> None:
    """
    Write records that could not be cleaned into a separate file.
    """

    failed_path = Path(failed_file)

    if failed_records:
        failed_dataframe = pd.DataFrame(
            failed_records
        )

        failed_dataframe.to_csv(
            failed_path,
            index=False,
            encoding="utf-8",
        )

        print(
            f"Failed-records CSV created: "
            f"{failed_path.resolve()}"
        )

    elif failed_path.exists():
        # Remove an old failed file when the latest run has no failures.
        failed_path.unlink()


# ============================================================
# STEP 15: RUN THE COMPLETE ETL PIPELINE
# ============================================================

def run_etl() -> None:
    """
    Execute the complete Extract, Transform and Load process.
    """

    print("=" * 60)
    print("STUDENT CSV ETL AUTOMATION")
    print("=" * 60)

    # EXTRACT: Load and read the CSV.
    input_dataframe = load_csv(INPUT_FILE)

    input_dataframe = validate_columns(
        input_dataframe
    )

    input_count = len(input_dataframe)

    # TRANSFORM: Clean records using Python and OpenAI.
    cleaned_records, failed_records = process_students(
        input_dataframe
    )

    cleaned_records, duplicate_count = remove_duplicates(
        cleaned_records
    )

    # LOAD: Create the final output CSV files.
    create_output_csv(
        cleaned_records,
        OUTPUT_FILE,
    )

    create_failed_csv(
        failed_records,
        FAILED_FILE,
    )

    # Display the final ETL report.
    print("\n" + "=" * 60)
    print("ETL EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Input records       : {input_count}")
    print(f"Cleaned records     : {len(cleaned_records)}")
    print(f"Failed records      : {len(failed_records)}")
    print(f"Duplicates removed  : {duplicate_count}")
    print(f"Output file         : {OUTPUT_FILE}")

    if failed_records:
        print(f"Failed file         : {FAILED_FILE}")

    print("=" * 60)


# ============================================================
# STEP 16: PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        run_etl()

    except Exception as error:
        print("\nETL process stopped.")
        print(f"Error: {error}")

        raise