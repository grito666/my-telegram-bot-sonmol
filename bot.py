import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import requests

API_TOKEN = '7754556589:AAEL1GgrR2hrdNN6EZoh3vubrUKKjsW5Keo'
NEWS_API_KEY = '36e922d0e83c4506a14d882d175c1dc6'

logging.basicConfig(level=logging.INFO)

def main_menu():
    keyboard = [
        [InlineKeyboardButton("Погода", callback_data='weather')],
        [InlineKeyboardButton("Новости", callback_data='news')],
        [InlineKeyboardButton("Гороскоп", callback_data='horoscope')],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Выбери раздел:", reply_markup=main_menu()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'news':
        url = f"https://newsapi.org/v2/top-headlines?category=technology&language=ru&apiKey={NEWS_API_KEY}"
        res = requests.get(url).json()
        articles = res.get('articles', [])[:5]

        if articles:
            msg = "Топ новости по технологии:\n\n"
            for a in articles:
                msg += f"• [{a['title']}]({a['url']})\n"
            await query.edit_message_text(msg, parse_mode='Markdown')
        else:
            await query.edit_message_text("Новости не найдены.")

    elif data == 'horoscope':
        zodiac_menu = [
            [InlineKeyboardButton("Овен", callback_data='hor_aries'), InlineKeyboardButton("Телец", callback_data='hor_taurus')],
            [InlineKeyboardButton("Близнецы", callback_data='hor_gemini'), InlineKeyboardButton("Рак", callback_data='hor_cancer')],
            [InlineKeyboardButton("Лев", callback_data='hor_leo'), InlineKeyboardButton("Дева", callback_data='hor_virgo')],
            [InlineKeyboardButton("Весы", callback_data='hor_libra'), InlineKeyboardButton("Скорпион", callback_data='hor_scorpio')],
            [InlineKeyboardButton("Стрелец", callback_data='hor_sagittarius'), InlineKeyboardButton("Козерог", callback_data='hor_capricorn')],
            [InlineKeyboardButton("Водолей", callback_data='hor_aquarius'), InlineKeyboardButton("Рыбы", callback_data='hor_pisces')],
            [InlineKeyboardButton("Назад", callback_data='main_menu')]
        ]
        await query.edit_message_text("Выбери свой знак зодиака:", reply_markup=InlineKeyboardMarkup(zodiac_menu))

    elif data.startswith('hor_'):
        sign = data[4:]
        response = requests.post(f'https://aztro.sameerkumar.website/?sign={sign}&day=today')
        if response.status_code == 200:
            horoscope = response.json()
            text = f"Гороскоп на сегодня для {sign.capitalize()}:\n\n{horoscope['description']}"
            await query.edit_message_text(text)
        else:
            await query.edit_message_text("Не удалось получить гороскоп.")

    elif data == 'main_menu':
        await query.edit_message_text("Главное меню:", reply_markup=main_menu())

    else:
        await query.edit_message_text("Этот раздел в разработке.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(API_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()
