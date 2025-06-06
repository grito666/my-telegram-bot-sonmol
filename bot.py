import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
import os

# Конфигурация логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Загрузка токенов из переменных окружения
API_TOKEN = os.getenv('TELEGRAM_TOKEN')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

def main_menu():
    keyboard = [
        [InlineKeyboardButton("Погода", callback_data='weather')],
        [InlineKeyboardButton("Новости", callback_data='news')],
        [InlineKeyboardButton("Гороскоп", callback_data='horoscope')],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Выбери раздел:", reply_markup=main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'news':
        try:
            url = f"https://newsapi.org/v2/top-headlines?category=technology&language=ru&apiKey={NEWS_API_KEY}"
            res = requests.get(url).json()
            articles = res.get('articles', [])[:5]
            if articles:
                msg = "Топ новости:\n\n" + "\n".join(f"• [{a['title']}]({a['url']})" for a in articles)
                await query.edit_message_text(msg, parse_mode='Markdown')
            else:
                await query.edit_message_text("Новости не найдены.")
        except Exception as e:
            logging.error(f"News API error: {e}")
            await query.edit_message_text("Ошибка при загрузке новостей.")

    elif data == 'horoscope':
        zodiac_menu = [[InlineKeyboardButton("Овен", callback_data='hor_aries')], [InlineKeyboardButton("Назад", callback_data='main_menu')]]
        await query.edit_message_text("Выбери знак зодиака:", reply_markup=InlineKeyboardMarkup(zodiac_menu))

    elif data.startswith('hor_'):
        sign = data[4:]
        try:
            response = requests.post(f'https://aztro.sameerkumar.website/?sign={sign}&day=today')
            if response.status_code == 200:
                horoscope = response.json()
                await query.edit_message_text(f"Гороскоп для {sign.capitalize()}:\n{horoscope['description']}")
            else:
                await query.edit_message_text("Ошибка API гороскопа.")
        except Exception as e:
            logging.error(f"Horoscope error: {e}")
            await query.edit_message_text("Сервис временно недоступен.")

    elif data == 'main_menu':
        await query.edit_message_text("Главное меню:", reply_markup=main_menu())

if __name__ == '__main__':
    if not API_TOKEN:
        raise ValueError("TELEGRAM_TOKEN не задан!")
    
    app = ApplicationBuilder().token(API_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling(drop_pending_updates=True)
