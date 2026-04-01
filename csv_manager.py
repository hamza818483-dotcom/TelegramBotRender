import csv
import os
import io
from datetime import datetime
from config import CSV_DIR, CSV_COLUMNS


def save_mcqs_to_csv(mcqs: list, title: str = None) -> str:
    """
    Save list of MCQ dicts to CSV file.
    Returns the file path.
    mcqs format:
    [
      {
        "question": "...",
        "options": ["A", "B", "C", "D"],
        "answer": 1,  # 1-based index
        "explanation": "..."
      },
      ...
    ]
    """
    if not title:
        title = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Sanitize filename
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip()
    safe_title = safe_title.replace(' ', '_')
    filename = f"{safe_title}_{datetime.now().strftime('%H%M%S')}.csv"
    filepath = os.path.join(CSV_DIR, filename)

    with open(filepath, "w", newline='', encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for mcq in mcqs:
            options = mcq.get("options", [])
            # Pad options to 5
            while len(options) < 5:
                options.append("")

            row = {
                "questions": mcq.get("question", ""),
                "option1": options[0] if len(options) > 0 else "",
                "option2": options[1] if len(options) > 1 else "",
                "option3": options[2] if len(options) > 2 else "",
                "option4": options[3] if len(options) > 3 else "",
                "option5": options[4] if len(options) > 4 else "",
                "answer": mcq.get("answer", 1),
                "explanation": mcq.get("explanation", ""),
                "type": 1,
                "section": 1,
            }
            writer.writerow(row)

    return filepath


def load_mcqs_from_csv(filepath: str) -> list:
    """
    Load MCQs from a CSV file (Rayvila format).
    Returns list of MCQ dicts.
    """
    mcqs = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            options = []
            for i in range(1, 6):
                opt = row.get(f"option{i}", "").strip()
                if opt:
                    options.append(opt)

            try:
                answer = int(row.get("answer", 1))
            except (ValueError, TypeError):
                answer = 1

            mcqs.append({
                "question": row.get("questions", "").strip(),
                "options": options,
                "answer": answer,
                "explanation": row.get("explanation", "").strip(),
            })
    return mcqs


def get_csv_as_bytes(filepath: str) -> bytes:
    with open(filepath, "rb") as f:
        return f.read()
