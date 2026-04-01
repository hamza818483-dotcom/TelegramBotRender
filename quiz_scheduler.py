import json
import os
import asyncio
from datetime import datetime

QUIZ_SCHEDULE_FILE = "quiz_schedules.json"


def load_schedules():
    if not os.path.exists(QUIZ_SCHEDULE_FILE):
        return {}
    with open(QUIZ_SCHEDULE_FILE, "r") as f:
        return json.load(f)


def save_schedules(data):
    with open(QUIZ_SCHEDULE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def save_quiz(quiz_id: str, quiz_data: dict):
    """Save a quiz configuration."""
    schedules = load_schedules()
    schedules[quiz_id] = quiz_data
    save_schedules(schedules)


def get_quiz(quiz_id: str) -> dict:
    schedules = load_schedules()
    return schedules.get(quiz_id)


def delete_quiz(quiz_id: str):
    schedules = load_schedules()
    if quiz_id in schedules:
        del schedules[quiz_id]
        save_schedules(schedules)


def list_quizzes() -> list:
    schedules = load_schedules()
    return list(schedules.values())
