#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import random
import string
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, ConversationHandler

# Конфигурация
BOT_TOKEN = "8408592358:AAHKXpGEF5xypy6wuHPdzFO3F4r0TkomnJk"
ADMIN_ID = 912353663

# Состояния для ConversationHandler
NAME, PHONE, CITY = range(3)

# Инициализация БД
def init_db():
    conn = sqlite3.connect('clooly.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS certificates
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  code TEXT UNIQUE,
                  client_name TEXT,
                  client_phone TEXT,
                  city TEXT,
                  trainer_name TEXT,
                  trainer_contact TEXT,
                  created_date TEXT,
                  activation_date TEXT,
                  status TEXT,
                  notes TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS trainers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  contact TEXT,
                  city TEXT)''')
    conn.commit()
    conn.close()

# Генерация уникального кода
def generate_code():
    conn = sqlite3.connect('clooly.db')
    c = conn.cursor()
    
    while True:
        code = "CLO-" + ''.join(random.choices(string.digits, k=4))
        c.execute("SELECT code FROM certificates WHERE code=?", (code,))
        if not c.fetchone():
            conn.close()
            return code

# Проверка админа
def is_admin(user_id):
    return user_id == ADMIN_ID

# Команда /start
def start(update: Update, context):
    user_id = update.effective_user.id
    
    if is_admin(user_id):
        keyboard = [
            [InlineKeyboardButton("➕ Новый сертификат", callback_data='new_cert')],
            [InlineKeyboardButton("📋 Все сертификаты", callback_data='list_certs')],
            [InlineKeyboardButton("👥 Управление тренерами", callback_data='manage_trainers')],
            [InlineKeyboardButton("📊 Статистика", callback_data='stats')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "🎯 *CLOOLY Manager*\n\n"
            "Админ-панель управления сертификатами.\n"
            "Выберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        update.message.reply_text(
            "👋 Привет!\n\n"
            "Получил сертификат CLOOLY?\n"
            "Просто отправь мне код (например: CLO-1234)\n\n"
            "Я покажу тебе контакт тренера в твоем городе!"
        )

# Обработка кнопок
def button_handler(update: Update, context):
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        query.message.reply_text("❌ Доступ запрещен")
        return ConversationHandler.END
    
    data = query.data
    
    if data == 'new_cert':
        query.message.reply_text(
            "➕ *Создание нового сертификата*\n\n"
            "Введите ФИО клиента:",
            parse_mode='Markdown'
        )
        return NAME
    
    elif data == 'list_certs':
        list_certificates(query.message)
        return ConversationHandler.END
    
    elif data == 'manage_trainers':
        manage_trainers(query.message)
        return ConversationHandler.END
    
    elif data == 'stats':
        show_stats(query.message)
        return ConversationHandler.END
    
    elif data == 'add_trainer':
        query.message.reply_text("Введите данные тренера в формате:\n\nИмя | Телефон | Город\n\nНапример:\nАхмед Магомедов | +79991234567 | Махачкала")
        return ConversationHandler.END

# Создание сертификата - шаг 1: имя
def get_name(update: Update, context):
    context.user_data['client_name'] = update.message.text
    update.message.reply_text("📱 Введите телефон клиента:")
    return PHONE

# Создание сертификата - шаг 2: телефон
def get_phone(update: Update, context):
    context.user_data['client_phone'] = update.message.text
    update.message.reply_text("🏙 Введите город клиента:")
    return CITY

# Создание сертификата - шаг 3: город
def get_city(update: Update, context):
    city = update.message.text
    context.user_data['city'] = city
    
    # Проверяем, есть ли тренер в этом городе
    conn = sqlite3.connect('clooly.db')
    c = conn.cursor()
    c.execute("SELECT name, contact FROM trainers WHERE city=?", (city,))
    trainer = c.fetchone()
    conn.close()
    
    code = generate_code()
    created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect('clooly.db')
    c = conn.cursor()
    
    if trainer:
        trainer_name, trainer_contact = trainer
        status = "Выдан"
        c.execute("""INSERT INTO certificates 
                     (code, client_name, client_phone, city, trainer_name, trainer_contact, 
                      created_date, status) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (code, context.user_data['client_name'], context.user_data['client_phone'],
                   city, trainer_name, trainer_contact, created_date, status))
    else:
        status = "В поиске тренера"
        c.execute("""INSERT INTO certificates 
                     (code, client_name, client_phone, city, created_date, status) 
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (code, context.user_data['client_name'], context.user_data['client_phone'],
                   city, created_date, status))
    
    conn.commit()
    conn.close()
    
    message = (
        f"✅ *Сертификат создан!*\n\n"
        f"🔑 Код: `{code}`\n"
        f"👤 Клиент: {context.user_data['client_name']}\n"
        f"📱 Телефон: {context.user_data['client_phone']}\n"
        f"🏙 Город: {city}\n"
    )
    
    if trainer:
        message += f"👨‍🏫 Тренер: {trainer_name}\n📞 Контакт: {trainer_contact}\n"
    else:
        message += "⚠️ Тренер в городе не найден - статус 'В поиске'\n"
    
    update.message.reply_text(message, parse_mode='Markdown')
    
    context.user_data.clear()
    return ConversationHandler.END

# Список всех сертификатов
def list_certificates(message):
    conn = sqlite3.connect('clooly.db')
    c = conn.cursor()
    c.execute("SELECT code, client_name, city, status FROM certificates ORDER BY id DESC LIMIT 20")
    certs = c.fetchall()
    conn.close()
    
    if not certs:
        message.reply_text("📋 Сертификатов пока нет")
        return
    
    text = "📋 *Последние 20 сертификатов:*\n\n"
    
    for code, name, city, status in certs:
        emoji = "✅" if status == "Выдан" else "🔍" if status == "В поиске тренера" else "🎯"
        text += f"{emoji} `{code}` - {name} ({city})\n"
    
    message.reply_text(text, parse_mode='Markdown')

# Управление тренерами
def manage_trainers(message):
    conn = sqlite3.connect('clooly.db')
    c = conn.cursor()
    c.execute("SELECT name, contact, city FROM trainers")
    trainers = c.fetchall()
    conn.close()
    
    if not trainers:
        text = "👥 *Тренеры не добавлены*\n\n"
    else:
        text = "👥 *Список тренеров:*\n\n"
        for name, contact, city in trainers:
            text += f"👨‍🏫 {name}\n📞 {contact}\n🏙 {city}\n\n"
    
    keyboard = [[InlineKeyboardButton("➕ Добавить тренера", callback_data='add_trainer')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Статистика
def show_stats(message):
    conn = sqlite3.connect('clooly.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM certificates")
    total = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM certificates WHERE status='Выдан'")
    issued = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM certificates WHERE status='В поиске тренера'")
    searching = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM certificates WHERE status='Активирован'")
    activated = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM trainers")
    trainers_count = c.fetchone()[0]
    
    conn.close()
    
    text = (
        f"📊 *Статистика CLOOLY*\n\n"
        f"📋 Всего сертификатов: {total}\n"
        f"✅ Выдано: {issued}\n"
        f"🔍 В поиске тренера: {searching}\n"
        f"🎯 Активировано: {activated}\n\n"
        f"👥 Тренеров в базе: {trainers_count}"
    )
    
    message.reply_text(text, parse_mode='Markdown')

# Обработка текстовых сообщений
def handle_message(update: Update, context):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Проверка кода сертификата
    if text.startswith("CLO-"):
        conn = sqlite3.connect('clooly.db')
        c = conn.cursor()
        c.execute("SELECT client_name, city, trainer_name, trainer_contact, status FROM certificates WHERE code=?", (text,))
        cert = c.fetchone()
        conn.close()
        
        if cert:
            name, city, trainer_name, trainer_contact, status = cert
            
            if trainer_name and trainer_contact:
                message = (
                    f"✅ *Сертификат найден!*\n\n"
                    f"👤 {name}\n"
                    f"🏙 Город: {city}\n\n"
                    f"👨‍🏫 Твой тренер: {trainer_name}\n"
                    f"📞 Контакт: {trainer_contact}\n\n"
                    f"Свяжись с тренером для записи на первую тренировку!"
                )
            else:
                message = (
                    f"✅ *Сертификат найден!*\n\n"
                    f"👤 {name}\n"
                    f"🏙 Город: {city}\n\n"
                    f"⏳ Мы сейчас подбираем тренера в твоем городе.\n"
                    f"Свяжемся в течение 2 недель!"
                )
            
            # Обновляем статус
            if status == "Выдан":
                conn = sqlite3.connect('clooly.db')
                c = conn.cursor()
                activation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("UPDATE certificates SET status='Активирован', activation_date=? WHERE code=?", 
                         (activation_date, text))
                conn.commit()
                conn.close()
            
            update.message.reply_text(message, parse_mode='Markdown')
        else:
            update.message.reply_text("❌ Сертификат не найден. Проверь код!")
    
    # Добавление тренера
    elif "|" in text and is_admin(user_id):
        parts = [p.strip() for p in text.split("|")]
        if len(parts) == 3:
            name, contact, city = parts
            
            conn = sqlite3.connect('clooly.db')
            c = conn.cursor()
            c.execute("INSERT INTO trainers (name, contact, city) VALUES (?, ?, ?)", 
                     (name, contact, city))
            conn.commit()
            conn.close()
            
            update.message.reply_text(
                f"✅ Тренер добавлен!\n\n"
                f"👨‍🏫 {name}\n"
                f"📞 {contact}\n"
                f"🏙 {city}"
            )
        else:
            update.message.reply_text("❌ Неверный формат. Используй:\nИмя | Телефон | Город")

# Отмена
def cancel(update: Update, context):
    update.message.reply_text("❌ Создание сертификата отменено")
    context.user_data.clear()
    return ConversationHandler.END

# Главная функция
def main():
    init_db()
    
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # ConversationHandler для создания сертификата
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern='^new_cert$')],
        states={
            NAME: [MessageHandler(Filters.text & ~Filters.command, get_name)],
            PHONE: [MessageHandler(Filters.text & ~Filters.command, get_phone)],
            CITY: [MessageHandler(Filters.text & ~Filters.command, get_city)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(conv_handler)
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    print("🤖 Бот запущен!")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
