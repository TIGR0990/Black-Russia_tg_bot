import os
import asyncio
import aiohttp
from datetime import datetime
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# === ТВОИ ДАННЫЕ (ОБЯЗАТЕЛЬНО ЗАМЕНИ) ===
TOKEN = "9048643506:AAEAOb4m2YvlghtQMMbCi4SEZGvgPtauoAg"  # Сюда вставь токен из BotFather (в кавычках!)
CHAT_ID = "7968538719"             # Сюда вставь свой ID из userinfobot (в кавычках!)
# ========================================

API_URL = "https://brmonitoring.onrender.com/api/servers"
TARGET_SERVER_IP = "80.66.82.154" # IP Норильска

last_status = {}
last_online_norilsk = None
notifications_enabled = True

async def check_servers():
    global last_status, notifications_enabled, last_online_norilsk
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if not isinstance(data, list):
                        data = list(data.values())
                    
                    server = next((s for s in data if s.get('ip') == TARGET_SERVER_IP), None)
                    if not server:
                        print("Сервер NORILSK не найден в API")
                        return
                    
                    online = int(server.get('online', 0))
                    status = 'online' if online > 0 else 'offline'
                    name = server.get('name', 'NORILSK')
                    server_key = f"{server['ip']}:{server['port']}"
                    
                    if server_key in last_status:
                        old_status = last_status[server_key]
                        if old_status != status:
                            await send_notification(name, old_status, status, online, server.get('maxonline', 1300))
                    
                    last_status[server_key] = status
                    
                    if last_online_norilsk is not None:
                        diff = online - last_online_norilsk
                        if abs(diff) >= 150:
                            await send_anomaly(name, last_online_norilsk, online, diff)
                    
                    last_online_norilsk = online
                        
    except Exception as e:
        print(f"Ошибка проверки: {e}")

async def send_notification(name, old_status, new_status, online, maxonline):
    bot = Bot(token=TOKEN)
    if new_status == 'online':
        emoji = "🟢"
        text = "ОТКРЫЛСЯ"
    else:
        emoji = "🔴"
        text = "ЗАКРЫЛСЯ"
        
    message = f"""{emoji} <b>{text}</b> {emoji}
<b>📡 Сервер:</b> {name}
<b>📊 Статус:</b> {new_status.upper()} ({online}/{maxonline})
<b>🕐 Время:</b> {datetime.now().strftime('%H:%M:%S')}"""
    try:
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')
    except Exception as e:
        print(f"Ошибка отправки: {e}")

async def send_anomaly(name, old_online, new_online, diff):
    bot = Bot(token=TOKEN)
    if diff < 0:
        emoji = "📉"
        text = "РЕЗКИЙ СКАЧОК ВНИЗ"
    else:
        emoji = "📈"
        text = "РЕЗКИЙ СКАЧОК ВВЕРХ"
        
    message = f"""{emoji} <b>{text}</b> {emoji}
<b>📡 Сервер:</b> {name}
<b>👥 Онлайн:</b> {old_online} → {new_online} (изменение: {diff})
<b>🕐 Время:</b> {datetime.now().strftime('%H:%M:%S')}
<i>Возможно, работает администрация или сервер перезагружается.</i>"""
    try:
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')
    except Exception as e:
        print(f"Ошибка отправки: {e}")

async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("🟢 Включить уведомления", callback_data="on")],
        [InlineKeyboardButton("🔴 Выключить уведомления", callback_data="off")],
        [InlineKeyboardButton("📊 Статус Норильска", callback_data="status")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 <b>Black Russia Monitor Bot</b>\n\n"
        "Я слежу за сервером NORILSK и присылаю уведомления, когда он открывается/закрывается или на нем резко меняется онлайн.\n\n"
        "📋 <b>Команды:</b>\n"
        "/start - показать меню\n"
        "/status - текущий статус\n"
        "/on - включить уведомления\n"
        "/off - выключить уведомления",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def status_command(update, context):
    await update.message.reply_text("🔄 Получаю данные...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if not isinstance(data, list):
                        data = list(data.values())
                    
                    server = next((s for s in data if s.get('ip') == TARGET_SERVER_IP), None)
                    if server:
                        online = int(server.get('online', 0))
                        maxonline = server.get('maxonline', 1300)
                        name = server.get('name', 'NORILSK')
                        status_emoji = "🟢" if online > 0 else "🔴"
                        
                        message = f"""📊 <b>СТАТУС СЕРВЕРА</b>

{status_emoji} <b>{name}</b>
👥 <b>Онлайн:</b> {online}/{maxonline}
📍 <b>IP:</b> {server['ip']}:{server['port']}"""
                        await update.message.reply_text(message, parse_mode='HTML')
                    else:
                        await update.message.reply_text("❌ Сервер NORILSK не найден в API.")
                    
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def turn_on(update, context):
    global notifications_enabled
    notifications_enabled = True
    await update.message.reply_text("🟢 Уведомления <b>включены</b>", parse_mode='HTML')

async def turn_off(update, context):
    global notifications_enabled
    notifications_enabled = False
    await update.message.reply_text("🔴 Уведомления <b>выключены</b>", parse_mode='HTML')

async def button_handler(update, context):
    global notifications_enabled
    query = update.callback_query
    await query.answer()
    
    if query.data == "on":
        notifications_enabled = True
        await query.edit_message_text("🟢 Уведомления <b>включены</b>", parse_mode='HTML')
    elif query.data == "off":
        notifications_enabled = False
        await query.edit_message_text("🔴 Уведомления <b>выключены</b>", parse_mode='HTML')
    elif query.data == "status":
        await status_command(update, context)

async def background_check():
    while True:
        await check_servers()
        await asyncio.sleep(30)

async def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("on", turn_on))
    application.add_handler(CommandHandler("off", turn_off))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    asyncio.create_task(background_check())
    
    print("🤖 Бот запущен и следит за NORILSK...")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
