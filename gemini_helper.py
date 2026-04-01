import google.generativeai as genai
import json
import re
import base64
from config import GEMINI_API_KEY, GEMINI_MODEL

genai.configure(api_key=GEMINI_API_KEY)


def _parse_mcq_json(text: str) -> list:
    """Extract JSON array from Gemini response."""
    # Try direct parse first
    text = text.strip()
    
    # Remove markdown code blocks if present
    text = re.sub(r"```(?:json)?", "", text).strip()
    text = text.rstrip("`").strip()

    # Find JSON array
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        text = match.group(0)

    try:
        data = json.loads(text)
        return data
    except json.JSONDecodeError:
        return []


def _build_mcq_prompt(custom_prompt: str = "", mode: str = "generate") -> str:
    base = """তুমি একজন MCQ বিশেষজ্ঞ। নিচের নির্দেশ মেনে MCQ তৈরি করো।

আউটপুট ONLY valid JSON array হবে, অন্য কোনো টেক্সট থাকবে না।

Format:
[
  {
    "question": "প্রশ্নের টেক্সট",
    "options": ["অপশন ১", "অপশন ২", "অপশন ৩", "অপশন ৪"],
    "answer": 1,
    "explanation": "সঠিক উত্তরের ব্যাখ্যা"
  }
]

নিয়মাবলী:
- প্রতিটি MCQ তে ঠিক ৪টি অপশন থাকবে
- "answer" হবে সঠিক অপশনের 1-based index (1, 2, 3, বা 4)
- explanation সংক্ষিপ্ত কিন্তু তথ্যপূর্ণ হবে
- ভাষা: prompt অনুযায়ী (বাংলা বা ইংরেজি)
"""
    if custom_prompt:
        base += f"\nবিশেষ নির্দেশ: {custom_prompt}\n"
    return base


def generate_mcq_from_text(text: str, custom_prompt: str = "", count: int = 10) -> list:
    """Generate MCQs from plain text using Gemini."""
    model = genai.GenerativeModel(GEMINI_MODEL)
    
    prompt = _build_mcq_prompt(custom_prompt)
    prompt += f"\nমোট {count}টি MCQ তৈরি করো।\n\nটেক্সট:\n{text}"
    
    response = model.generate_content(prompt)
    return _parse_mcq_json(response.text)


def generate_mcq_from_image(image_bytes: bytes, mime_type: str, custom_prompt: str = "", count: int = 5) -> list:
    """Generate MCQs from image using Gemini Vision."""
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = _build_mcq_prompt(custom_prompt)
    prompt += f"\nছবিতে যা দেখছো তার উপর ভিত্তি করে {count}টি MCQ তৈরি করো।"

    image_part = {
        "mime_type": mime_type,
        "data": image_bytes
    }

    response = model.generate_content([prompt, image_part])
    return _parse_mcq_json(response.text)


def extract_mcq_from_text(text: str) -> list:
    """
    /qbm mode: Extract existing MCQs from text (PDF page content).
    Try to parse ready-made MCQs without AI generation.
    """
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = """নিচের টেক্সটে যে MCQ গুলো আছে সেগুলো হুবহু তুলে নাও (নতুন MCQ বানিও না)।
আউটপুট ONLY valid JSON array হবে, অন্য কোনো টেক্সট থাকবে না।

Format:
[
  {
    "question": "প্রশ্নের টেক্সট",
    "options": ["অপশন ১", "অপশন ২", "অপশন ৩", "অপশন ৪"],
    "answer": 1,
    "explanation": ""
  }
]

নিয়মাবলী:
- যদি ৪টির বেশি অপশন থাকে, প্রথম ৪টি নাও
- যদি উত্তর দেওয়া থাকে answer field এ সেই index দাও, না থাকলে 1 দাও
- শুধু টেক্সটে যা আছে তাই তুলবে

টেক্সট:
""" + text

    response = model.generate_content(prompt)
    return _parse_mcq_json(response.text)
