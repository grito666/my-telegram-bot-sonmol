import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes,
    filters, ConversationHandler
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")  # добавим на Render

ASK_CITY = 1  # состояние FSM

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [["📍 Узнать погоду", "ℹ️ Помощь"]]
    reply_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    await update.message.reply_text("Привет! Что ты хочешь сделать?", reply_markup=reply_markup)

# Обработка нажатий кнопок
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📍 Узнать погоду":
        await update.message.reply_text("Введи название города:")
        return ASK_CITY
    elif text == "ℹ️ Помощь":
        await update.message.reply_text("Я могу показать погоду. Просто выбери соответствующий пункт в меню.")
    else:
        await update.message.reply_text("Пожалуйста, выбери действие с кнопок ниже.")

# Обработка города и вызов API
async def get_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text
    key = os.getenv("OPENWEATHER_API_KEY")
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric&lang=ru"

    try:
        response = requests.get(url)
        data = response.json()

        if data.get("cod") != 200:
            await update.message.reply_text("Город не найден. Попробуй снова.")
            return ASK_CITY

        temp = data["main"]["temp"]
        description = data["weather"][0]["description"].capitalize()
        humidity = data["main"]["humidity"]

        reply = (
            f"🌤 Погода в городе {city}:\n"
            f"🌡 Температура: {temp}°C\n"
            f"💧 Влажность: {humidity}%\n"
            f"📋 Описание: {description}"
        )

        await update.message.reply_text(reply)
    except Exception as e:
        logging.error(f"Ошибка при получении погоды: {e}")
        await update.message.reply_text("Произошла ошибка при получении данных.")
    return ConversationHandler.END

# Сброс диалога
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён.")
    return ConversationHandler.END

if name == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # FSM для погоды
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("📍 Узнать погоду"), handle_menu)],
        states={
            ASK_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weather)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))

    print("Бот запущен...")
    app.run_polling()
