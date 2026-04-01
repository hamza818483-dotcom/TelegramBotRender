# 🤖 MCQ Poll Bot — Setup Guide

## ⚙️ ধাপ ১: Prerequisites

Python 3.10+ ইনস্টল থাকতে হবে।

---

## ⚙️ ধাপ ২: Dependencies ইনস্টল করুন

```bash
pip install -r requirements.txt
```

---

## ⚙️ ধাপ ৩: config.py সেটআপ করুন

`config.py` ফাইল খুলুন এবং এগুলো পরিবর্তন করুন:

```python
TELEGRAM_BOT_TOKEN = "আপনার_বট_টোকেন"   # @BotFather থেকে
GEMINI_API_KEY = "আপনার_gemini_key"        # aistudio.google.com থেকে
OWNER_ID = 123456789                        # @userinfobot দিয়ে আপনার ID পান
```

### Gemini API Key পাবেন কোথায়?
👉 https://aistudio.google.com/app/apikey

### আপনার Telegram User ID পাবেন:
👉 Telegram এ @userinfobot কে মেসেজ করুন

---

## ⚙️ ধাপ ৪: Bot চালু করুন

```bash
python bot.py
```

---

## 📋 সব কমান্ড

| কমান্ড | কাজ |
|--------|-----|
| `/start` | Bot শুরু |
| `/help` | সাহায্য |
| `/image [prompt]` | ছবি থেকে MCQ (আগে ছবি পাঠান) |
| `/pdfm -p 1-10 -m "Title"` | PDF থেকে AI MCQ |
| `/qbm -p 1-10 -m "Title"` | PDF থেকে হুবহু MCQ তোলা |
| `/sendcsv` | CSV থেকে Poll পাঠানো |
| `/quizlink` | Scheduled Quiz সেটআপ |
| `/startquiz` | Quiz শুরু করা |
| `/permit [user_id]` | User কে access দিন |
| `/revoke [user_id]` | Access নিন |
| `/listusers` | সব permitted user |

---

## 📄 PDF Command উদাহরণ

```
/pdfm -p 1-10 -c @mychannel -m "Chapter 1" বাংলায় ৫টি করে MCQ বানাও
/pdfm -p 1-5 -m "Quiz" -i -t 123
/qbm -p 10-20 -m "MCQ Bank"
```

---

## 🗂️ CSV Format (Rayvila Style)

```
questions,option1,option2,option3,option4,option5,answer,explanation,type,section
প্রশ্ন ১,অপশন ক,অপশন খ,অপশন গ,অপশন ঘ,,2,ব্যাখ্যা,1,1
```

---

## 🐧 Linux/VPS এ চালাতে (Background):

```bash
# Screen দিয়ে:
screen -S mcqbot
python bot.py
# Ctrl+A, D চাপুন detach করতে

# অথবা systemd service:
# /etc/systemd/system/mcqbot.service বানান
```

---

## ☁️ Environment Variables দিয়ে চালানো (recommended):

```bash
export TELEGRAM_BOT_TOKEN="your_token"
export GEMINI_API_KEY="your_key"
export OWNER_ID="123456789"
python bot.py
```
