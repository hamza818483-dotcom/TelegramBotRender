import os
import pandas as pd
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# 🔹 Replace these with your own
TOKEN = "8297282007:AAGZTiGNGuMaEVjjpF1gNO3VnrL0bAbYfGc"
GEMINI_API = "AIzaSyDwq9YEiP6uqD_MgkTk8CmoFG6a9mKDHes"

genai.configure(api_key=GEMINI_API)
model = genai.GenerativeModel("gemini-1.5")

users_allowed = set()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Send me an image with /image to generate MCQ.")

# /permit command
async def permit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = int(context.args[0])
        users_allowed.add(user_id)
        await update.message.reply_text(f"User {user_id} permitted.")
    except:
        await update.message.reply_text("Use: /permit <user_id>")

# Image handler
async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in users_allowed:
        await update.message.reply_text("You are not permitted to use this bot.")
        return

    if not update.message.photo:
        await update.message.reply_text("Please send a photo.")
        return

    file = await update.message.photo[-1].get_file()
    path = "img.jpg"
    await file.download_to_drive(path)

    prompt = "Extract text from image and create 1 MCQ with 4 options and correct answer."
    response = model.generate_content(prompt)
    text = response.text

    df = pd.DataFrame([{
        "questions": text,
        "option1": "Option A",
        "option2": "Option B",
        "option3": "Option C",
        "option4": "Option D",
        "option5": "",
        "answer": "1",
        "explanation": "",
        "type": "1",
        "section": "1"
    }])
    df.to_csv("mcq.csv", index=False)
    await update.message.reply_document(open("mcq.csv", "rb"))

# Telegram bot setup
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("permit", permit))
app.add_handler(MessageHandler(filters.PHOTO, image_handler))

app.run_polling()
