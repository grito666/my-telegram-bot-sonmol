import os
import logging
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

ASK_CITY = 1

def create_weather_image(city, temp, description, humidity, icon_url):
    img = Image.new('RGB', (400, 200), color=(135, 206, 250))  # Голубой фон
    draw = ImageDraw.Draw(img)

    try:
        response = requests.get(icon_url)
        icon = Image.open(BytesIO(response.content)).convert("RGBA")
        icon = icon.resize((100, 100))
        img.paste(icon, (20, 50), icon)
    except Exception as e:
        logging.error(f"Ошибка загрузки иконки: {e}")

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        font_large = ImageFont.truetype(font_path, 30)
        font_small = ImageFont.truetype(font_path, 20)
    except IOError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    draw.text((140, 40), f"{city}", font=font_large, fill="white")
    draw.text((140, 80), f"{temp}°C, {description}", font=font_small, fill="white")
    draw.text((140, 120), f"Влажность: {humidity}%", font=font_small, fill="white")

    output = BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    return output

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📍 Узнать погоду", callback_data='weather')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери действие:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'weather':
        await query.edit_message_text("Введи название города:")
        return ASK_CITY
    elif data == 'help':
        await query.edit_message_text(
            "Я помогу тебе узнать погоду.\n\nНажми 'Узнать погоду', введи город и получи прогноз."
        )
        return ConversationHandler.END
    elif data == 'cancel':
        await query.edit_message_text("Диалог отменён.")
        return ConversationHandler.END

async def get_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    url = (
        f"http://api.openweathermap.org/data/2.5/weather?q={city}"
        f"&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
    )
    try:
        response = requests.get(url)
        data = response.json()

        if data.get("cod") != 200:
            await update.message.reply_text("Город не найден. Попробуй ещё раз.")
            return ASK_CITY

        temp = data["main"]["temp"]
        description = data["weather"][0]["description"].capitalize()
        humidity = data["main"]["humidity"]
        icon_code = data["weather"][0]["icon"]
        icon_url = f"http://openweathermap.org/img/wn/{icon_code}@2x.png"

        image = create_weather_image(city, temp, description, humidity, icon_url)
        await update.message.reply_photo(photo=image)

    except Exception as e:
        logging.error(f"Ошибка при получении погоды: {e}")
        await update.message.reply_text("Произошла ошибка при получении данных.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён.")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
entry_points=[CallbackQueryHandler(button_handler, pattern='^weather$')],
        states={
            ASK_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weather)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(conv_handler)

    print("Бот запущен...")
    app.run_polling()
