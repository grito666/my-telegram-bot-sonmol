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

# Состояния
MAIN_MENU, WEATHER_NOW, WEATHER_FORECAST = range(3)

# Память для истории запросов (user_id -> list городов)
history_data = {}

def create_weather_image(city, temp, description, humidity, icon_url):
    img = Image.new('RGB', (400, 200), color=(135, 206, 250))
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
        [InlineKeyboardButton("🌤 Узнать погоду", callback_data='weather_now')],
        [InlineKeyboardButton("📅 Прогноз на несколько дней", callback_data='weather_forecast')],
        [InlineKeyboardButton("🕘 История запросов", callback_data='history')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text("Выберите действие:", reply_markup=reply_markup)
    return MAIN_MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == 'weather_now':
        await query.edit_message_text("Введите название города для текущей погоды:")
        return WEATHER_NOW
    elif data == 'weather_forecast':
        await query.edit_message_text("Введите название города для прогноза на несколько дней:")
        return WEATHER_FORECAST
    elif data == 'history':
        cities = history_data.get(user_id, [])
        if not cities:
            text = "История запросов пуста."
        else:
            text = "Последние города:\n" + "\n".join(f"- {c}" for c in cities[-5:])
        await query.edit_message_text(text)
        return MAIN_MENU
    elif data == 'help':
        await query.edit_message_text(
            "Этот бот поможет:\n"
            "- Узнать текущую погоду\n"
            "- Получить прогноз на несколько дней\n"
            "- Посмотреть историю запросов\n"
            "Используй кнопки меню для навигации."
        )
        return MAIN_MENU
    elif data == 'cancel':
        await query.edit_message_text("Диалог отменён.")
        return ConversationHandler.END

def save_history(user_id, city):
    if user_id not in history_data:
        history_data[user_id] = []
    history_data[user_id].append(city)

async def get_current_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    user_id = update.message.from_user.id

    url = (

𝙶𝚁𝙸𝚃𝙾🫩, [06.06.2025 12:49]
f"http://api.openweathermap.org/data/2.5/weather?q={city}"
        f"&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
    )
    try:
        response = requests.get(url)
        data = response.json()

        if data.get("cod") != 200:
            await update.message.reply_text("Город не найден. Попробуйте снова.")
            return WEATHER_NOW

        temp = data["main"]["temp"]
        description = data["weather"][0]["description"].capitalize()
        humidity = data["main"]["humidity"]
        icon_code = data["weather"][0]["icon"]
        icon_url = f"http://openweathermap.org/img/wn/{icon_code}@2x.png"

        save_history(user_id, city)

        image = create_weather_image(city, temp, description, humidity, icon_url)
        await update.message.reply_photo(photo=image)
    except Exception as e:
        logging.error(f"Ошибка получения погоды: {e}")
        await update.message.reply_text("Ошибка при получении данных.")
    return await start(update, context)

async def get_forecast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    user_id = update.message.from_user.id

    url = (
        f"http://api.openweathermap.org/data/2.5/forecast?q={city}"
        f"&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
    )
    try:
        response = requests.get(url)
        data = response.json()

        if data.get("cod") != "200":
            await update.message.reply_text("Город не найден. Попробуйте снова.")
            return WEATHER_FORECAST

        save_history(user_id, city)

        # Собираем прогноз на 5 дней с интервалом 3 часа, возьмем, например, 12:00 каждого дня
        forecast_text = f"Прогноз погоды для {city}:\n"
        shown_dates = set()
        for item in data["list"]:
            dt_txt = item["dt_txt"]  # строка формата '2025-06-06 12:00:00'
            if "12:00:00" in dt_txt:
                date = dt_txt.split(" ")[0]
                if date in shown_dates:
                    continue
                shown_dates.add(date)
                temp = item["main"]["temp"]
                desc = item["weather"][0]["description"].capitalize()
                forecast_text += f"{date}: {temp}°C, {desc}\n"
                if len(shown_dates) >= 5:
                    break

        await update.message.reply_text(forecast_text)
    except Exception as e:
        logging.error(f"Ошибка получения прогноза: {e}")
        await update.message.reply_text("Ошибка при получении данных.")
    return await start(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён.")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CallbackQueryHandler(menu_handler)],
        states={
            MAIN_MENU: [CallbackQueryHandler(menu_handler)],
            WEATHER_NOW: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_current_weather)],
            WEATHER_FORECAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_forecast)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)

    print("Бот запущен...")
    app.run_polling()
