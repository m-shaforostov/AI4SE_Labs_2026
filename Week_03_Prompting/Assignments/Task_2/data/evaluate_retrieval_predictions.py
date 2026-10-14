# To run this script, a file with predictions of SQL queries must be provided in the same format as the labels file. The script will execute each predicted SQL query against a database constructed from the provided schema and data, and compare the results to the expected results from the labels file. The accuracy of the predictions will be calculated and printed.

import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict, deque
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent
LABELS_PATH = DATA_DIR / "restaurants_dataset.csv"
PREDICTIONS_PATH = DATA_DIR / "restaurants_dataset_predictions.csv"
SCHEMA_PATH = DATA_DIR / "restaurants-schema.csv"
DATABASE_PATH = DATA_DIR / "restaurants-db.txt"


def sqlite_type(schema_type):
    normalized_type = schema_type.strip().lower()
    if normalized_type.startswith("int"):
        return "INTEGER"
    if normalized_type.startswith("decimal") or normalized_type.startswith("float"):
        return "REAL"
    return "TEXT"


def load_database():
    tables = {}
    with SCHEMA_PATH.open(encoding="utf-8", newline="") as schema_file:
        for table, field, primary_key, _foreign_key, column_type in csv.reader(
            schema_file, skipinitialspace=True
        ):
            table = table.strip()
            field = field.strip()
            if table == "-":
                continue
            tables.setdefault(table, []).append(
                (field, sqlite_type(column_type), primary_key.strip().lower() == "y")
            )

    connection = sqlite3.connect(":memory:")
    for table, columns in tables.items():
        definitions = []
        for field, column_type, primary_key in columns:
            definition = f'"{field}" {column_type}'
            if primary_key:
                definition += " PRIMARY KEY"
            definitions.append(definition)
        connection.execute(f'CREATE TABLE "{table}" ({", ".join(definitions)})')

    with DATABASE_PATH.open(encoding="utf-8") as database_file:
        for line_number, line in enumerate(database_file, start=1):
            match = re.fullmatch(r"([A-Z_]+)\((.*)\)", line.rstrip("\r\n"))
            if match is None:
                raise ValueError(f"Invalid database record on line {line_number}")

            table, values_text = match.groups()
            if table not in tables:
                raise ValueError(f"Unknown table {table!r} on line {line_number}")

            values = next(csv.reader([values_text], skipinitialspace=True))
            columns = tables[table]
            if len(values) != len(columns):
                raise ValueError(
                    f"Expected {len(columns)} values for {table} on line "
                    f"{line_number}, got {len(values)}"
                )

            converted_values = []
            for value, (_field, column_type, _primary_key) in zip(values, columns):
                if column_type == "INTEGER":
                    converted_values.append(int(value))
                elif column_type == "REAL":
                    converted_values.append(float(value))
                else:
                    converted_values.append(value)

            placeholders = ", ".join("?" for _ in columns)
            connection.execute(
                f'INSERT INTO "{table}" VALUES ({placeholders})', converted_values
            )

    return connection


def row_multiset(rows):
    return Counter(tuple(row) for row in rows)


def main():
    csv.field_size_limit(1_000_000_000)
    labels_by_question = defaultdict(deque)
    with LABELS_PATH.open(encoding="utf-8", newline="") as source:
        for line_number, row in enumerate(csv.DictReader(source), start=2):
            try:
                result = json.loads(row["result"])
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON label result on line {line_number} "
                    f"of {LABELS_PATH}"
                ) from error
            if not isinstance(result, list):
                raise ValueError(
                    f"Expected a JSON array label result on line {line_number} "
                    f"of {LABELS_PATH}"
                )
            labels_by_question[row["question"]].append(result)

    connection = load_database()
    try:
        total = 0
        correct = 0
        with PREDICTIONS_PATH.open(encoding="utf-8", newline="") as source:
            for line_number, row in enumerate(csv.DictReader(source), start=2):
                question = row["question"]
                if not labels_by_question[question]:
                    raise ValueError(
                        f"No matching label question for prediction on line "
                        f"{line_number}: {question!r}"
                    )

                expected_rows = labels_by_question[question].popleft()
                try:
                    predicted_rows = connection.execute(
                        row["predicted_sql"]
                    ).fetchall()
                except sqlite3.Error as error:
                    raise RuntimeError(
                        f"Could not execute predicted SQL on line {line_number} "
                        f"of {PREDICTIONS_PATH}"
                    ) from error

                total += 1
                if row_multiset(predicted_rows) == row_multiset(expected_rows):
                    correct += 1

        unmatched_labels = sum(len(results) for results in labels_by_question.values())
        if unmatched_labels:
            raise ValueError(
                f"{unmatched_labels} label records had no corresponding prediction"
            )
    finally:
        connection.close()

    if total == 0:
        raise ValueError(f"No predictions found in {PREDICTIONS_PATH}")

    accuracy = correct / total
    print(f"Accuracy: {accuracy:.4f} ({accuracy:.2%})")
    print(f"Correct: {correct}/{total}")


if __name__ == "__main__":
    main()
